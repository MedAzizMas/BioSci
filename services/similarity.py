"""
Similarity Computation Service
================================
Compute cosine similarity between chunk embeddings.
"""

import numpy as np
from sklearn.preprocessing import normalize

def compute_cosine_similarity(embeddings_a, embeddings_b):
    """
    Compute cosine similarity matrix between two sets of embeddings.
    
    Args:
        embeddings_a: numpy array of shape (N, dim)
        embeddings_b: numpy array of shape (M, dim)
        
    Returns:
        Similarity matrix of shape (N, M) with values in [0, 1]
    """
    # Normalize embeddings
    emb_a_norm = normalize(embeddings_a, axis=1)
    emb_b_norm = normalize(embeddings_b, axis=1)
    
    # Compute similarity matrix
    similarity_matrix = np.dot(emb_a_norm, emb_b_norm.T)
    
    return similarity_matrix

def get_similarity_statistics(similarity_matrix):
    """
    Compute statistics on the similarity matrix.
    
    Returns:
        Dictionary with min, max, mean, std, median, percentiles
    """
    S = similarity_matrix
    
    top_k = min(100, S.size)
    topk_vals = np.partition(S.flatten(), -top_k)[-top_k:]
    
    stats = {
        "matrix_shape": list(S.shape),
        "min_similarity": float(S.min()),
        "max_similarity": float(S.max()),
        "mean_similarity": float(S.mean()),
        "std_similarity": float(S.std()),
        "median_similarity": float(np.median(S)),
        f"mean_top_{top_k}": float(topk_vals.mean()),
        "percentile_90": float(np.percentile(S, 90)),
        "percentile_95": float(np.percentile(S, 95)),
        "percentile_99": float(np.percentile(S, 99))
    }
    
    return stats

def get_top_chunk_pairs(similarity_matrix, h_chunks, b_chunks, top_n=20):
    """
    Get the top N chunk pairs by similarity score.
    
    Returns:
        List of dicts with chunk pair information
    """
    pairs = []
    H, B = similarity_matrix.shape
    
    for i in range(H):
        for j in range(B):
            pairs.append((i, j, float(similarity_matrix[i, j])))
    
    pairs_sorted = sorted(pairs, key=lambda x: x[2], reverse=True)
    
    top_pairs = []
    for i, j, score in pairs_sorted[:top_n]:
        h_row = h_chunks.iloc[i]
        b_row = b_chunks.iloc[j]
        
        top_pairs.append({
            "human_chunk_idx": int(i),
            "bact_chunk_idx": int(j),
            "similarity": score,
            "human_range": [int(h_row['start']), int(h_row['end'])],
            "bact_range": [int(b_row['start']), int(b_row['end'])],
            "human_seq": str(h_row['chunk_seq']),
            "bact_seq": str(b_row['chunk_seq'])
        })
    
    return top_pairs
