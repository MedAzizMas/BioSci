"""
Configuration file for Protein Alignment Flask Application
============================================================
"""

import os

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "protein_data")
CACHE_DIR = os.path.join(BASE_DIR, "protein_cache")

# Data paths
CHUNKS_DIR = os.path.join(DATA_DIR, "chunks")
FASTA_DIR = os.path.join(DATA_DIR, "fasta")
CLEANED_DIR = os.path.join(DATA_DIR, "cleaned")
EMBEDDINGS_CACHE_DIR = os.path.join(CACHE_DIR, "embeddings")

# Chunk parquet files
HUMAN_CHUNKS_FILE = os.path.join(CHUNKS_DIR, "Homo_sapiens_chunks.parquet")
BACT_CHUNKS_FILE = os.path.join(CHUNKS_DIR, "Klebsiella_pneumoniae_chunks.parquet")

# Cleaned sequence files (output from clean_fasta_files.py)
HUMAN_CLEANED_FILE = os.path.join(CLEANED_DIR, "Homo_sapiens_cleaned.parquet")
BACT_CLEANED_FILE = os.path.join(CLEANED_DIR, "Klebsiella_pneumoniae_cleaned.parquet")

# Organism names
HUMAN = "Homo_sapiens"
BACT = "Klebsiella_pneumoniae"

# Chunking parameters
CHUNK_LEN = 10
CHUNK_STRIDE = 5

# Smith-Waterman parameters
GAP_OPEN = -0.2
GAP_EXTEND = -0.1
SCORE_THRESHOLD = 0.5
MIN_SCORE = 0.3
MIN_CHUNKS = 2

# ESM-2 Model settings
ESM2_MODEL = "esm2_t30_150M_UR50D"  # ESM-2 150M
EMBEDDING_BATCH_SIZE = 8
DEVICE = "cuda"  # Change to "cpu" if no GPU available

# Groq API settings
from app_secrets import GROQ_API_KEY as _GROQ_KEY
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", _GROQ_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.1
GROQ_MAX_TOKENS = 3000

# Pfam settings (optional - only if using local PfamScan)
PFAM_DIR = os.environ.get("PFAM_DIR", "")  # Set this if you have local Pfam
PFAM_SCAN_PATH = os.path.join(PFAM_DIR, "PfamScan/pfam_scan.pl") if PFAM_DIR else ""
USE_LOCAL_PFAM = bool(PFAM_DIR and os.path.exists(PFAM_SCAN_PATH))

# Flask settings
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
DEBUG = True

# Cache settings
ENABLE_EMBEDDING_CACHE = True
CACHE_EXPIRY_DAYS = 30

# Ensure directories exist
os.makedirs(EMBEDDINGS_CACHE_DIR, exist_ok=True)
