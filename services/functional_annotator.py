"""
Functional Annotation Service
===============================
Compute functional annotations:
- Pfam domains (via local PfamScan - NOT AVAILABLE in Windows, returns empty)
- Prosite motifs (via ScanProsite API)
- Signal peptide prediction (heuristic - SignalP-like)
- Transmembrane helix prediction (heuristic - TMHMM-like)

NOTE: This is an exact copy of the notebook implementation.
      Pfam/PfamScan requires Linux and is disabled on Windows.
"""

import requests
import re
import os

def predict_signal_peptide(sequence):
    """
    Predict signal peptide using heuristic rules based on SignalP characteristics.
    Exact copy from notebook.
    
    - Positive N-region (first 1-5 aa with K, R)
    - Hydrophobic H-region (aa 5-20 with high hydrophobic content)
    - Polar C-region with cleavage site
    
    Returns:
        True if signal peptide detected, False otherwise
    """
    if len(sequence) < 20:
        return False
    
    n_term = sequence[:30].upper()
    
    # N-region: first 5 aa should have positive charge (K, R)
    n_region = n_term[:5]
    positive = sum(1 for aa in n_region if aa in 'KR')
    
    # H-region: aa 5-20 should be hydrophobic
    h_region = n_term[5:20]
    hydrophobic = set('AVILMFWP')
    hydro_count = sum(1 for aa in h_region if aa in hydrophobic)
    hydro_frac = hydro_count / len(h_region) if h_region else 0
    
    # Signal peptide if: some positive charges AND high hydrophobicity
    return positive >= 1 and hydro_frac >= 0.5

def predict_tm_helices(sequence):
    """
    Predict transmembrane helices using hydrophobicity-based heuristic.
    Exact copy from notebook.
    
    TM helices are typically 18-25 hydrophobic residues.
    
    Returns:
        Number of TM helices
    """
    hydrophobic = set('AVILMFWP')
    window_size = 20
    threshold = 0.65  # 65% hydrophobic
    
    tm_count = 0
    i = 0
    
    while i < len(sequence) - window_size:
        window = sequence[i:i+window_size].upper()
        hydro_frac = sum(1 for aa in window if aa in hydrophobic) / window_size
        
        if hydro_frac >= threshold:
            tm_count += 1
            i += window_size + 5  # Skip past this TM + short loop
        else:
            i += 1
    
    return tm_count

def search_prosite_motifs(sequence):
    """
    Search Prosite motifs using ScanProsite API.
    Exact copy from notebook.
    
    Returns:
        List of Prosite pattern accessions (e.g., ['PS00001', 'PS00002'])
    """
    url = "https://prosite.expasy.org/cgi-bin/prosite/PSScan.cgi"
    
    params = {
        'seq': sequence,
        'output': 'json',
        'skip': 'false'
    }
    
    try:
        response = requests.post(url, data=params, timeout=30)
        
        if response.status_code == 200:
            # Try to parse JSON response
            try:
                results = response.json()
                motifs = []
                
                if 'matchset' in results:
                    for match in results['matchset']:
                        acc = match.get('signature_ac', '')
                        if acc and acc not in motifs:
                            motifs.append(acc)
                
                return motifs
            except:
                # Fallback: parse text response
                motifs = []
                text = response.text
                # Look for PS##### patterns
                pattern = re.findall(r'PS\d{5}', text)
                for p in pattern:
                    if p not in motifs:
                        motifs.append(p)
                return motifs
        else:
            print(f"    Prosite API failed: HTTP {response.status_code}")
            return []
    
    except Exception as e:
        print(f"    Prosite API error: {e}")
        return []

def search_pfam_domains(sequence, protein_id="unknown"):
    """
    Search Pfam domains using LOCAL PfamScan (via WSL on Windows).
    Exact copy from notebook lines 978-1037.
    
    Requirements:
        - WSL installed (wsl --install)
        - Pfam database in WSL: ~/pfam/Pfam-A.hmm
        - PfamScan scripts: ~/pfam/PfamScan/pfam_scan.pl
        - Dependencies: hmmer, perl, Moose, JSON, List::MoreUtils
    
    Returns:
        List of Pfam domain accessions (e.g., ['PF00001', 'PF00002'])
    """
    import subprocess
    import uuid
    
    # ⚠️ UPDATE THIS PATH to match your WSL username
    WSL_USERNAME = "moham"  # Your WSL username
    PFAM_DIR = f"/home/{WSL_USERNAME}/pfam"
    PFAM_SCAN_PATH = f"{PFAM_DIR}/PfamScan/pfam_scan.pl"
    
    clean_id = protein_id.replace('|', '_').replace('/', '_')
    
    # Use /tmp in WSL directly (no wslpath conversion needed)
    unique_id = str(uuid.uuid4())[:8]
    wsl_fasta = f"/tmp/pfam_{clean_id}_{unique_id}.fasta"
    wsl_output = f"/tmp/pfam_{clean_id}_{unique_id}.out"
    
    try:
        # Write FASTA using sh -c with simple commands (most reliable)
        # Write header line
        header_cmd = f'wsl sh -c "echo \\>{clean_id} > {wsl_fasta}"'
        subprocess.run(header_cmd, shell=True, timeout=15, capture_output=True, check=True)
        
        # Write sequence line (may be long, increase timeout)
        seq_cmd = f'wsl sh -c "echo {sequence} >> {wsl_fasta}"'
        subprocess.run(seq_cmd, shell=True, timeout=30, capture_output=True, check=True)
        
        # Run PfamScan in WSL (EXACT notebook command with -I Bio)
        cmd = ['wsl', '--exec', 'perl', '-I', f'{PFAM_DIR}/PfamScan', '-I', f'{PFAM_DIR}/PfamScan/Bio',
               PFAM_SCAN_PATH, '-fasta', wsl_fasta, '-dir', PFAM_DIR, '-outfile', wsl_output, '-cpu', '2']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        # Read output file from WSL
        read_cmd = f"wsl cat {wsl_output}"
        read_result = subprocess.run(read_cmd, shell=True, capture_output=True, text=True, timeout=5)
        
        # Parse output (exact notebook implementation)
        domains = []
        if read_result.returncode == 0 and read_result.stdout:
            for line in read_result.stdout.split('\n'):
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split()
                if len(parts) >= 6:
                    # Column 6 contains Pfam accession (PF#####)
                    pfam_acc = parts[5]
                    if pfam_acc.startswith('PF') and pfam_acc not in domains:
                        domains.append(pfam_acc)
        else:
            # Check for errors
            if result.returncode != 0:
                if 'No such file or directory' in result.stderr or 'cannot open' in result.stderr:
                    print(f"    PfamScan not found at: {PFAM_SCAN_PATH}")
                else:
                    print(f"    PfamScan error (exit {result.returncode})")
                    if result.stderr:
                        print(f"    {result.stderr[:200]}")
        
        return domains
        
    except subprocess.TimeoutExpired:
        print(f"    PfamScan timeout for {protein_id} (>60s)")
        return []
    except Exception as e:
        print(f"    PfamScan error: {e}")
        return []
    finally:
        # Cleanup temp files in WSL
        try:
            subprocess.run(f"wsl rm -f {wsl_fasta} {wsl_output}", shell=True, 
                         capture_output=True, timeout=5)
        except:
            pass

def compute_functional_annotations(sequence, protein_id="unknown"):
    """
    Compute functional annotations using dedicated tools.
    Exact copy from notebook.
    
    - Pfam domains: LOCAL PfamScan (disabled on Windows, returns empty)
    - Prosite motifs: ScanProsite API
    - Signal peptide: SignalP heuristic
    - TM helices: TMHMM heuristic
    
    Returns:
        Dictionary with predicted domains, motifs, signal peptide, TM helices
    """
    print(f"  Computing functional annotations for {protein_id} ({len(sequence)} aa)")
    
    annotations = {
        "predicted_domains": [],
        "predicted_motifs": [],
        "is_signal_peptide": False,
        "num_transmembrane_helices": 0
    }
    
    # 1. Pfam domains (LOCAL PfamScan - not available on Windows)
    print(f"    Searching Pfam domains (local PfamScan)...")
    annotations["predicted_domains"] = search_pfam_domains(sequence, protein_id)
    print(f"       Found {len(annotations['predicted_domains'])} domains")
    
    # 2. Prosite motifs (ScanProsite API)
    print(f"    Searching Prosite motifs...")
    try:
        annotations["predicted_motifs"] = search_prosite_motifs(sequence)
        print(f"       Found {len(annotations['predicted_motifs'])} motifs")
    except Exception as e:
        print(f"       Prosite search failed: {e}")
    
    # 3. Signal peptide (SignalP heuristic)
    print(f"    Predicting signal peptide...")
    annotations["is_signal_peptide"] = predict_signal_peptide(sequence)
    print(f"       Signal peptide: {annotations['is_signal_peptide']}")
    
    # 4. TM helices (TMHMM heuristic)
    print(f"    Predicting TM helices...")
    annotations["num_transmembrane_helices"] = predict_tm_helices(sequence)
    print(f"       TM helices: {annotations['num_transmembrane_helices']}")
    
    print(f"  Annotations complete for {protein_id}")
    
    return annotations
