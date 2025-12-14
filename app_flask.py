from flask import Flask, render_template, request, jsonify, send_file
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import httpx
from openai import OpenAI
from pyvis.network import Network
import tempfile
import os
import json
from datetime import datetime

# Import protein alignment services
from services.pipeline import run_alignment_pipeline
from services.chunk_loader import validate_protein_exists

app = Flask(__name__, static_folder='static', template_folder='templates')

# Global variables for loaded resources
chunks = None
index = None
embedding_model = None
llm_client = None
stats = None

# Protein alignment results cache
protein_results_cache = {}

def load_resources():
    """Load all resources once at startup"""
    global chunks, index, embedding_model, llm_client, stats
    
    # Load chunks
    with open('data/graph_chunks.pkl', 'rb') as f:
        chunks = pickle.load(f)
    
    # Load FAISS index
    index = faiss.read_index('data/graph_index.faiss')
    
    # Load embedding model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Setup LLM client
    from secrets import TOKENFACTORY_API_KEY
    http_client = httpx.Client(verify=False)
    llm_client = OpenAI(
        api_key=TOKENFACTORY_API_KEY,
        base_url="https://tokenfactory.esprit.tn/api",
        http_client=http_client
    )
    
    # Calculate stats
    type_counts = {}
    for chunk in chunks:
        t = chunk['type']
        type_counts[t] = type_counts.get(t, 0) + 1
    
    stats = {
        'diseases': f"{type_counts.get('disease_subgraph', 0):,}",
        'chemicals': f"{type_counts.get('chemical_subgraph', 0):,}",
        'genes': f"{type_counts.get('gene_subgraph', 0):,}",
        'pathways': f"{type_counts.get('pathway_subgraph', 0):,}"
    }

def retrieve_chunks(question, top_k=10):
    """Retrieve relevant chunks"""
    question_embedding = embedding_model.encode([question])
    faiss.normalize_L2(question_embedding)
    scores, indices = index.search(question_embedding.astype('float32'), top_k)
    
    retrieved = []
    for i, idx in enumerate(indices[0]):
        chunk = chunks[idx].copy()
        chunk['score'] = float(scores[0][i])
        retrieved.append(chunk)
    return retrieved

def generate_answer(question, retrieved_chunks):
    """Generate answer using LLM"""
    context = "\n\n".join([chunk["text"] for chunk in retrieved_chunks])
    
    prompt = f"""You are a biomedical expert. Use the knowledge graph data to answer the question.

IMPORTANT: Don't just list names. Explain the relationships, why they matter, and provide biological context. Write in natural paragraphs like a scientist explaining to a colleague.

KNOWLEDGE GRAPH DATA:
{context}

QUESTION: {question}

Answer in a conversational, explanatory way:"""

    response = llm_client.chat.completions.create(
        model="hosted_vllm/Llama-3.1-70B-Instruct",
        messages=[
            {"role": "system", "content": "You are a biomedical expert. Explain findings in natural language with biological context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=600
    )
    return response.choices[0].message.content


def generate_followup_questions(question, answer):
    """Generate follow-up questions based on the original question and answer"""
    prompt = f"""Based on this biomedical Q&A, suggest 3 related follow-up questions the user might want to ask next.

Original Question: {question}

Answer Given: {answer[:500]}...

Generate exactly 3 short, specific follow-up questions that:
- Explore related diseases, drugs, genes, or pathways mentioned
- Dig deeper into the topic
- Are different from the original question

Return ONLY the 3 questions, one per line, no numbering or bullets:"""

    try:
        response = llm_client.chat.completions.create(
            model="hosted_vllm/Llama-3.1-70B-Instruct",
            messages=[
                {"role": "system", "content": "You generate concise biomedical follow-up questions. Return only the questions, nothing else."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        # Parse the response into a list of questions
        text = response.choices[0].message.content.strip()
        questions = [q.strip() for q in text.split('\n') if q.strip() and len(q.strip()) > 10]
        return questions[:3]  # Return max 3 questions
    except Exception as e:
        print(f"Error generating follow-up questions: {e}")
        return []


def build_graph_visualization(retrieved_chunks, theme='dark'):
    """Build interactive graph from retrieved chunks with theme support"""
    # Theme-based colors
    if theme == 'light':
        bgcolor = "#f8f9fa"
        font_color = "#1a1a1a"
        edge_opacity = "0.7"
    else:
        bgcolor = "#1a1a2e"
        font_color = "white"
        edge_opacity = "1"
    
    net = Network(height="480px", width="100%", bgcolor=bgcolor, font_color=font_color)
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=200)
    
    colors = {
        "disease": "#e74c3c",
        "chemical": "#3498db",
        "gene": "#2ecc71",
        "pathway": "#9b59b6"
    }
    
    added_nodes = set()
    extracted_entities = {"disease": set(), "chemical": set(), "gene": set(), "pathway": set()}
    
    for chunk in retrieved_chunks:
        chunk_type = chunk['type'].replace('_subgraph', '')
        center_entity = chunk['center_entity']
        text = chunk.get('text', '')
        
        # Track entity for highlighting
        if chunk_type in extracted_entities:
            extracted_entities[chunk_type].add(center_entity)
        
        if center_entity not in added_nodes:
            net.add_node(
                center_entity, 
                label=center_entity[:20], 
                color=colors.get(chunk_type, "#95a5a6"),
                size=30,
                title=f"{chunk_type.upper()}: {center_entity}"
            )
            added_nodes.add(center_entity)
        
        lines = text.split('\n')
        for line in lines:
            if ':' in line and line.strip():
                parts = line.split(':', 1)
                if len(parts) == 2:
                    rel_type = parts[0].strip()
                    entities = parts[1].strip()
                    
                    if 'Treats' in rel_type or 'treats' in rel_type:
                        target_type, edge_color = 'disease', '#e74c3c'
                    elif 'genes' in rel_type.lower() or 'Implicated' in rel_type:
                        target_type, edge_color = 'gene', '#2ecc71'
                    elif 'pathway' in rel_type.lower():
                        target_type, edge_color = 'pathway', '#9b59b6'
                    elif 'chemical' in rel_type.lower() or 'Chemical' in rel_type:
                        target_type, edge_color = 'chemical', '#3498db'
                    elif 'disease' in rel_type.lower() or 'Disease' in rel_type:
                        target_type, edge_color = 'disease', '#e74c3c'
                    else:
                        continue
                    
                    entity_list = [e.strip() for e in entities.split(',')][:5]
                    for entity in entity_list:
                        if entity:
                            # Track entity for highlighting
                            extracted_entities[target_type].add(entity)
                            
                            if entity not in added_nodes:
                                net.add_node(entity, label=entity[:15], color=colors.get(target_type, "#95a5a6"),
                                            size=20, title=f"{target_type.upper()}: {entity}")
                                added_nodes.add(entity)
                            net.add_edge(center_entity, entity, color=edge_color, width=2)
    
    # Generate HTML
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
        net.save_graph(f.name)
    
    with open(f.name, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    os.unlink(f.name)
    
    # Convert sets to lists for JSON serialization
    entities_dict = {k: list(v) for k, v in extracted_entities.items()}
    
    return html_content, entities_dict

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/genomic')
def genomic():
    return render_template('genomic.html', stats=stats)

@app.route('/api/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        question = data.get('question', '')
        top_k = data.get('top_k', 10)
        theme = data.get('theme', 'light')
        print(f"[DEBUG] Query received - Theme: {theme}")
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        # Retrieve chunks
        retrieved = retrieve_chunks(question, top_k)
        
        # Generate answer
        answer = generate_answer(question, retrieved)
        
        # Build graph with theme support and get entities for highlighting
        graph_html, entities = build_graph_visualization(retrieved, theme)
        
        # Generate follow-up questions
        followup_questions = generate_followup_questions(question, answer)
        
        # Prepare sources
        sources = [{
            'type': chunk['type'],
            'center_entity': chunk['center_entity'],
            'text': chunk['text'],
            'score': chunk['score']
        } for chunk in retrieved]
        
        return jsonify({
            'answer': answer,
            'graph_html': graph_html,
            'sources': sources,
            'followup_questions': followup_questions,
            'entities': entities  # For entity highlighting
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Entity names cache for autocomplete
entity_names_cache = None

def build_entity_cache():
    """Build a cache of all entity names for autocomplete"""
    global entity_names_cache
    if entity_names_cache is not None:
        return entity_names_cache
    
    entities = set()
    for chunk in chunks:
        # Add center entity
        center = chunk.get('center_entity', '')
        if center:
            entities.add((center, chunk['type'].replace('_subgraph', '')))
        
        # Parse text for related entities
        text = chunk.get('text', '')
        lines = text.split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    entity_list = [e.strip() for e in parts[1].split(',')]
                    for entity in entity_list:
                        if entity and len(entity) > 2:
                            # Determine type from relationship
                            rel_type = parts[0].lower()
                            if 'disease' in rel_type or 'treats' in rel_type:
                                etype = 'disease'
                            elif 'gene' in rel_type or 'implicated' in rel_type:
                                etype = 'gene'
                            elif 'pathway' in rel_type:
                                etype = 'pathway'
                            elif 'chemical' in rel_type:
                                etype = 'chemical'
                            else:
                                etype = 'entity'
                            entities.add((entity, etype))
    
    entity_names_cache = list(entities)
    return entity_names_cache


@app.route('/api/translate', methods=['POST'])
def translate_answer():
    """Translate answer to French using LLM"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        target_lang = data.get('target_lang', 'french')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        prompt = f"""Translate the following biomedical text to French. 
Keep scientific and medical terms accurate. Maintain the same tone and structure.

Text to translate:
{text}

French translation:"""

        response = llm_client.chat.completions.create(
            model="hosted_vllm/Llama-3.1-70B-Instruct",
            messages=[
                {"role": "system", "content": "You are a professional biomedical translator. Translate accurately to French while preserving scientific terminology."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        translated = response.choices[0].message.content.strip()
        return jsonify({'success': True, 'translated': translated})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    """Return entity suggestions based on query"""
    try:
        query = request.args.get('q', '').lower().strip()
        if len(query) < 2:
            return jsonify({'suggestions': []})
        
        entities = build_entity_cache()
        
        # Find matching entities
        matches = []
        for name, etype in entities:
            if query in name.lower():
                # Prioritize matches at the start
                score = 0 if name.lower().startswith(query) else 1
                matches.append({'name': name, 'type': etype, 'score': score})
        
        # Sort by score (start matches first), then alphabetically
        matches.sort(key=lambda x: (x['score'], x['name'].lower()))
        
        # Return top 10
        suggestions = [{'name': m['name'], 'type': m['type']} for m in matches[:10]]
        
        return jsonify({'suggestions': suggestions})
        
    except Exception as e:
        return jsonify({'suggestions': [], 'error': str(e)})

# Protein Alignment Routes
@app.route('/protein')
def protein():
    return render_template('protein.html')

@app.route('/protein/results/<result_id>')
def protein_results(result_id):
    if result_id not in protein_results_cache:
        return "Results not found", 404
    results = protein_results_cache[result_id]
    return render_template('protein_results.html', results=results, result_id=result_id)

@app.route('/api/protein/analyze', methods=['POST'])
def protein_analyze():
    try:
        data = request.get_json()
        human_protein_id = data.get('human_protein_id', '').strip()
        bact_protein_id = data.get('bact_protein_id', '').strip()
        compute_functional = data.get('compute_functional', True)
        use_llm = data.get('use_llm', True)

        if not human_protein_id or not bact_protein_id:
            return jsonify({'success': False, 'error': 'Both protein IDs are required'}), 400

        # Validate proteins exist
        h_exists, h_chunks, h_error = validate_protein_exists(human_protein_id, "human")
        if not h_exists:
            return jsonify({'success': False, 'error': f'Human protein not found: {h_error}'}), 404

        b_exists, b_chunks, b_error = validate_protein_exists(bact_protein_id, "bacteria")
        if not b_exists:
            return jsonify({'success': False, 'error': f'Bacterial protein not found: {b_error}'}), 404

        # Run pipeline
        results = run_alignment_pipeline(
            human_protein_id, bact_protein_id,
            compute_functional=compute_functional, use_llm=use_llm
        )

        # Store results
        result_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        protein_results_cache[result_id] = results

        return jsonify({'success': True, 'result_id': result_id, 'results': results})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/protein/validate', methods=['POST'])
def protein_validate():
    try:
        data = request.get_json()
        human_protein_id = data.get('human_protein_id', '').strip()
        bact_protein_id = data.get('bact_protein_id', '').strip()

        results = {}
        if human_protein_id:
            h_exists, h_chunks, h_error = validate_protein_exists(human_protein_id, "human")
            results['human'] = {'exists': h_exists, 'num_chunks': h_chunks, 'error': h_error}

        if bact_protein_id:
            b_exists, b_chunks, b_error = validate_protein_exists(bact_protein_id, "bacteria")
            results['bacteria'] = {'exists': b_exists, 'num_chunks': b_chunks, 'error': b_error}

        return jsonify({'success': True, 'validation': results})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/protein/download/<result_id>')
def download_protein_results(result_id):
    if result_id not in protein_results_cache:
        return jsonify({'error': 'Result not found'}), 404

    results = protein_results_cache[result_id]
    filename = f"alignment_results_{result_id}.json"
    filepath = os.path.join('protein_cache', filename)

    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)

    return send_file(filepath, as_attachment=True, download_name=filename)


def extract_uniprot_id(protein_id):
    """
    Extract UniProt accession from various protein ID formats:
    - tr|A0A024RA31|A0A024RA31_HUMAN -> A0A024RA31
    - A0A024RA31_HUMAN -> A0A024RA31
    - A0A024RA31 -> A0A024RA31
    """
    # Handle pipe-separated format: tr|A0A024RA31|A0A024RA31_HUMAN
    if '|' in protein_id:
        parts = protein_id.split('|')
        if len(parts) >= 2:
            return parts[1]
    
    # Handle underscore format: A0A024RA31_HUMAN or A0A024RA31_KLEPN
    if '_' in protein_id:
        return protein_id.split('_')[0]
    
    return protein_id


@app.route('/api/protein/structure/<protein_id>')
def get_protein_structure(protein_id):
    """Fetch AlphaFold structure for a protein using the AlphaFold API"""
    import requests
    
    try:
        uniprot_id = extract_uniprot_id(protein_id)
        
        # First, query AlphaFold API to get the correct PDB URL (handles versioning)
        api_url = f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
        api_response = requests.get(api_url, timeout=10)
        
        if api_response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Structure not found for {uniprot_id} in AlphaFold database',
                'uniprot_id': uniprot_id
            }), 404
        
        api_data = api_response.json()
        
        # Check if we got results
        if not api_data or len(api_data) == 0:
            return jsonify({
                'success': False,
                'error': f'No AlphaFold prediction available for {uniprot_id}',
                'uniprot_id': uniprot_id
            }), 404
        
        # Get the PDB URL from the API response
        prediction = api_data[0]
        pdb_url = prediction.get('pdbUrl')
        
        if not pdb_url:
            return jsonify({
                'success': False,
                'error': f'PDB file not available for {uniprot_id}',
                'uniprot_id': uniprot_id
            }), 404
        
        # Fetch the actual PDB file
        pdb_response = requests.get(pdb_url, timeout=15)
        
        if pdb_response.status_code == 200:
            return jsonify({
                'success': True,
                'uniprot_id': uniprot_id,
                'pdb_url': pdb_url,
                'pdb_data': pdb_response.text,
                'source': 'AlphaFold',
                'protein_name': prediction.get('uniprotDescription', ''),
                'organism': prediction.get('organismScientificName', ''),
                'plddt_score': prediction.get('globalMetricValue', 0),
                'version': prediction.get('latestVersion', '')
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to download PDB file for {uniprot_id}',
                'uniprot_id': uniprot_id
            }), 404
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Request timed out. Please try again.'
        }), 504
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("Loading resources...")
    load_resources()
    print("Resources loaded! Starting server...")
    app.run(debug=True, port=5000)
