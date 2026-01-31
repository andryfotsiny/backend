from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1 import api_router
from app.services.cache import cache_service
from app.services.ml_service import ml_service
from app.services.rag_service import rag_service
from app.rag.embeddings import embedding_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache_service.connect()
    ml_service.load_models()
    rag_service.connect()
    embedding_service.load_model()
    
    yield
    
    await cache_service.disconnect()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

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
    return {"status": "healthy", "version": settings.VERSION}

@app.get("/")
async def root():
    return {
        "message": "DYLETH API",
        "version": settings.VERSION,
        "docs": "/docs"
    }
