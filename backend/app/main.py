from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.api.v1 import api_router
from app.services.cache import cache_service
from app.services.ml_service import ml_service
from app.services.rag_service import rag_service
from app.rag.embeddings import embedding_service
import logging

logger = logging.getLogger(__name__)


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Cache Redis
    await cache_service.connect()
    logger.info("Redis cache connected")

    # 2. ML models (Random Forest SMS)
    ml_service.load_models()
    logger.info("ML models loaded")

    # 3. Qdrant vector DB (RAG)
    rag_service.connect()
    if rag_service.enabled:
        logger.info("RAG service connected to Qdrant")
    else:
        logger.warning("RAG service disabled (Qdrant unavailable)")

    # 4. Sentence-transformers embeddings
    embedding_service.load_model()
    if embedding_service.enabled:
        logger.info("Embedding model loaded: %s", embedding_service.model_name)
    else:
        logger.warning("Embedding model disabled")

    yield

    await cache_service.disconnect()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "services": {
            "ml": bool(ml_service.sms_model),
            "rag": rag_service.enabled,
            "embeddings": embedding_service.enabled,
        },
    }


@app.get("/")
async def root():
    return {"message": "DYLETH API", "version": settings.VERSION, "docs": "/docs"}