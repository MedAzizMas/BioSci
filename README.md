# BioSci AI

A professional bioinformatics platform combining Knowledge Graph-based Genomic Analysis with Protein Alignment tools, powered by Large Language Models.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![License](https://img.shields.io/badge/License-Academic-orange.svg)

## Features

### 1. Genomic Analysis (GraphRAG Chatbot)
- Query relationships between **diseases**, **drugs/chemicals**, **genes**, and **pathways**
- Knowledge graph with 4.7M+ relationships from CTD database
- Interactive graph visualization using PyVis
- AI-powered answers using Llama 3.1 70B
- Features:
  - Voice input (Web Speech API)
  - Text-to-speech output
  - French translation
  - Follow-up question suggestions
  - Entity autocomplete
  - Dark/Light theme support

### 2. Protein Alignment Analysis
- Compare protein sequences between **Human** and **Klebsiella pneumoniae**
- ESM-2 embeddings (150M parameters) for semantic similarity
- Smith-Waterman alignment on embedding space
- Biochemical and structural descriptor analysis
- LLM biological interpretation using Llama 3.3 70B (via Groq)
- 3D protein structure visualization (AlphaFold integration)

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask (Python) |
| Genomic LLM | Llama 3.1 70B (TokenFactory API) |
| Protein LLM | Llama 3.3 70B (Groq API) |
| Embeddings | Sentence-Transformers, ESM-2 |
| Vector Search | FAISS |
| Graph Visualization | PyVis |
| 3D Visualization | 3Dmol.js + AlphaFold API |
| Frontend | HTML5, CSS3, JavaScript |

## Installation

### Prerequisites
- Python 3.9 or higher
- CUDA-compatible GPU (recommended for ESM-2)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd biosci-ai
```

2. Create virtual environment:
```bash
python -m venv graphrag_env
source graphrag_env/bin/activate  # Linux/Mac
graphrag_env\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Ensure data files are present:
```
data/
├── graph_chunks.pkl
├── graph_embeddings.npy
└── graph_index.faiss

protein_data/
├── chunks/
├── cleaned/
└── fasta/
```

## Usage

### Running the Application

```bash
python app_flask.py
```

The application will be available at `http://127.0.0.1:5000`

### Pages

| Route | Description |
|-------|-------------|
| `/` | Homepage |
| `/genomic` | GraphRAG Chatbot for genomic queries |
| `/protein` | Protein alignment analysis tool |
| `/protein/results/<id>` | Alignment results page |

## API Endpoints

### Genomic Analysis
- `POST /api/query` - Submit a genomic question
- `GET /api/autocomplete?q=<query>` - Entity autocomplete
- `POST /api/translate` - Translate answer to French

### Protein Analysis
- `POST /api/protein/analyze` - Run alignment pipeline
- `POST /api/protein/validate` - Validate protein IDs
- `GET /api/protein/structure/<id>` - Fetch AlphaFold structure
- `GET /api/protein/download/<id>` - Download results as JSON

## Project Structure

```
biosci-ai/
├── app_flask.py              # Main Flask application
├── protein_config.py         # Protein pipeline configuration
├── requirements.txt          # Python dependencies
├── data/                     # GraphRAG data files
├── protein_data/             # Protein sequence data
├── protein_cache/            # Cached results
├── services/                 # Protein alignment services
│   ├── aligner.py
│   ├── chunk_loader.py
│   ├── descriptors.py
│   ├── embedder.py
│   ├── functional_annotator.py
│   ├── llm_analyzer.py
│   ├── pipeline.py
│   └── similarity.py
├── static/
│   ├── css/
│   ├── js/
│   ├── images/
│   └── videos/
└── templates/
    ├── index.html
    ├── genomic.html
    ├── protein.html
    └── protein_results.html
```

## Configuration

### API Keys

Set the following in `protein_config.py`:
- `GROQ_API_KEY` - For protein LLM analysis

The genomic LLM uses TokenFactory API (pre-configured).

### GPU Settings

In `protein_config.py`:
```python
DEVICE = "cuda"  # Use "cpu" if no GPU available
```

## Team

- **Mohamed Aziz Masmoudi** - Developer
- **Hazem Mbarek** - Developer
- **Ala Kammoun** - Developer
- **Nour Chokri** - Developer
- **Ranim Ammar** - Developer
- **Doua Boudokhan** - Developer

## Acknowledgments

- CTD (Comparative Toxicogenomics Database) for genomic data
- Meta AI for ESM-2 protein language model
- AlphaFold for protein structure predictions
- Groq and TokenFactory for LLM APIs

## License

This project is developed for academic purposes.

---

© 2025 BioSci AI. All Rights Reserved.
