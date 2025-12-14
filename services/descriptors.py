"""
Biochemical and Structural Descriptors Service
================================================
Compute 16 descriptors for protein sequences:
- 12 biochemical descriptors
- 4 structural descriptors
"""

from Bio.SeqUtils.ProtParam import ProteinAnalysis
from collections import Counter
import math
import numpy as np
import torch

# Global ESM2 model reference
_esm2_model = None
_esm2_alphabet = None
_esm2_device = None

def set_esm2_model(model, alphabet, device):
    """Set global ESM2 model for structural predictions."""
    global _esm2_model, _esm2_alphabet, _esm2_device
    _esm2_model = model
    _esm2_alphabet = alphabet
    _esm2_device = device

def get_esm2_model():
    """Get the ESM2 model from embedder if available."""
    global _esm2_model, _esm2_alphabet, _esm2_device
    
    if _esm2_model is None:
        # Import here to avoid circular dependency
        from services.embedder import get_esm2_model as load_model
        model, alphabet, _, device = load_model()
        set_esm2_model(model, alphabet, device)
    
    return _esm2_model, _esm2_alphabet, _esm2_device

def compute_chunk_descriptors(sequence, include_structural=True):
    """
    Compute all 16 descriptors for a protein chunk sequence.
    
    Returns:
        Dictionary with 12 biochemical + 4 structural descriptors
    """
    clean_seq = ''.join([aa for aa in sequence.upper() if aa in 'ACDEFGHIKLMNPQRSTVWY'])
    
    if len(clean_seq) < 2:
        default = {
            "length": len(sequence), "aromaticity": 0.0, "aliphatic_fraction": 0.0,
            "GRAVY": 0.0, "hydrophobic_fraction": 0.0, "polar_fraction": 0.0,
            "instability_index": 0.0, "charge_at_pH7": 0.0, "positive_fraction": 0.0,
            "negative_fraction": 0.0, "shannon_entropy": 0.0
        }
        if include_structural:
            default.update({"helix_fraction": 0.0, "sheet_fraction": 0.0,
                          "disorder_fraction": 0.0, "surface_exposed_fraction": 0.5})
        return default
    
    try:
        analysis = ProteinAnalysis(clean_seq)
    except:
        fallback = {
            "length": len(sequence), "aromaticity": 0.0, "aliphatic_fraction": 0.0,
            "GRAVY": 0.0, "hydrophobic_fraction": 0.0, "polar_fraction": 0.0,
            "instability_index": 0.0, "charge_at_pH7": 0.0, "positive_fraction": 0.0,
            "negative_fraction": 0.0, "shannon_entropy": 0.0
        }
        if include_structural:
            fallback.update({"helix_fraction": 0.0, "sheet_fraction": 0.0,
                           "disorder_fraction": 0.0, "surface_exposed_fraction": 0.5})
        return fallback
    
    L = len(clean_seq)
    
    # Residue groups
    aliphatic = set('AVLIM')
    hydrophobic = set('AVLIMFWP')
    polar = set('STNQCY')
    positive = set('KRH')
    negative = set('DE')
    
    aa_counts = Counter(clean_seq)
    aliphatic_count = sum(aa_counts.get(aa, 0) for aa in aliphatic)
    hydrophobic_count = sum(aa_counts.get(aa, 0) for aa in hydrophobic)
    polar_count = sum(aa_counts.get(aa, 0) for aa in polar)
    positive_count = sum(aa_counts.get(aa, 0) for aa in positive)
    negative_count = sum(aa_counts.get(aa, 0) for aa in negative)
    
    # Shannon entropy
    def shannon_entropy(seq):
        counts = Counter(seq)
        total = len(seq)
        entropy = 0.0
        for count in counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        return entropy
    
    # Build result with BioPython methods
    result = {
        "length": len(sequence),
        "aromaticity": round(analysis.aromaticity(), 4),
        "aliphatic_fraction": round(aliphatic_count / L, 4) if L > 0 else 0.0,
        "GRAVY": round(analysis.gravy(), 4),
        "hydrophobic_fraction": round(hydrophobic_count / L, 4) if L > 0 else 0.0,
        "polar_fraction": round(polar_count / L, 4) if L > 0 else 0.0,
        "instability_index": round(analysis.instability_index(), 4),
        "charge_at_pH7": round(analysis.charge_at_pH(7.0), 4),
        "positive_fraction": round(positive_count / L, 4) if L > 0 else 0.0,
        "negative_fraction": round(negative_count / L, 4) if L > 0 else 0.0,
        "shannon_entropy": round(shannon_entropy(clean_seq), 4)
    }
    
    # Add structural descriptors
    if include_structural:
        try:
            esm_model, esm_alphabet, esm_device = get_esm2_model()
            structural = compute_structural_descriptors(sequence, esm_model, esm_alphabet, esm_device)
            result.update(structural)
        except Exception as e:
            result.update({"helix_fraction": 0.0, "sheet_fraction": 0.0,
                          "disorder_fraction": 0.0, "surface_exposed_fraction": 0.5})
    
    return result

def compute_structural_descriptors(sequence, model=None, alphabet=None, device="cpu"):
    """Compute all 4 structural descriptors."""
    # Secondary structure via ESM2
    if model is not None and alphabet is not None:
        helix_frac, sheet_frac = predict_secondary_structure_esm2(sequence, model, alphabet, device)
    else:
        helix_frac, sheet_frac = 0.0, 0.0
    
    # Disorder and surface - propensity based
    disorder_frac = predict_disorder_propensity(sequence)
    surface_frac = predict_surface_accessibility_propensity(sequence)
    
    return {
        "helix_fraction": helix_frac,
        "sheet_fraction": sheet_frac,
        "disorder_fraction": disorder_frac,
        "surface_exposed_fraction": surface_frac
    }

def predict_secondary_structure_esm2(sequence, model, alphabet, device="cpu"):
    """Predict secondary structure using ESM2 contact maps."""
    try:
        batch_converter = alphabet.get_batch_converter()
        data = [("seq", sequence)]
        batch_labels, batch_strs, batch_tokens = batch_converter(data)
        batch_tokens = batch_tokens.to(device)
        
        with torch.no_grad():
            results = model(batch_tokens, repr_layers=[model.num_layers], return_contacts=True)
        
        contacts = results["contacts"][0].cpu().numpy()
        L = len(sequence)
        
        if L < 4:
            return 0.0, 0.0
        
        # Helix: i, i+3/i+4 contacts
        helix_score = sum(1 for i in range(L - 4) if contacts[i, i+3] > 0.3 or contacts[i, i+4] > 0.3)
        # Sheet: long-range contacts
        sheet_score = sum(1 for i in range(L) for j in range(i + 5, L) if contacts[i, j] > 0.3)
        
        helix_fraction = min(helix_score / max(L - 4, 1), 1.0)
        sheet_fraction = min(sheet_score / max((L * (L - 5)) / 2, 1) * 10, 1.0)
        
        return round(helix_fraction, 4), round(sheet_fraction, 4)
    except:
        return 0.0, 0.0

def predict_disorder_propensity(sequence):
    """Propensity-based disorder prediction."""
    disorder_prop = {
        'A': 0.06, 'R': 0.18, 'N': 0.13, 'D': 0.19, 'C': -0.20,
        'E': 0.24, 'Q': 0.18, 'G': 0.16, 'H': 0.05, 'I': -0.39,
        'L': -0.28, 'K': 0.21, 'M': -0.22, 'F': -0.35, 'P': 0.33,
        'S': 0.14, 'T': 0.05, 'W': -0.27, 'Y': -0.20, 'V': -0.32
    }
    
    clean_seq = ''.join([aa for aa in sequence.upper() if aa in 'ACDEFGHIKLMNPQRSTVWY'])
    if len(clean_seq) < 2:
        return 0.0
    
    scores = [disorder_prop.get(aa, 0.0) for aa in clean_seq]
    avg_score = sum(scores) / len(scores)
    disorder_fraction = max(0, min(1, (avg_score + 0.4) / 0.75))
    return round(disorder_fraction, 4)

def predict_surface_accessibility_propensity(sequence):
    """Propensity-based surface accessibility prediction."""
    rsa_prop = {
        'A': 0.48, 'R': 0.84, 'N': 0.76, 'D': 0.78, 'C': 0.32,
        'E': 0.82, 'Q': 0.78, 'G': 0.51, 'H': 0.66, 'I': 0.34,
        'L': 0.40, 'K': 0.85, 'M': 0.44, 'F': 0.35, 'P': 0.62,
        'S': 0.66, 'T': 0.60, 'W': 0.38, 'Y': 0.48, 'V': 0.36
    }
    
    clean_seq = ''.join([aa for aa in sequence.upper() if aa in 'ACDEFGHIKLMNPQRSTVWY'])
    if len(clean_seq) < 2:
        return 0.5
    
    scores = [rsa_prop.get(aa, 0.5) for aa in clean_seq]
    return round(sum(scores) / len(scores), 4)

def compare_descriptors(desc_h, desc_b):
    """Compute differences between descriptors for comparison."""
    comparison = {}
    biochem_keys = ["aromaticity", "aliphatic_fraction", "GRAVY", "hydrophobic_fraction",
                    "polar_fraction", "instability_index", "charge_at_pH7",
                    "positive_fraction", "negative_fraction", "shannon_entropy"]
    structural_keys = ["helix_fraction", "sheet_fraction", "disorder_fraction",
                       "surface_exposed_fraction"]
    
    for key in biochem_keys + structural_keys:
        if key in desc_h and key in desc_b:
            diff = abs(desc_h[key] - desc_b[key])
            comparison[f"{key}_diff"] = round(diff, 4)
            threshold = 0.20 if key in structural_keys else 0.15
            comparison[f"{key}_similar"] = diff < threshold
    
    return comparison
