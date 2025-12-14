"""
LLM Analysis Service
=====================
Use Groq LLM to provide biological interpretation of alignment results.
"""

import json
import re
from groq import Groq
import protein_config as config

def analyze_alignment_with_llm(results, api_key=None):
    """
    Use Groq LLM to analyze alignment results and provide biological interpretation.
    
    Args:
        results: Complete alignment results dictionary
        api_key: Groq API key (uses config if not provided)
        
    Returns:
        Parsed JSON response with biological interpretation
    """
    if api_key is None:
        api_key = config.GROQ_API_KEY
    
    # Prepare analysis data
    data = prepare_analysis_data(results)
    
    # Build prompt
    prompt = build_llm_prompt(data)
    
    # Call Groq API
    print("Calling Groq API for LLM analysis...")
    try:
        client = Groq(api_key=api_key)
    except TypeError:
        # Older Groq version compatibility
        import os
        os.environ["GROQ_API_KEY"] = api_key
        from groq import Client
        client = Client()
    
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a rigorous but balanced bioinformatics expert.
CRITICAL INSTRUCTIONS:
1. Weigh ALL evidence fairly - both FOR and AGAINST
2. Acknowledge ambiguity when evidence conflicts
3. Don't over-rely on any single factor (including Pfam domains)
4. High alignment coverage is significant signal even without domain match
5. Multiple independent alignments reduce false positive likelihood
6. Use "Uncertain" or "Possible_convergence" when truly ambiguous
7. Output valid JSON only"""
            },
            {"role": "user", "content": prompt}
        ],
        temperature=config.GROQ_TEMPERATURE,
        max_tokens=config.GROQ_MAX_TOKENS,
    )
    
    raw_response = response.choices[0].message.content
    print("LLM response received!")
    
    # Parse JSON
    parsed = parse_llm_response(raw_response)
    
    return parsed

def format_alignment_with_descriptors(aln, idx, human_len, bact_len):
    """Format a single alignment with its descriptor information for display (notebook implementation)."""  
    h_region = aln["human_region"]
    b_region = aln["bacteria_region"]
    h_desc = h_region.get("avg_descriptors", {})
    b_desc = b_region.get("avg_descriptors", {})
    
    desc_comparison = ""
    if h_desc and b_desc:
        desc_comparison = f"""
    Biochemical Profile (region averages):
      GRAVY: Human={h_desc.get('GRAVY', 'N/A'):.3f} vs Bact={b_desc.get('GRAVY', 'N/A'):.3f}
      Charge: Human={h_desc.get('charge_at_pH7', 'N/A'):.2f} vs Bact={b_desc.get('charge_at_pH7', 'N/A'):.2f}
      Hydrophobic: Human={h_desc.get('hydrophobic_fraction', 'N/A'):.2f} vs Bact={b_desc.get('hydrophobic_fraction', 'N/A'):.2f}
      Helix: Human={h_desc.get('helix_fraction', 'N/A'):.2f} vs Bact={b_desc.get('helix_fraction', 'N/A'):.2f}
      Sheet: Human={h_desc.get('sheet_fraction', 'N/A'):.2f} vs Bact={b_desc.get('sheet_fraction', 'N/A'):.2f}
      Disorder: Human={h_desc.get('disorder_fraction', 'N/A'):.2f} vs Bact={b_desc.get('disorder_fraction', 'N/A'):.2f}"""
    
    h_cov = h_region['length_aa'] / human_len * 100 if human_len > 0 else 0
    b_cov = b_region['length_aa'] / bact_len * 100 if bact_len > 0 else 0
    
    return f"""
  ALIGNMENT #{idx + 1}:
    SW Score: {aln['smith_waterman_score']:.3f}
    Avg Cosine Similarity: {aln['avg_cosine_similarity']:.3f}
    Continuity: {aln['continuity']:.0%}
    Human region: aa {h_region['start']}-{h_region['end']} ({h_region['length_aa']} aa, {h_cov:.1f}% of protein)
    Bacteria region: aa {b_region['start']}-{b_region['end']} ({b_region['length_aa']} aa, {b_cov:.1f}% of protein)
    Chunks aligned: {aln['num_chunks_aligned']}{desc_comparison}"""

def format_top_chunk_pairs(alignments):
    """Format the top 5 chunk pairs from the best alignment for display (notebook implementation)."""
    chunk_details = ""
    if alignments and "chunk_pairs" in alignments[0]:
        top_pairs = alignments[0]["chunk_pairs"][:5]
        chunk_details = "\n## Sample Chunk Pairs (first 5 from best alignment):\n"
        for i, pair in enumerate(top_pairs):
            h_desc = pair["human_chunk"]["descriptors"]
            b_desc = pair["bacteria_chunk"]["descriptors"]
            chunk_details += f"""
  Pair {i+1}: Cosine={pair['cosine_similarity']:.3f}
    Human: {pair['human_chunk']['sequence']} | Bact: {pair['bacteria_chunk']['sequence']}
    GRAVY: {h_desc['GRAVY']:.2f} vs {b_desc['GRAVY']:.2f} | Charge: {h_desc['charge_at_pH7']:.1f} vs {b_desc['charge_at_pH7']:.1f}
"""
    return chunk_details

def prepare_analysis_data(results):
    """Pre-compute statistics for LLM analysis (matches notebook implementation)."""
    human_info = results["input_sequences"]["human"]
    bact_info = results["input_sequences"]["bacteria"]
    sim_stats = results["similarity_matrix_stats"]
    alignments = results["alignments"]
    summary = results["alignment_summary"]
    
    human_func = human_info.get("functional_annotations", {}) or {}
    bact_func = bact_info.get("functional_annotations", {}) or {}
    
    # Domain/motif overlap
    human_domains = set(human_func.get('predicted_domains', []))
    bact_domains = set(bact_func.get('predicted_domains', []))
    shared_domains = human_domains & bact_domains
    domains_overlap = len(shared_domains) > 0
    
    human_motifs = set(human_func.get('predicted_motifs', []))
    bact_motifs = set(bact_func.get('predicted_motifs', []))
    shared_motifs = human_motifs & bact_motifs
    
    GENERIC_MOTIFS = {'PS00001', 'PS00004', 'PS00005', 'PS00006', 'PS00007', 'PS00008', 'PS00009'}
    specific_shared_motifs = shared_motifs - GENERIC_MOTIFS
    has_specific_shared_motifs = len(specific_shared_motifs) > 0
    
    # Coverage calculations
    human_len = human_info['length_aa']
    bact_len = bact_info['length_aa']
    total_human_aligned = summary.get('total_human_aa_aligned', 0)
    total_bact_aligned = summary.get('total_bact_aa_aligned', 0)
    human_coverage = (total_human_aligned / human_len * 100) if human_len > 0 else 0
    bact_coverage = (total_bact_aligned / bact_len * 100) if bact_len > 0 else 0
    
    # Per-alignment coverage
    alignment_coverages = []
    for i, aln in enumerate(alignments):
        h_region = aln["human_region"]
        b_region = aln["bacteria_region"]
        h_cov = h_region['length_aa'] / human_len * 100 if human_len > 0 else 0
        b_cov = b_region['length_aa'] / bact_len * 100 if bact_len > 0 else 0
        alignment_coverages.append({
            "rank": i + 1,
            "human_coverage_pct": round(h_cov, 1),
            "bact_coverage_pct": round(b_cov, 1),
            "chunks_aligned": aln['num_chunks_aligned'],
            "continuity": aln['continuity'],
            "avg_similarity": aln['avg_cosine_similarity']
        })
    
    # Descriptor pattern analysis across ALL chunk pairs (notebook implementation)
    descriptor_matches = {
        "gravy_similar": 0, "gravy_different": 0,
        "charge_similar": 0, "charge_different": 0,
        "hydrophobic_similar": 0, "hydrophobic_different": 0,
        "helix_similar": 0, "helix_different": 0,
        "sheet_similar": 0, "sheet_different": 0,
        "disorder_similar": 0, "disorder_different": 0,
        "total_pairs": 0
    }
    
    for aln in alignments:
        if "chunk_pairs" in aln:
            for pair in aln["chunk_pairs"]:
                desc_cmp = pair.get("descriptor_comparison", {})
                descriptor_matches["total_pairs"] += 1
                
                # Count matches vs mismatches for each descriptor
                if desc_cmp.get("GRAVY_similar", False):
                    descriptor_matches["gravy_similar"] += 1
                else:
                    descriptor_matches["gravy_different"] += 1
                
                if desc_cmp.get("charge_at_pH7_similar", False):
                    descriptor_matches["charge_similar"] += 1
                else:
                    descriptor_matches["charge_different"] += 1
                
                if desc_cmp.get("hydrophobic_fraction_similar", False):
                    descriptor_matches["hydrophobic_similar"] += 1
                else:
                    descriptor_matches["hydrophobic_different"] += 1
                
                if desc_cmp.get("helix_fraction_similar", False):
                    descriptor_matches["helix_similar"] += 1
                else:
                    descriptor_matches["helix_different"] += 1
                
                if desc_cmp.get("sheet_fraction_similar", False):
                    descriptor_matches["sheet_similar"] += 1
                else:
                    descriptor_matches["sheet_different"] += 1
                
                if desc_cmp.get("disorder_fraction_similar", False):
                    descriptor_matches["disorder_similar"] += 1
                else:
                    descriptor_matches["disorder_different"] += 1
    
    # Calculate match percentages
    total = descriptor_matches["total_pairs"]
    if total > 0:
        descriptor_match_summary = {
            "gravy_match_pct": round(descriptor_matches["gravy_similar"] / total * 100, 1),
            "charge_match_pct": round(descriptor_matches["charge_similar"] / total * 100, 1),
            "hydrophobic_match_pct": round(descriptor_matches["hydrophobic_similar"] / total * 100, 1),
            "helix_match_pct": round(descriptor_matches["helix_similar"] / total * 100, 1),
            "sheet_match_pct": round(descriptor_matches["sheet_similar"] / total * 100, 1),
            "disorder_match_pct": round(descriptor_matches["disorder_similar"] / total * 100, 1),
            "total_chunk_pairs_analyzed": total
        }
    else:
        descriptor_match_summary = {"note": "No chunk pairs to analyze"}
    
    return {
        "human_info": human_info,
        "bact_info": bact_info,
        "human_func": human_func,
        "bact_func": bact_func,
        "human_domains": human_domains,
        "bact_domains": bact_domains,
        "shared_domains": shared_domains,
        "domains_overlap": domains_overlap,
        "human_motifs": human_motifs,
        "bact_motifs": bact_motifs,
        "shared_motifs": shared_motifs,
        "specific_shared_motifs": specific_shared_motifs,
        "has_specific_shared_motifs": has_specific_shared_motifs,
        "human_len": human_len,
        "bact_len": bact_len,
        "human_coverage": human_coverage,
        "bact_coverage": bact_coverage,
        "sim_stats": sim_stats,
        "alignments": alignments,
        "summary": summary,
        "alignment_coverages": alignment_coverages,
        "descriptor_match_summary": descriptor_match_summary
    }

def build_llm_prompt(data):
    """Build comprehensive LLM prompt (exact notebook implementation)."""
    
    # Format alignment details using notebook function
    alignments_str = "\n".join(
        format_alignment_with_descriptors(aln, i, data['human_len'], data['bact_len'])
        for i, aln in enumerate(data['alignments'])
    )
    
    # Format top chunk pairs
    chunk_details = format_top_chunk_pairs(data['alignments'])
    
    alignments_text = alignments_str
    
    prompt = f"""You are an expert protein bioinformatician. Analyze this ESM2 embedding alignment systematically.

ANALYSIS FRAMEWORK - Weigh ALL evidence fairly:
1. Domain analysis is IMPORTANT but not the only factor
2. Alignment coverage and continuity are SIGNIFICANT signals
3. Descriptor patterns across chunks reveal local similarities
4. Multiple independent alignments suggest non-random relationship
5. Acknowledge AMBIGUITY when evidence conflicts

## 1️⃣ PROTEINS
- Human: {data['human_info']['protein_id']} ({data['human_len']} aa, {data['human_info']['num_chunks']} chunks)
- Bacteria: {data['bact_info']['protein_id']} ({data['bact_len']} aa, {data['bact_info']['num_chunks']} chunks)

## 2️⃣ SIMILARITY MATRIX STATISTICS
- Min: {data['sim_stats']['min_similarity']:.3f}
- Max: {data['sim_stats']['max_similarity']:.3f}
- Mean: {data['sim_stats']['mean_similarity']:.3f}
- Std: {data['sim_stats']['std_similarity']:.3f}
- 95th percentile: {data['sim_stats'].get('percentile_95', 'N/A')}
- Mean of top 20: {data['sim_stats'].get('mean_top_20', 'N/A')}

## 3️⃣ ALIGNMENT COVERAGE ANALYSIS (IMPORTANT!)
- Number of independent alignments found: {data['summary']['filtered_alignments']}
- Total human residues aligned: {data['summary'].get('total_human_aa_aligned', 0)} aa ({data['human_coverage']:.1f}% coverage)
- Total bacteria residues aligned: {data['summary'].get('total_bact_aa_aligned', 0)} aa ({data['bact_coverage']:.1f}% coverage)

Per-alignment breakdown:
{json.dumps(data['alignment_coverages'], indent=2)}

INTERPRETATION GUIDE for coverage:
- >70% coverage with high continuity = extensive structural similarity
- Multiple independent alignments = relationship unlikely to be random
- Full-length alignment (>90%) = very strong signal regardless of domain match

## 4️⃣ DESCRIPTOR PATTERN ANALYSIS (across {data['descriptor_match_summary'].get('total_chunk_pairs_analyzed', 0)} chunk pairs)
{json.dumps(data['descriptor_match_summary'], indent=2)}

INTERPRETATION GUIDE for descriptors:
- >60% match = descriptors support similarity
- <40% match = descriptors diverge despite ESM2 similarity
- Mixed pattern = local similarities may exist in specific regions

## 5️⃣ DETAILED ALIGNMENTS
{alignments_text}
{chunk_details}

## 6️⃣ FUNCTIONAL ANNOTATIONS

Human protein:
  - Pfam domains: {list(data['human_domains']) if data['human_domains'] else 'NONE'}
  - Prosite motifs: {list(data['human_motifs']) if data['human_motifs'] else 'NONE'}
  - TM helices: {data['human_func'].get('num_transmembrane_helices', 0)}

Bacteria protein:
  - Pfam domains: {list(data['bact_domains']) if data['bact_domains'] else 'NONE'}
  - Prosite motifs: {list(data['bact_motifs']) if data['bact_motifs'] else 'NONE'}
  - TM helices: {data['bact_func'].get('num_transmembrane_helices', 0)}

Domain overlap: {'YES - ' + str(list(data['shared_domains'])) if data['domains_overlap'] else 'NO'}
Shared motifs: {list(data['shared_motifs']) if data['shared_motifs'] else 'NONE'}
Specific shared motifs (non-generic): {list(data['specific_shared_motifs']) if data['specific_shared_motifs'] else 'NONE'}

Note: PS00001, PS00005, PS00008 etc. are generic phosphorylation/modification sites present in many proteins.

## 7️⃣ EVIDENCE WEIGHING GUIDE

Evidence FOR biological relationship:
- Shared Pfam domains (strongest)
- Shared specific Prosite motifs (strong)
- High coverage alignment (>70%) with good continuity (strong)
- Multiple independent alignments (moderate-strong)
- Matching descriptor patterns across chunks (moderate)
- Similar TM topology (weak-moderate for membrane proteins)

Evidence AGAINST biological relationship:
- Different Pfam domains (strong, but not absolute)
- Only generic motifs shared (weak evidence against)
- Opposite GRAVY signs (moderate)
- Low descriptor match percentages (moderate)
- Single short alignment (weak against if low coverage)

IMPORTANT: When evidence conflicts, acknowledge the ambiguity. Use relationship_type "Uncertain" or "Possible_convergence" when appropriate.

Return ONLY valid JSON:
{{
  "alignment_quality": "High|Medium|Low",
  "confidence_score": <0-100, where 50 means truly uncertain>,
  "false_positive_risk": "Low|Medium|High",
  "biological_interpretation": {{
    "relationship_type": "<Homology|Functional_convergence|Analogous_function|Divergent_homologs|Embedding_artifact|False_positive|Uncertain>",
    "evidence_summary": "<3-4 sentences weighing ALL evidence fairly>",
    "key_evidence_for": ["<list specific evidence supporting relationship>"],
    "key_evidence_against": ["<list specific evidence against relationship>"]
  }},
  "coverage_analysis": {{
    "human_coverage_pct": {data['human_coverage']:.1f},
    "bacteria_coverage_pct": {data['bact_coverage']:.1f},
    "num_independent_alignments": {data['summary']['filtered_alignments']},
    "coverage_interpretation": "<is coverage extensive enough to be significant?>"
  }},
  "descriptor_pattern_analysis": {{
    "overall_descriptor_agreement": "High|Mixed|Low",
    "strongest_matching_descriptors": ["<which descriptors match best>"],
    "divergent_descriptors": ["<which descriptors don't match>"],
    "pattern_interpretation": "<what do the descriptor patterns reveal about local vs global similarity?>"
  }},
  "domain_analysis": {{
    "domains_overlap": {str(data['domains_overlap']).lower()},
    "domain_interpretation": "<what does domain match/mismatch mean in context of other evidence?>"
  }},
  "motif_analysis": {{
    "has_specific_shared_motifs": {str(data['has_specific_shared_motifs']).lower()},
    "motif_interpretation": "<are any shared motifs meaningful?>"
  }},
  "membrane_topology": {{
    "both_membrane_proteins": {str(data['human_func'].get('num_transmembrane_helices', 0) > 0 and data['bact_func'].get('num_transmembrane_helices', 0) > 0).lower()},
    "topology_note": "<how does membrane topology affect interpretation?>"
  }},
  "alternative_hypotheses": [
    "<what else could explain this pattern? e.g., convergent evolution, domain shuffling, analogous function>"
  ],
  "conclusion": "<balanced final assessment that acknowledges uncertainty if evidence conflicts>"
}}"""
    
    return prompt

def parse_llm_response(raw_response):
    """Parse LLM JSON response."""
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        return json.loads(cleaned)
    except:
        # Try to find JSON in response
        json_match = re.search(r'\{[\s\S]*\}', raw_response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Return raw if parsing fails
        return {"raw_response": raw_response, "parse_error": True}
