"""
Pipeline Orchestrator
======================
Orchestrates the complete alignment pipeline from chunks to LLM analysis.
"""

import numpy as np
from datetime import datetime
from services import chunk_loader, embedder, similarity, aligner, descriptors, functional_annotator, llm_analyzer
import protein_config as config

def run_alignment_pipeline(human_protein_id, bact_protein_id, compute_functional=True, use_llm=True):
    """
    Run the complete protein alignment pipeline.
    
    Args:
        human_protein_id: Human protein ID
        bact_protein_id: Bacterial protein ID
        compute_functional: Whether to compute functional annotations
        use_llm: Whether to generate LLM analysis
        
    Returns:
        Complete results dictionary with alignments, descriptors, and LLM analysis
    """
    start_time = datetime.now()
    print(f"\n{'='*70}")
    print("🧬 PROTEIN ALIGNMENT PIPELINE")
    print(f"{'='*70}")
    print(f"Human protein: {human_protein_id}")
    print(f"Bacterial protein: {bact_protein_id}\n")
    
    # Step 1: Load chunks
    step_start = datetime.now()
    print("⏳ [1/9] Loading protein chunks...")
    h_chunks = chunk_loader.get_protein_chunks(human_protein_id, "human")
    b_chunks = chunk_loader.get_protein_chunks(bact_protein_id, "bacteria")
    print(f"   ✓ Human: {len(h_chunks)} chunks | Bacterial: {len(b_chunks)} chunks")
    print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
    
    # Step 2: Load full sequences
    step_start = datetime.now()
    print("⏳ [2/9] Loading full sequences...")
    human_full_seq = chunk_loader.get_protein_full_sequence(human_protein_id, "human")
    bact_full_seq = chunk_loader.get_protein_full_sequence(bact_protein_id, "bacteria")
    print(f"   ✓ Human: {len(human_full_seq)} aa | Bacterial: {len(bact_full_seq)} aa")
    print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
    
    # Step 3: Generate embeddings
    step_start = datetime.now()
    print("⏳ [3/9] Generating ESM-2 embeddings...")
    print("   (First run: ~2-3 min for model download, then ~30s)")
    h_emb = embedder.embed_chunk_dataframe(h_chunks, use_cache=True)
    b_emb = embedder.embed_chunk_dataframe(b_chunks, use_cache=True)
    print(f"   ✓ Human embeddings: {h_emb.shape}")
    print(f"   ✓ Bacterial embeddings: {b_emb.shape}")
    print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
    
    # Step 4: Compute similarity matrix
    step_start = datetime.now()
    print("⏳ [4/9] Computing cosine similarity matrix...")
    S = similarity.compute_cosine_similarity(h_emb, b_emb)
    sim_stats = similarity.get_similarity_statistics(S)
    print(f"   ✓ Similarity matrix: {S.shape}")
    print(f"   ✓ Max similarity: {sim_stats['max_similarity']:.4f}")
    print(f"   ✓ Mean similarity: {sim_stats['mean_similarity']:.4f}")
    print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
    
    # Step 5: Run Smith-Waterman alignment
    step_start = datetime.now()
    print("⏳ [5/9] Running Smith-Waterman alignment...")
    all_alignments_raw = aligner.find_all_alignments(S)
    print(f"   ✓ Found {len(all_alignments_raw)} raw alignments")
    print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
    
    # Step 6: Filter alignments
    step_start = datetime.now()
    print("⏳ [6/9] Filtering alignments with adaptive thresholds...")
    all_alignments = aligner.filter_alignments_adaptive(all_alignments_raw, S)
    print(f"   ✓ Kept {len(all_alignments)} high-quality alignments")
    print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
    
    # Step 7: Compute descriptors for aligned regions
    step_start = datetime.now()
    print("⏳ [7/9] Computing biochemical and structural descriptors...")
    alignment_details = build_alignment_details(
        all_alignments, h_chunks, b_chunks, S, human_full_seq, bact_full_seq
    )
    print(f"   ✓ Computed 16 descriptors for {len(alignment_details)} alignments")
    print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
    
    # Step 8: Compute functional annotations
    human_functional = None
    bact_functional = None
    
    if compute_functional:
        step_start = datetime.now()
        print("⏳ [8/9] Computing functional annotations...")
        print("   (Pfam via WSL: ~2-5s per protein, Prosite API: ~5-10s)")
        try:
            human_functional = functional_annotator.compute_functional_annotations(
                human_full_seq, human_protein_id
            )
            bact_functional = functional_annotator.compute_functional_annotations(
                bact_full_seq, bact_protein_id
            )
            print(f"   ✓ Functional annotations complete")
            print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
        except Exception as e:
            print(f"   ✗ Functional annotation error: {e}")
            print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
    else:
        print("⏭️  [8/9] Skipping functional annotations...\n")
    
    # Build results structure
    results = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "pipeline_version": "ESM2-ChunkSW-v3.0",
            "description": "Smith-Waterman alignment on ESM2 chunk embeddings with biochemical, structural, and functional descriptors"
        },
        "input_sequences": {
            "human": {
                "protein_id": human_protein_id,
                "full_sequence": human_full_seq,
                "length_aa": len(human_full_seq),
                "num_chunks": len(h_chunks),
                "functional_annotations": human_functional
            },
            "bacteria": {
                "protein_id": bact_protein_id,
                "full_sequence": bact_full_seq,
                "length_aa": len(bact_full_seq),
                "num_chunks": len(b_chunks),
                "functional_annotations": bact_functional
            }
        },
        "parameters": {
            "chunk_length": config.CHUNK_LEN,
            "chunk_stride": config.CHUNK_STRIDE,
            "overlap_percentage": round((config.CHUNK_LEN - config.CHUNK_STRIDE) / config.CHUNK_LEN * 100, 1),
            "smith_waterman": {
                "gap_open": config.GAP_OPEN,
                "gap_extend": config.GAP_EXTEND,
                "score_threshold": config.SCORE_THRESHOLD
            },
            "filtering": {
                "min_score": config.MIN_SCORE,
                "min_chunks": config.MIN_CHUNKS,
                "adaptive_thresholds": True,
                "note": "Thresholds computed relative to best alignment (90% sim, 60% continuity, 20% score)"
            }
        },
        "similarity_matrix_stats": sim_stats,
        "alignment_summary": {
            "raw_alignments_found": len(all_alignments_raw),
            "filtered_alignments": len(all_alignments),
            "total_human_aa_aligned": sum(a['human_region']['length_aa'] for a in alignment_details),
            "total_bact_aa_aligned": sum(a['bacteria_region']['length_aa'] for a in alignment_details),
            "best_score": alignment_details[0]['smith_waterman_score'] if alignment_details else None,
            "best_avg_similarity": alignment_details[0]['avg_cosine_similarity'] if alignment_details else None,
            "best_continuity": alignment_details[0]['continuity'] if alignment_details else None
        },
        "alignments": alignment_details,
        "descriptor_legend": {
            "length": "Sequence length in amino acids",
            "aromaticity": "Fraction of aromatic residues (F, W, Y) - indicates pi-pi interactions",
            "aromatic_count": "Absolute count of aromatic residues",
            "aliphatic_fraction": "Fraction of aliphatic residues (A, V, L, I, M) - hydrophobic core",
            "GRAVY": "Grand Average of Hydropathy (-4.5 to +4.5) - negative=hydrophilic, positive=hydrophobic",
            "hydrophobic_fraction": "Fraction of hydrophobic residues (A, V, L, I, M, F, W, P)",
            "polar_fraction": "Fraction of polar residues (S, T, N, Q, C, Y)",
            "instability_index": "Protein stability (<40 = stable, >40 = unstable)",
            "charge_at_pH7": "Net charge at physiological pH",
            "positive_fraction": "Fraction of positively charged residues (K, R, H)",
            "negative_fraction": "Fraction of negatively charged residues (D, E)",
            "shannon_entropy": "Sequence complexity (0-4.3) - higher = more diverse composition",
            "helix_fraction": "Predicted fraction of residues in alpha-helix (0-1)",
            "sheet_fraction": "Predicted fraction of residues in beta-sheet (0-1)",
            "disorder_fraction": "Predicted fraction of intrinsically disordered residues (0-1)",
            "surface_exposed_fraction": "Predicted fraction of solvent-accessible residues (0-1)"
        },
        "functional_annotation_legend": {
            "predicted_domains": "Pfam domain accessions (e.g., PF00069) - computed on full protein",
            "predicted_motifs": "Prosite motif accessions (e.g., PS00107) - computed on full protein",
            "is_signal_peptide": "Whether protein has N-terminal signal peptide (true/false)",
            "num_transmembrane_helices": "Number of predicted transmembrane helices (0+)"
        }
    }
    
    # Step 9: LLM analysis
    llm_analysis = None
    if use_llm:
        step_start = datetime.now()
        print("⏳ [9/9] Generating LLM biological interpretation...")
        print("   (Groq Llama 3.3 70B: ~10-20s)")
        try:
            llm_analysis = llm_analyzer.analyze_alignment_with_llm(results)
            results["llm_analysis"] = llm_analysis
            print(f"   ✓ LLM analysis complete ({len(llm_analysis.get('interpretation', ''))} chars)")
            print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
        except Exception as e:
            print(f"   ✗ LLM analysis error: {e}")
            print(f"   ⏱️  Took {(datetime.now() - step_start).total_seconds():.1f}s\n")
            results["llm_analysis"] = {"error": str(e)}
    else:
        print("⏭️  [9/9] Skipping LLM analysis...\n")
    
    total_time = (datetime.now() - start_time).total_seconds()
    print(f"\n{'='*70}")
    print("✅ PIPELINE COMPLETE")
    print(f"{'='*70}")
    print(f"⏱️  Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"📊 Results: {len(alignment_details)} alignments, {len(results)} data fields")
    print(f"{'='*70}\n")
    
    return results

def build_alignment_details(all_alignments, h_chunks, b_chunks, S, human_full_seq, bact_full_seq):
    """Build detailed alignment info with descriptors."""
    alignment_details = []
    
    for i, aln in enumerate(all_alignments):
        h_start = int(h_chunks.iloc[aln['h_range'][0]]['start'])
        h_end = int(h_chunks.iloc[aln['h_range'][1]]['end'])
        b_start = int(b_chunks.iloc[aln['b_range'][0]]['start'])
        b_end = int(b_chunks.iloc[aln['b_range'][1]]['end'])
        
        # Extract aligned region sequences
        human_aligned_region = human_full_seq[h_start-1:h_end]
        bact_aligned_region = bact_full_seq[b_start-1:b_end]
        
        # Compute descriptors for aligned chunk pairs
        aligned_pairs = []
        for h_idx, b_idx in aln['alignment']:
            h_seq = str(h_chunks.iloc[h_idx]['chunk_seq'])
            b_seq = str(b_chunks.iloc[b_idx]['chunk_seq'])
            
            h_descriptors = descriptors.compute_chunk_descriptors(h_seq)
            b_descriptors = descriptors.compute_chunk_descriptors(b_seq)
            descriptor_comparison = descriptors.compare_descriptors(h_descriptors, b_descriptors)
            
            aligned_pairs.append({
                "human_chunk_idx": int(h_idx),
                "bact_chunk_idx": int(b_idx),
                "cosine_similarity": float(S[h_idx, b_idx]),
                "human_chunk": {
                    "sequence": h_seq,
                    "range": [int(h_chunks.iloc[h_idx]['start']), int(h_chunks.iloc[h_idx]['end'])],
                    "descriptors": h_descriptors
                },
                "bacteria_chunk": {
                    "sequence": b_seq,
                    "range": [int(b_chunks.iloc[b_idx]['start']), int(b_chunks.iloc[b_idx]['end'])],
                    "descriptors": b_descriptors
                },
                "descriptor_comparison": descriptor_comparison
            })
        
        # Aggregate descriptors for the whole alignment
        avg_descriptors_h = {}
        avg_descriptors_b = {}
        if aligned_pairs:
            desc_keys = [k for k in aligned_pairs[0]['human_chunk']['descriptors'].keys() if k != 'length']
            for key in desc_keys:
                avg_descriptors_h[key] = round(np.mean([p['human_chunk']['descriptors'][key] for p in aligned_pairs]), 4)
                avg_descriptors_b[key] = round(np.mean([p['bacteria_chunk']['descriptors'][key] for p in aligned_pairs]), 4)
        
        alignment_details.append({
            "alignment_rank": i + 1,
            "smith_waterman_score": float(aln['score']),
            "num_chunks_aligned": int(aln['num_chunks']),
            "avg_cosine_similarity": float(aln['avg_similarity']),
            "continuity": float(aln['continuity']),
            "human_region": {
                "start": h_start,
                "end": h_end,
                "length_aa": h_end - h_start + 1,
                "sequence": human_aligned_region,
                "avg_descriptors": avg_descriptors_h
            },
            "bacteria_region": {
                "start": b_start,
                "end": b_end,
                "length_aa": b_end - b_start + 1,
                "sequence": bact_aligned_region,
                "avg_descriptors": avg_descriptors_b
            },
            "chunk_span": {
                "human_chunks": [int(aln['h_range'][0]), int(aln['h_range'][1])],
                "bact_chunks": [int(aln['b_range'][0]), int(aln['b_range'][1])],
                "human_span": int(aln['h_span']),
                "bact_span": int(aln['b_span'])
            },
            "chunk_pairs": aligned_pairs
        })
    
    return alignment_details
