import json
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

log = logging.getLogger(__name__)


class ContextIndex:
    def __init__(self, contexts_path: str):
        log.info("Loading sentence transformer model all-MiniLM-L6-v2")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        with open(contexts_path, "r") as f:
            self.contexts = json.load(f)

        texts = [ctx["text"] for ctx in self.contexts]
        log.info("Encoding %d context chunks", len(texts))
        embeddings = self.model.encode(texts, show_progress_bar=False)
        embeddings = embeddings.astype(np.float32)
        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        log.info("FAISS index built with %d vectors (dim=%d)", len(texts), dimension)
