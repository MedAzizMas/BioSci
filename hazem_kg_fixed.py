# =============================================================================
# UNIFIED MULTI-OMICS + CHEMICAL KNOWLEDGE GRAPH - FIXED VERSION
# =============================================================================
# This script fixes the GeneID mismatch issue causing 0 edges for:
# - Chemical-Gene edges
# - Gene-Pathway edges  
# - Gene-Disease edges
# =============================================================================

from google.colab import drive
drive.mount('/content/drive')

import pandas as pd
import os

base_proc = "/content/drive/MyDrive/data_hazem/processed_data"
base_meta = "/content/drive/MyDrive/data_hazem/metabolite_integration"

# =============================================================================
# CELL 1: Load Existing Processed Data
# =============================================================================
reactome_human = pd.read_csv(f"{base_proc}/reactome_human.csv")
genes_pathways = pd.read_csv(f"{base_proc}/genes_pathways.csv")
disease_pathways = pd.read_csv(f"{base_proc}/disease_pathways.csv")
curated_gene_disease = pd.read_csv(f"{base_proc}/curated_gene_disease.csv")
gene_vocab = pd.read_csv(f"{base_proc}/gene_vocab.csv")

# =============================================================================
# CELL 2: Load Chemical Vocabulary
# =============================================================================
chem_cols = [
    "ChemicalName", "ChemicalID", "CasRN", "PubChemCID", "PubChemSID",
    "DTXSID", "InChIKey", "Definition", "ParentIDs", "TreeNumbers",
    "ParentTreeNumbers", "MESHSynonyms", "CTDCuratedSynonyms"
]

chem_vocab = pd.read_csv(
    f"{base_meta}/CTD_chemicals.tsv/CTD_chemicals.tsv",
    sep="\t", comment="#", header=None, names=chem_cols, low_memory=False
)

# =============================================================================
# CELL 3: Load Chemical-Gene Interactions
# =============================================================================
chem_gene_cols = [
    "ChemicalName", "ChemicalID", "CasRN", "GeneSymbol", "GeneID",
    "GeneForms", "Organism", "OrganismID", "Interaction", 
    "InteractionActions", "PubMedIDs"
]
chem_gene_ixns = pd.read_csv(
    f"{base_meta}/CTD_chem_gene_ixns.tsv/CTD_chem_gene_ixns.tsv",
    sep="\t", comment="#", header=None, names=chem_gene_cols, low_memory=False
)

# =============================================================================
# CELL 4: Load Chemical-Pathway Enrichment
# =============================================================================
chem_pathway_cols = [
    "ChemicalName", "ChemicalID", "CasRN", "PathwayName", "PathwayID",
    "PValue", "CorrectedPValue", "TargetMatchQty", "TargetTotalQty",
    "BackgroundMatchQty", "BackgroundTotalQty"
]
chem_pathways = pd.read_csv(
    f"{base_meta}/CTD_chem_pathways_enriched.tsv/CTD_chem_pathways_enriched.tsv",
    sep="\t", comment="#", header=None, names=chem_pathway_cols, low_memory=False
)

# =============================================================================
# CELL 5: Load Chemical-Disease Associations
# =============================================================================
chem_disease_cols = [
    "ChemicalName", "ChemicalID", "CasRN", "DiseaseName", "DiseaseID",
    "DirectEvidence", "PubMedIDs"
]
chem_diseases = pd.read_csv(
    f"{base_meta}/CTD_curated_chemicals_diseases.tsv/CTD_curated_chemicals_diseases.tsv",
    sep="\t", comment="#", header=None, names=chem_disease_cols, low_memory=False
)

# =============================================================================
# CELL 6: Filter Chemicals - Keep only those with edges
# =============================================================================
# Clean names
chem_vocab["ChemicalName"] = chem_vocab["ChemicalName"].astype(str).str.strip().str.upper()
chem_gene_ixns["ChemicalName"] = chem_gene_ixns["ChemicalName"].astype(str).str.strip().str.upper()
chem_pathways["ChemicalName"] = chem_pathways["ChemicalName"].astype(str).str.strip().str.upper()
chem_diseases["ChemicalName"] = chem_diseases["ChemicalName"].astype(str).str.strip().str.upper()

# Keep only chemicals that appear in any interaction table
chemicals_with_edges = (
    set(chem_gene_ixns["ChemicalName"]) |
    set(chem_pathways["ChemicalName"]) |
    set(chem_diseases["ChemicalName"])
)

chem_vocab_filtered = chem_vocab[
    chem_vocab["ChemicalName"].isin(chemicals_with_edges)
].copy()

chem_gene_filtered = chem_gene_ixns[
    chem_gene_ixns["ChemicalName"].isin(chem_vocab_filtered["ChemicalName"])
].copy()

chem_pathways_filtered = chem_pathways[
    chem_pathways["ChemicalName"].isin(chem_vocab_filtered["ChemicalName"])
].copy()

chem_diseases_filtered = chem_diseases[
    chem_diseases["ChemicalName"].isin(chem_vocab_filtered["ChemicalName"])
].copy()

print("Chemicals kept:", len(chem_vocab_filtered))
print("Chem-Gene edges:", len(chem_gene_filtered))
print("Chem-Pathway edges:", len(chem_pathways_filtered))
print("Chem-Disease edges:", len(chem_diseases_filtered))

# =============================================================================
# CELL 7: Save Processed Chemical Data
# =============================================================================
chem_vocab_filtered.to_csv(f"{base_proc}/chemical_vocab.csv", index=False)
chem_gene_filtered.to_csv(f"{base_proc}/chemical_gene_edges.csv", index=False)
chem_pathways_filtered.to_csv(f"{base_proc}/chemical_pathway_edges.csv", index=False)
chem_diseases_filtered.to_csv(f"{base_proc}/chemical_disease_edges.csv", index=False)

print("Saved chemical files!")

# =============================================================================
# CELL 8: Reload All Data for Graph Construction
# =============================================================================
reactome_human = pd.read_csv(f"{base_proc}/reactome_human.csv")
genes_pathways = pd.read_csv(f"{base_proc}/genes_pathways.csv")
disease_pathways = pd.read_csv(f"{base_proc}/disease_pathways.csv")
curated_gene_disease = pd.read_csv(f"{base_proc}/curated_gene_disease.csv")
gene_vocab = pd.read_csv(f"{base_proc}/gene_vocab.csv")

chemical_vocab = pd.read_csv(f"{base_proc}/chemical_vocab.csv")
chemical_gene_edges = pd.read_csv(f"{base_proc}/chemical_gene_edges.csv")
chemical_pathway_edges = pd.read_csv(f"{base_proc}/chemical_pathway_edges.csv")
chemical_disease_edges = pd.read_csv(f"{base_proc}/chemical_disease_edges.csv")

# =============================================================================
# CELL 9: CRITICAL FIX - Define Normalization Functions
# =============================================================================
def norm_id(s):
    """Normalize IDs: strip, uppercase, remove MESH:/REACT: prefixes"""
    return (s.astype(str)
              .str.strip()
              .str.upper()
              .str.replace("MESH:", "", regex=False)
              .str.replace("REACT:", "", regex=False))

def norm_gene_id(s):
    """
    CRITICAL FIX: Normalize GeneID consistently across all dataframes.
    - Convert to string
    - Strip whitespace  
    - Remove trailing .0 (from float conversion)
    - This fixes the mismatch causing 0 edges!
    """
    return (s.astype(str)
              .str.strip()
              .str.replace(r'\.0$', '', regex=True))

# =============================================================================
# CELL 10: Apply Normalization to ALL IDs
# =============================================================================

# --- Normalize Chemical IDs ---
chemical_vocab["ChemicalID"] = norm_id(chemical_vocab["ChemicalID"])
chemical_gene_edges["ChemicalID"] = norm_id(chemical_gene_edges["ChemicalID"])
chemical_pathway_edges["ChemicalID"] = norm_id(chemical_pathway_edges["ChemicalID"])
chemical_disease_edges["ChemicalID"] = norm_id(chemical_disease_edges["ChemicalID"])

# --- Normalize Disease IDs ---
disease_pathways["DiseaseID"] = norm_id(disease_pathways["DiseaseID"])
curated_gene_disease["DiseaseID"] = norm_id(curated_gene_disease["DiseaseID"])
chemical_disease_edges["DiseaseID"] = norm_id(chemical_disease_edges["DiseaseID"])

# --- Normalize Pathway IDs ---
reactome_human["PathwayID"] = norm_id(reactome_human["PathwayID"])
genes_pathways["PathwayID"] = norm_id(genes_pathways["PathwayID"])
disease_pathways["PathwayID"] = norm_id(disease_pathways["PathwayID"])
chemical_pathway_edges["PathwayID"] = norm_id(chemical_pathway_edges["PathwayID"])

# --- CRITICAL: Normalize Gene IDs using the fix function ---
gene_vocab["GeneID"] = norm_gene_id(gene_vocab["GeneID"])
genes_pathways["GeneID"] = norm_gene_id(genes_pathways["GeneID"])
curated_gene_disease["GeneID"] = norm_gene_id(curated_gene_disease["GeneID"])
chemical_gene_edges["GeneID"] = norm_gene_id(chemical_gene_edges["GeneID"])

print("All IDs normalized!")

# =============================================================================
# CELL 11: Debug - Verify GeneID Overlap (Run this to confirm fix works)
# =============================================================================
print("\n=== DEBUG: Checking GeneID formats ===")
print("gene_vocab GeneID samples:", gene_vocab["GeneID"].head(5).tolist())
print("chemical_gene_edges GeneID samples:", chemical_gene_edges["GeneID"].head(5).tolist())
print("genes_pathways GeneID samples:", genes_pathways["GeneID"].head(5).tolist())
print("curated_gene_disease GeneID samples:", curated_gene_disease["GeneID"].head(5).tolist())

gene_vocab_ids = set(gene_vocab["GeneID"])
print(f"\nTotal unique genes in gene_vocab: {len(gene_vocab_ids)}")
print(f"Overlap with chemical_gene_edges: {len(set(chemical_gene_edges['GeneID']) & gene_vocab_ids)}")
print(f"Overlap with genes_pathways: {len(set(genes_pathways['GeneID']) & gene_vocab_ids)}")
print(f"Overlap with curated_gene_disease: {len(set(curated_gene_disease['GeneID']) & gene_vocab_ids)}")

# =============================================================================
# CELL 12: Create Node Tables
# =============================================================================

# Chemical nodes
chem_nodes = chemical_vocab[["ChemicalID", "ChemicalName", "CasRN", "InChIKey"]].drop_duplicates()
chem_nodes = chem_nodes.rename(columns={"ChemicalID": "chemical_id:ID(Chemical)"})

# Gene nodes
gene_nodes = gene_vocab[["GeneID", "GeneSymbol", "GeneName"]].drop_duplicates()
gene_nodes = gene_nodes.rename(columns={"GeneID": "gene_id:ID(Gene)"})

# Pathway nodes
pathway_nodes = reactome_human[["PathwayID", "PathwayName"]].drop_duplicates()
pathway_nodes = pathway_nodes.rename(columns={"PathwayID": "pathway_id:ID(Pathway)"})

# Disease nodes
disease_nodes = disease_pathways[["DiseaseID", "DiseaseName"]].drop_duplicates()
disease_nodes = disease_nodes.rename(columns={"DiseaseID": "disease_id:ID(Disease)"})

print(f"Chemical nodes: {len(chem_nodes)}")
print(f"Gene nodes: {len(gene_nodes)}")
print(f"Pathway nodes: {len(pathway_nodes)}")
print(f"Disease nodes: {len(disease_nodes)}")

# =============================================================================
# CELL 13: Filter Edges - Keep only edges with valid nodes
# =============================================================================

# Get valid ID sets
valid_chemicals = set(chem_nodes["chemical_id:ID(Chemical)"])
valid_genes = set(gene_nodes["gene_id:ID(Gene)"])
valid_pathways = set(pathway_nodes["pathway_id:ID(Pathway)"])
valid_diseases = set(disease_nodes["disease_id:ID(Disease)"])

# 1. Chemical-Gene edges
chem_gene_edges_filtered = chemical_gene_edges[
    (chemical_gene_edges["ChemicalID"].isin(valid_chemicals)) &
    (chemical_gene_edges["GeneID"].isin(valid_genes))
].copy()

# 2. Chemical-Pathway edges
chem_pathway_edges_filtered = chemical_pathway_edges[
    (chemical_pathway_edges["ChemicalID"].isin(valid_chemicals)) &
    (chemical_pathway_edges["PathwayID"].isin(valid_pathways))
].copy()

# 3. Chemical-Disease edges
chem_disease_edges_filtered = chemical_disease_edges[
    (chemical_disease_edges["ChemicalID"].isin(valid_chemicals)) &
    (chemical_disease_edges["DiseaseID"].isin(valid_diseases))
].copy()

# 4. Gene-Pathway edges
gene_path_edges_filtered = genes_pathways[
    (genes_pathways["GeneID"].isin(valid_genes)) &
    (genes_pathways["PathwayID"].isin(valid_pathways))
].copy()

# 5. Disease-Pathway edges
disease_path_edges_filtered = disease_pathways[
    (disease_pathways["DiseaseID"].isin(valid_diseases)) &
    (disease_pathways["PathwayID"].isin(valid_pathways))
].copy()

# 6. Gene-Disease edges
gene_disease_edges_filtered = curated_gene_disease[
    (curated_gene_disease["GeneID"].isin(valid_genes)) &
    (curated_gene_disease["DiseaseID"].isin(valid_diseases))
].copy()

print("\n=== EDGE COUNTS AFTER FILTERING ===")
print(f"Chemical-Gene edges: {len(chem_gene_edges_filtered)}")
print(f"Chemical-Pathway edges: {len(chem_pathway_edges_filtered)}")
print(f"Chemical-Disease edges: {len(chem_disease_edges_filtered)}")
print(f"Gene-Pathway edges: {len(gene_path_edges_filtered)}")
print(f"Disease-Pathway edges: {len(disease_path_edges_filtered)}")
print(f"Gene-Disease edges: {len(gene_disease_edges_filtered)}")

# =============================================================================
# CELL 14: Format Edges for Neo4j Import
# =============================================================================

# Chemical-Gene
chem_gene_edges_neo = chem_gene_edges_filtered.rename(columns={
    "ChemicalID": ":START_ID(Chemical)",
    "GeneID": ":END_ID(Gene)"
})
chem_gene_edges_neo[":TYPE"] = "INTERACTS_WITH"
chem_gene_edges_neo = chem_gene_edges_neo[[":START_ID(Chemical)", ":END_ID(Gene)", ":TYPE"]]

# Chemical-Pathway
chem_pathway_edges_neo = chem_pathway_edges_filtered.rename(columns={
    "ChemicalID": ":START_ID(Chemical)",
    "PathwayID": ":END_ID(Pathway)"
})
chem_pathway_edges_neo[":TYPE"] = "AFFECTS_PATHWAY"
chem_pathway_edges_neo = chem_pathway_edges_neo[[":START_ID(Chemical)", ":END_ID(Pathway)", ":TYPE"]]

# Chemical-Disease
chem_disease_edges_neo = chem_disease_edges_filtered.rename(columns={
    "ChemicalID": ":START_ID(Chemical)",
    "DiseaseID": ":END_ID(Disease)"
})
chem_disease_edges_neo[":TYPE"] = "ASSOCIATED_WITH"
chem_disease_edges_neo = chem_disease_edges_neo[[":START_ID(Chemical)", ":END_ID(Disease)", ":TYPE"]]

# Gene-Pathway
gene_path_edges_neo = gene_path_edges_filtered.rename(columns={
    "GeneID": ":START_ID(Gene)",
    "PathwayID": ":END_ID(Pathway)"
})
gene_path_edges_neo[":TYPE"] = "PARTICIPATES_IN"
gene_path_edges_neo = gene_path_edges_neo[[":START_ID(Gene)", ":END_ID(Pathway)", ":TYPE"]]

# Disease-Pathway
disease_path_edges_neo = disease_path_edges_filtered.rename(columns={
    "DiseaseID": ":START_ID(Disease)",
    "PathwayID": ":END_ID(Pathway)"
})
disease_path_edges_neo[":TYPE"] = "INVOLVES_PATHWAY"
disease_path_edges_neo = disease_path_edges_neo[[":START_ID(Disease)", ":END_ID(Pathway)", ":TYPE"]]

# Gene-Disease
gene_disease_edges_neo = gene_disease_edges_filtered.rename(columns={
    "GeneID": ":START_ID(Gene)",
    "DiseaseID": ":END_ID(Disease)"
})
gene_disease_edges_neo[":TYPE"] = "IMPLICATED_IN"
gene_disease_edges_neo = gene_disease_edges_neo[[":START_ID(Gene)", ":END_ID(Disease)", ":TYPE"]]

# =============================================================================
# CELL 15: Save All Edge Files for Neo4j
# =============================================================================
chem_gene_edges_neo.to_csv(f"{base_proc}/edges_chemical_gene.csv", index=False)
chem_pathway_edges_neo.to_csv(f"{base_proc}/edges_chemical_pathway.csv", index=False)
chem_disease_edges_neo.to_csv(f"{base_proc}/edges_chemical_disease.csv", index=False)
gene_path_edges_neo.to_csv(f"{base_proc}/edges_gene_pathway.csv", index=False)
disease_path_edges_neo.to_csv(f"{base_proc}/edges_disease_pathway.csv", index=False)
gene_disease_edges_neo.to_csv(f"{base_proc}/edges_gene_disease.csv", index=False)

print("\n=== FINAL EDGE COUNTS (Saved to CSV) ===")
print(f"Chemical-Gene edges: {len(chem_gene_edges_neo)}")
print(f"Chemical-Pathway edges: {len(chem_pathway_edges_neo)}")
print(f"Chemical-Disease edges: {len(chem_disease_edges_neo)}")
print(f"Gene-Pathway edges: {len(gene_path_edges_neo)}")
print(f"Disease-Pathway edges: {len(disease_path_edges_neo)}")
print(f"Gene-Disease edges: {len(gene_disease_edges_neo)}")

print("\nAll files saved successfully!")