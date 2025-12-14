"""
Smith-Waterman Alignment Service
==================================
Perform local alignment on similarity matrix and filter results.
"""

import numpy as np
import protein_config as config

def smith_waterman_alignment(S, gap_open=None, gap_extend=None, score_threshold=None):
    """
    Smith-Waterman local alignment on chunk similarity matrix.
    
    Args:
        S: Similarity matrix (N x M)
        gap_open: Gap opening penalty (default from config)
        gap_extend: Gap extension penalty (default from config)
        score_threshold: Score threshold (default from config)
        
    Returns:
        (max_score, alignment, H_matrix)
        - alignment: list of (h_idx, b_idx) tuples
    """
    if gap_open is None:
        gap_open = config.GAP_OPEN
    if gap_extend is None:
        gap_extend = config.GAP_EXTEND
    if score_threshold is None:
        score_threshold = config.SCORE_THRESHOLD
    
    n_human, n_bact = S.shape
    H_matrix = np.zeros((n_human + 1, n_bact + 1))
    traceback = np.zeros((n_human + 1, n_bact + 1), dtype=int)
    max_score = 0
    max_pos = (0, 0)
    
    for i in range(1, n_human + 1):
        for j in range(1, n_bact + 1):
            sim = S[i-1, j-1] - score_threshold
            match = H_matrix[i-1, j-1] + sim
            gap_h = H_matrix[i-1, j] + (gap_extend if traceback[i-1, j] == 2 else gap_open)
            gap_b = H_matrix[i, j-1] + (gap_extend if traceback[i, j-1] == 3 else gap_open)
            
            scores = [0, match, gap_h, gap_b]
            best = np.argmax(scores)
            H_matrix[i, j] = scores[best]
            traceback[i, j] = best
            
            if H_matrix[i, j] > max_score:
                max_score = H_matrix[i, j]
                max_pos = (i, j)
    
    # Traceback
    alignment = []
    i, j = max_pos
    while i > 0 and j > 0 and H_matrix[i, j] > 0:
        if traceback[i, j] == 1:  # Match
            alignment.append((i-1, j-1))
            i -= 1
            j -= 1
        elif traceback[i, j] == 2:  # Gap in bacteria
            i -= 1
        elif traceback[i, j] == 3:  # Gap in human
            j -= 1
        else:
            break
    
    alignment.reverse()
    return max_score, alignment, H_matrix

def find_all_alignments(S, gap_open=None, gap_extend=None, score_threshold=None, 
                        min_score=None, min_chunks=None):
    """
    Find multiple non-overlapping local alignments iteratively.
    
    Returns:
        List of alignment dicts with scores, ranges, and statistics
    """
    if gap_open is None:
        gap_open = config.GAP_OPEN
    if gap_extend is None:
        gap_extend = config.GAP_EXTEND
    if score_threshold is None:
        score_threshold = config.SCORE_THRESHOLD
    if min_score is None:
        min_score = config.MIN_SCORE
    if min_chunks is None:
        min_chunks = config.MIN_CHUNKS
    
    S_work = S.copy()
    all_alignments = []
    
    while True:
        score, alignment, _ = smith_waterman_alignment(S_work, gap_open, gap_extend, score_threshold)
        
        if score < min_score or len(alignment) < min_chunks:
            break
        
        h_indices = [a[0] for a in alignment]
        b_indices = [a[1] for a in alignment]
        h_range = (min(h_indices), max(h_indices))
        b_range = (min(b_indices), max(b_indices))
        
        avg_sim = np.mean([S[h, b] for h, b in alignment])
        h_span = h_range[1] - h_range[0] + 1
        b_span = b_range[1] - b_range[0] + 1
        num_aligned = len(alignment)
        continuity = num_aligned / max(h_span, b_span)
        
        all_alignments.append({
            'score': float(score),
            'alignment': alignment,
            'h_range': h_range,
            'b_range': b_range,
            'num_chunks': num_aligned,
            'avg_similarity': float(avg_sim),
            'h_span': h_span,
            'b_span': b_span,
            'continuity': float(continuity)
        })
        
        # Mask found region
        for h_idx in range(h_range[0], h_range[1] + 1):
            for b_idx in range(b_range[0], b_range[1] + 1):
                S_work[h_idx, b_idx] = 0
    
    return all_alignments

def filter_alignments_adaptive(alignments, S):
    """
    Filter alignments using adaptive quality thresholds.
    
    Args:
        alignments: List of alignment dicts
        S: Original similarity matrix
        
    Returns:
        Filtered list of alignments
    """
    if not alignments:
        return []
    
    best_aln = alignments[0]
    best_avg_sim = best_aln['avg_similarity']
    best_continuity = best_aln['continuity']
    best_score = best_aln['score']
    
    min_avg_sim = best_avg_sim * 0.90
    min_continuity = max(0.5, best_continuity * 0.6)
    min_relative_score = best_score * 0.20
    
    print(f"  Adaptive thresholds:")
    print(f"    Best: score={best_score:.3f}, similarity={best_avg_sim:.3f}, continuity={best_continuity:.3f}")
    print(f"    Min similarity: {min_avg_sim:.3f}, continuity: {min_continuity:.3f}, score: {min_relative_score:.3f}")
    
    filtered = []
    for i, aln in enumerate(alignments):
        passes = True
        reasons = []
        
        if aln['avg_similarity'] < min_avg_sim:
            passes = False
            reasons.append(f"sim {aln['avg_similarity']:.3f}")
        if aln['continuity'] < min_continuity:
            passes = False
            reasons.append(f"cont {aln['continuity']:.3f}")
        if aln['score'] < min_relative_score:
            passes = False
            reasons.append(f"score {aln['score']:.3f}")
        
        if passes:
            filtered.append(aln)
        else:
            print(f"    Filtered out alignment #{i+1}: {', '.join(reasons)}")
    
    return filtered
