from sentence_transformers import SentenceTransformer
from typing import List, Optional

class EmbeddingService:
    def __init__(self):
        self.model = None
        self.model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    
    def load_model(self):
        try:
            self.model = SentenceTransformer(self.model_name)
        except:
            self.model = None
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        if not self.model:
            return None
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except:
            return None
    
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.model:
            return []
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except:
            return []

embedding_service = EmbeddingService()
