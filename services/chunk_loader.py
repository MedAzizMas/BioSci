"""
Chunk Loader Service
====================
Load pre-computed protein chunks from parquet files.
"""

import pandas as pd
import protein_config as config

def load_chunks(organism="human"):
    """
    Load chunk parquet file for specified organism.
    
    Args:
        organism: "human" or "bacteria"
        
    Returns:
        DataFrame with columns: organism, protein_id, chunk_index, start, end, chunk_seq, chunk_row/chunk_col
    """
    if organism.lower() == "human":
        chunks_file = config.HUMAN_CHUNKS_FILE
    elif organism.lower() in ["bacteria", "bacterial"]:
        chunks_file = config.BACT_CHUNKS_FILE
    else:
        raise ValueError(f"Unknown organism: {organism}. Use 'human' or 'bacteria'")
    
    print(f"Loading chunks from: {chunks_file}")
    chunks_df = pd.read_parquet(chunks_file)
    print(f"  Loaded {len(chunks_df)} chunks")
    
    return chunks_df

def get_protein_chunks(protein_id, organism="human"):
    """
    Get all chunks for a specific protein ID.
    
    Args:
        protein_id: Protein identifier (e.g., "tr|A0A024RA31|A0A024RA31_HUMAN")
        organism: "human" or "bacteria"
        
    Returns:
        DataFrame with chunks for the specified protein, sorted by chunk_index
    """
    chunks_df = load_chunks(organism)
    
    # Filter for the specific protein
    protein_chunks = chunks_df[chunks_df["protein_id"] == protein_id].sort_values("chunk_index").reset_index(drop=True)
    
    if len(protein_chunks) == 0:
        raise ValueError(f"Protein ID '{protein_id}' not found in {organism} chunks")
    
    print(f"  Found {len(protein_chunks)} chunks for protein {protein_id}")
    
    return protein_chunks

def get_protein_full_sequence(protein_id, organism="human"):
    """
    Retrieve full protein sequence from cleaned parquet files.
    
    Args:
        protein_id: Protein identifier
        organism: "human" or "bacteria"
        
    Returns:
        Full protein sequence string
    """
    if organism.lower() == "human":
        cleaned_file = config.HUMAN_CLEANED_FILE
    elif organism.lower() in ["bacteria", "bacterial"]:
        cleaned_file = config.BACT_CLEANED_FILE
    else:
        raise ValueError(f"Unknown organism: {organism}")
    
    cleaned_df = pd.read_parquet(cleaned_file)
    
    # Find the protein
    protein_row = cleaned_df[cleaned_df["protein_id"] == protein_id]
    
    if protein_row.empty:
        raise ValueError(f"Protein ID '{protein_id}' not found in cleaned {organism} sequences")
    
    return str(protein_row.iloc[0]["sequence"])

def validate_protein_exists(protein_id, organism="human"):
    """
    Check if a protein ID exists in the chunks.
    
    Returns:
        (exists: bool, num_chunks: int, error_message: str)
    """
    try:
        chunks = get_protein_chunks(protein_id, organism)
        return True, len(chunks), None
    except ValueError as e:
        return False, 0, str(e)
