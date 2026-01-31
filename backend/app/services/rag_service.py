from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Tuple, Optional
from app.core.config import settings
import hashlib

class RAGService:
    def __init__(self):
        self.client = None
        self.collection_name = "fraud_vectors"
        
    def connect(self):
        try:
            self.client = QdrantClient(url=settings.QDRANT_URL)
            self._ensure_collection()
        except:
            self.client = None
    
    def _ensure_collection(self):
        if not self.client:
            return
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
        except:
            pass
    
    def search_similar(self, vector: List[float], limit: int = 10) -> List[dict]:
        if not self.client:
            return []
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit
            )
            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "payload": r.payload
                }
                for r in results
            ]
        except:
            return []
    
    def add_vector(self, vector: List[float], payload: dict):
        if not self.client:
            return
        try:
            point_id = hashlib.md5(str(payload).encode()).hexdigest()[:16]
            point = PointStruct(
                id=int(point_id, 16) % (2**63),
                vector=vector,
                payload=payload
            )
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
        except:
            pass
    
    def check_similarity_fraud(self, vector: List[float], threshold: float = 0.85) -> Tuple[bool, int]:
        results = self.search_similar(vector, limit=100)
        similar_frauds = [r for r in results if r["score"] >= threshold]
        is_fraud = len(similar_frauds) >= 3
        return is_fraud, len(similar_frauds)

rag_service = RAGService()
