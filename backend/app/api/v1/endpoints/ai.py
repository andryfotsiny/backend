from fastapi import APIRouter, Depends, BackgroundTasks, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import io
import csv
from app.db.session import get_db
from app.schemas.ai import ChatRequest, ChatResponse, TrainingDataRequest, TrainingResponse
from app.services.ai_service import ai_service
from app.services.ml_service.service import ml_service
from app.api.deps.auth_deps import get_current_user
from app.models.user import User
from app.ml.train import trigger_training, DATA_DIR

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Interagir avec l'IA de DYLETH.
    Permet de poser des questions sur les détections, les statistiques ou le fonctionnement du système.
    """
    result = await ai_service.get_response(db, request.message, request.user_id)
    return ChatResponse(**result)


async def run_training_background():
    """Tâche de fond pour l'entraînement et le rechargement."""
    try:
        trigger_training()
        ml_service.load_models()
    except Exception as e:
        print(f"Error in background training: {e}")


@router.post("/train/text", response_model=TrainingResponse)
async def add_training_text(
    request: TrainingDataRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Ajouter un message unique au jeu d'entraînement et déclencher le ré-entraînement.
    """
    try:
        dataset_path = DATA_DIR / "sms_train.csv"
        file_exists = dataset_path.exists()

        with open(dataset_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["content", "is_fraud", "fraud_type"])
            writer.writerow([request.content, 1 if request.is_fraud else 0, "api_submission"])

        background_tasks.add_task(run_training_background)
        return TrainingResponse(
            success=True,
            message="Données ajoutées. Entraînement lancé en arrière-plan."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train/csv", response_model=TrainingResponse)
async def upload_training_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Uploader un fichier CSV pour l'entraînement.
    Le CSV doit avoir les colonnes : content, is_fraud
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers CSV sont acceptés.")

    try:
        content = await file.read()
        df_new = pd.read_csv(io.BytesIO(content))

        if "content" not in df_new.columns or "is_fraud" not in df_new.columns:
            raise HTTPException(
                status_code=400,
                detail="Le CSV doit contenir les colonnes 'content' et 'is_fraud'."
            )

        # Standardisation des labels
        df_new["is_fraud"] = df_new["is_fraud"].astype(int)
        if "fraud_type" not in df_new.columns:
            df_new["fraud_type"] = "csv_upload"

        # On ne garde que ce qui nous intéresse
        df_new = df_new[["content", "is_fraud", "fraud_type"]]

        dataset_path = DATA_DIR / "sms_train.csv"
        if dataset_path.exists():
            df_existing = pd.read_csv(dataset_path)
            df_final = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_final = df_new

        df_final.to_csv(dataset_path, index=False)

        background_tasks.add_task(run_training_background)
        return TrainingResponse(
            success=True,
            message=f"{len(df_new)} exemples ajoutés. Entraînement lancé en arrière-plan."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
