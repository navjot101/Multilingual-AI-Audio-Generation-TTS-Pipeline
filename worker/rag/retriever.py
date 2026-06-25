import logging
import numpy as np
import faiss

log = logging.getLogger(__name__)


def retrieve(context_index, query: str, top_k: int = 3) -> list[str]:
    query_embedding = context_index.model.encode([query], show_progress_bar=False)
    query_embedding = query_embedding.astype(np.float32)
    faiss.normalize_L2(query_embedding)

    scores, indices = context_index.index.search(query_embedding, top_k)
    results = [context_index.contexts[i]["text"] for i in indices[0]]
    log.debug("Retrieved top-%d chunks with scores %s", top_k, scores[0])
    return results
