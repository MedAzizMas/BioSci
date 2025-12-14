"""
ESM-2 Embedding Service
========================
Generate protein embeddings using ESM-2 model.
"""

import torch
import numpy as np
from esm import pretrained
from torch.utils.data import DataLoader, Dataset
import protein_config as config
import os
import hashlib
import pickle

# Global model cache
_model_cache = None

class SeqDataset(Dataset):
    """Dataset wrapper for batching sequences."""
    def __init__(self, ids, seqs):
        self.ids = ids
        self.seqs = seqs
    
    def __len__(self):
        return len(self.seqs)
    
    def __getitem__(self, idx):
        return (self.ids[idx], self.seqs[idx])

def get_esm2_model():
    """
    Load ESM-2 model (cached globally to avoid reloading).
    
    Returns:
        (model, alphabet, batch_converter, device)
    """
    global _model_cache
    
    if _model_cache is not None:
        return _model_cache
    
    print("Loading ESM-2 model...")
    model, alphabet = pretrained.esm2_t30_150M_UR50D()
    batch_converter = alphabet.get_batch_converter()
    
    device = config.DEVICE if torch.cuda.is_available() else "cpu"
    model = model.eval().to(device)
    
    print(f"  Model loaded on device: {device}")
    
    _model_cache = (model, alphabet, batch_converter, device)
    return _model_cache

def embed_sequences(sequences, ids=None, batch_size=None):
    """
    Generate ESM-2 embeddings for a list of sequences.
    
    Args:
        sequences: List of protein sequences
        ids: Optional list of sequence IDs
        batch_size: Batch size for embedding (default from config)
        
    Returns:
        numpy array of shape (N, embedding_dim) with mean-pooled embeddings
    """
    if ids is None:
        ids = [str(i) for i in range(len(sequences))]
    
    if batch_size is None:
        batch_size = config.EMBEDDING_BATCH_SIZE
    
    model, alphabet, batch_converter, device = get_esm2_model()
    
    ds = SeqDataset(ids, sequences)
    dl = DataLoader(ds, batch_size=batch_size, collate_fn=list)
    
    embeddings = []
    
    with torch.no_grad():
        for batch in dl:
            batch_list = [(b[0], b[1]) for b in batch]
            labels, strs, toks = batch_converter(batch_list)
            toks = toks.to(device)
            
            results = model(toks, repr_layers=[model.num_layers], return_contacts=False)
            rep = results["representations"][model.num_layers]
            
            # Mean pooling over sequence length (excluding special tokens)
            for i, (_, seq) in enumerate(batch_list):
                L = len(seq)
                vec = rep[i, 1:L+1].mean(0).cpu().numpy().astype("float32")
                embeddings.append(vec)
    
    return np.vstack(embeddings)

def get_cache_key(sequences):
    """Generate a cache key from sequences."""
    seq_str = "".join(sequences)
    return hashlib.md5(seq_str.encode()).hexdigest()

def load_cached_embeddings(cache_key):
    """Load embeddings from cache if available."""
    if not config.ENABLE_EMBEDDING_CACHE:
        return None
    
    cache_file = os.path.join(config.EMBEDDINGS_CACHE_DIR, f"{cache_key}.pkl")
    
    if os.path.exists(cache_file):
        print(f"  Loading embeddings from cache: {cache_key[:8]}...")
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    
    return None

def save_cached_embeddings(cache_key, embeddings):
    """Save embeddings to cache."""
    if not config.ENABLE_EMBEDDING_CACHE:
        return
    
    cache_file = os.path.join(config.EMBEDDINGS_CACHE_DIR, f"{cache_key}.pkl")
    
    with open(cache_file, 'wb') as f:
        pickle.dump(embeddings, f)
    
    print(f"  Saved embeddings to cache: {cache_key[:8]}...")

def embed_chunk_dataframe(chunks_df, use_cache=True):
    """
    Generate embeddings for all chunks in a DataFrame.
    
    Args:
        chunks_df: DataFrame with 'chunk_seq' column
        use_cache: Whether to use cached embeddings
        
    Returns:
        numpy array of embeddings
    """
    sequences = chunks_df["chunk_seq"].astype(str).tolist()
    
    if use_cache:
        cache_key = get_cache_key(sequences)
        cached = load_cached_embeddings(cache_key)
        if cached is not None:
            return cached
    
    print(f"  Generating embeddings for {len(sequences)} chunks...")
    embeddings = embed_sequences(sequences)
    
    if use_cache:
        cache_key = get_cache_key(sequences)
        save_cached_embeddings(cache_key, embeddings)
    
    return embeddings
