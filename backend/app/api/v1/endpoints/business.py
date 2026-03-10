from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.session import get_db
from app.api.deps.auth_deps import get_current_user
from app.models.user import User
from app.services.business_service import business_service
from app.schemas.business import ImportResult, Business, BusinessUpdate, BusinessList

router = APIRouter()


@router.get("/", response_model=BusinessList)
async def list_businesses(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Liste les entreprises avec recherche (iLike) et pagination.
    Recherche sur : nomination, ville, act, tel.
    """
    items, total = await business_service.get_multi(
        db, skip=skip, limit=limit, search=search
    )
    return BusinessList(items=items, total=total)


@router.patch("/{business_id}", response_model=Business)
async def update_business(
    business_id: int,
    obj_in: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Met à jour une entreprise.
    """
    db_obj = await business_service.update(
        db, business_id=business_id, obj_in=obj_in.dict()
    )
    if not db_obj:
        raise HTTPException(status_code=404, detail="Business not found")
    return db_obj


@router.delete("/{business_id}")
async def delete_business(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Supprime une entreprise.
    """
    success = await business_service.remove(db, business_id=business_id)
    if not success:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"message": "Business deleted successfully"}


@router.post("/import", response_model=ImportResult)
async def import_businesses(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Importe des entreprises depuis un fichier CSV ou Excel.
    Colonnes attendues : NOMINATION, Adresse, CP, Ville, TEL, ACT
    """
    # Check file extension
    filename = file.filename.lower()
    if filename.endswith(".csv"):
        file_type = "csv"
    elif filename.endswith((".xlsx", ".xls")):
        file_type = "xlsx"
    else:
        raise HTTPException(
            status_code=400, detail="Only CSV or Excel files are supported"
        )

    content = await file.read()
    result = await business_service.import_from_file(content, file_type, db)

    if result.errors:
        raise HTTPException(status_code=400, detail=", ".join(result.errors))

    return result
