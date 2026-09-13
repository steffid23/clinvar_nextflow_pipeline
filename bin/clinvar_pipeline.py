#!/usr/bin/env python3
"""
clinvar_pipeline.py - NCBI ClinVar Filtering & Statistical Analysis Pipeline Engine
Optimized for low-RAM / WSL environments using chunked stream processing.
Extracts GRCh38 assembly variants, applies ReviewStatus star-rating confidence filtering,
analyzes Pathogenic/Likely Pathogenic cohorts, categorizes Gene-Disease landscapes,
and exports publication summary tables (CSV/TSV).
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np

REVIEW_STATUS_STARS = {
    'practice guideline': 4,
    'reviewed by expert panel': 3,
    'criteria provided, multiple submitters, no conflicts': 2,
    'criteria provided, single submitter': 1,
    'criteria provided, conflicting interpretations': 1,
    'no assertion criteria provided': 0,
    'no assertion provided': 0,
    'no interpretations': 0,
    'no interpretation for the single variant': 0
}

def parse_args():
    parser = argparse.ArgumentParser(description="ClinVar Bioinformatics ETL & Statistical Analysis Engine")
    parser.add_argument("--input-file", type=str, required=True, help="Path to ClinVar variant_summary.txt")
    parser.add_argument("--output-dir", type=str, default="results", help="Output directory for CSV/TSV tables")
    parser.add_argument("--assembly", type=str, default="GRCh38", help="Genomic assembly filter (default: GRCh38)")
    parser.add_argument("--min-stars", type=int, default=1, help="Minimum ClinVar ReviewStatus star rating (0-4)")
    parser.add_argument("--chunk-size", type=int, default=250000, help="Chunk size for stream processing (RAM optimization)")
    parser.add_argument("--sample-rows", type=int, default=None, help="Optionally limit read rows for fast testing")
    return parser.parse_args()

def assign_star_rating(status):
    if not isinstance(status, str):
        return 0
    status_clean = status.strip().lower()
    return REVIEW_STATUS_STARS.get(status_clean, 0)

def categorize_clinical_sig(sig):
    if not isinstance(sig, str):
        return 'Other'
    sig_lower = sig.lower()
    if 'pathogenic' in sig_lower and 'benign' not in sig_lower:
        return 'Pathogenic'
    elif 'benign' in sig_lower and 'pathogenic' not in sig_lower:
        return 'Benign'
    elif 'uncertain significance' in sig_lower or 'vus' in sig_lower:
        return 'Uncertain Significance'
    elif 'conflicting' in sig_lower:
        return 'Conflicting Interpretations'
    else:
        return 'Other'

def process_clinvar_chunked(file_path, target_assembly, min_stars, chunk_size=250000, nrows=None):
    print(f"[LOAD & STREAM] Processing ClinVar dataset with low-RAM chunk size = {chunk_size:,}...")
    
    usecols = [
        '#AlleleID', 'Type', 'Name', 'GeneID', 'GeneSymbol', 'HGNC_ID',
        'ClinicalSignificance', 'ClinSigSimple', 'LastEvaluated', 'RS# (rsID)',
        'PhenotypeIDS', 'PhenotypeList', 'Origin', 'Assembly', 'Chromosome',
        'Start', 'Stop', 'ReferenceAllele', 'AlternateAllele', 'ReviewStatus',
        'NumberSubmitters', 'VariationID'
    ]
    
    header_df = pd.read_csv(file_path, sep='\t', nrows=2)
    available_cols = header_df.columns.tolist()
    read_cols = [c for c in usecols if c in available_cols]
    if len(read_cols) < 5:
        read_cols = None
        
    filtered_chunks = []
    total_loaded = 0
    total_retained = 0
    
    # Read in stream chunks to keep memory usage under 200MB
    chunks = pd.read_csv(
        file_path,
        sep='\t',
        usecols=read_cols,
        nrows=nrows,
        chunksize=chunk_size,
        low_memory=False
    )
    
    for i, chunk in enumerate(chunks):
        chunk_len = len(chunk)
        total_loaded += chunk_len
        
        # Assembly filter
        if 'Assembly' in chunk.columns:
            chunk = chunk[chunk['Assembly'].astype(str).str.upper() == target_assembly.upper()]
            
        # Star rating filter
        if 'ReviewStatus' in chunk.columns:
            chunk['StarRating'] = chunk['ReviewStatus'].apply(assign_star_rating)
            if min_stars > 0:
                chunk = chunk[chunk['StarRating'] >= min_stars]
                
        if len(chunk) > 0:
            if 'ClinicalSignificance' in chunk.columns:
                chunk['SigCategory'] = chunk['ClinicalSignificance'].apply(categorize_clinical_sig)
            filtered_chunks.append(chunk)
            total_retained += len(chunk)
            
        sys.stdout.write(f"\r[STREAMING] Processed {total_loaded:,} records | Retained: {total_retained:,}")
        sys.stdout.flush()
        
    print("\n[STREAM COMPLETE] Aggregating filtered cohorts...")
    if len(filtered_chunks) > 0:
        df = pd.concat(filtered_chunks, ignore_index=True)
    else:
        df = pd.DataFrame()
        
    print(f"[SUMMARY] Total loaded: {total_loaded:,} | Retained GRCh38 (>={min_stars} star): {len(df):,}")
    return df

def run_analyses(df, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    print(f"[ANALYSIS] Executing cohort and gene-disease landscape analyses...")
    
    # 1. Pathogenic Cohort Analysis
    patho_df = df[df['SigCategory'] == 'Pathogenic'].copy()
    benign_df = df[df['SigCategory'] == 'Benign'].copy()
    vus_df = df[df['SigCategory'] == 'Uncertain Significance'].copy()
    
    unique_patho_genes = patho_df['GeneSymbol'].replace('-', np.nan).dropna().unique()
    
    all_phenotypes = []
    for pheno_str in patho_df['PhenotypeList'].dropna():
        if pheno_str != 'not provided' and pheno_str != 'not specified' and pheno_str != '-':
            terms = [p.strip() for p in pheno_str.split(';') if p.strip()]
            all_phenotypes.extend(terms)
            
    pheno_series = pd.Series(all_phenotypes)
    unique_phenotypes_count = pheno_series.nunique()
    
    summary_stats = {
        'Metric': [
            'Total Assembly Variants Evaluated',
            'High-Confidence (>=1 Star) Variants',
            'Pathogenic / Likely Pathogenic Variants',
            'Benign / Likely Benign Variants',
            'Uncertain Significance (VUS) Variants',
            'Unique Genes Harboring Pathogenic Variants',
            'Unique Phenotypes/Diseases Associated with Pathogenic Variants',
            'Pathogenic Variant Percentage (%)'
        ],
        'Value': [
            len(df),
            len(df),
            len(patho_df),
            len(benign_df),
            len(vus_df),
            len(unique_patho_genes),
            unique_phenotypes_count,
            round((len(patho_df) / len(df) * 100), 2) if len(df) > 0 else 0
        ]
    }
    summary_df = pd.DataFrame(summary_stats)
    summary_path = os.path.join(output_dir, 'pathogenic_cohort_summary.csv')
    summary_df.to_csv(summary_path, index=False)
    print(f"[EXPORTED] {summary_path}")
    
    # 2. Clinical Significance & Variant Type Distributions
    sig_dist = df['ClinicalSignificance'].value_counts().reset_index()
    sig_dist.columns = ['ClinicalSignificance', 'VariantCount']
    sig_dist['Percentage'] = (sig_dist['VariantCount'] / len(df) * 100).round(2)
    sig_dist_path = os.path.join(output_dir, 'clinical_significance_distribution.csv')
    sig_dist.to_csv(sig_dist_path, index=False)
    print(f"[EXPORTED] {sig_dist_path}")
    
    var_type_df = df.groupby(['Type', 'SigCategory']).size().unstack(fill_value=0).reset_index()
    var_type_df['Total'] = var_type_df.sum(axis=1, numeric_only=True)
    var_type_df = var_type_df.sort_values(by='Total', ascending=False)
    var_type_path = os.path.join(output_dir, 'variant_type_distribution.csv')
    var_type_df.to_csv(var_type_path, index=False)
    print(f"[EXPORTED] {var_type_path}")
    
    # 3. Gene-Disease-Pathogenicity Landscape Mapping & Categorization
    print("[ANALYSIS] Categorizing genes into Pathogenic-only, Benign-only, and Multiclass profiles...")
    gene_df = df[df['GeneSymbol'].notna() & (df['GeneSymbol'] != '-')].copy()
    
    gene_stats = gene_df.groupby('GeneSymbol').agg(
        GeneID=('GeneID', 'first'),
        Pathogenic_Count=('SigCategory', lambda x: (x == 'Pathogenic').sum()),
        Benign_Count=('SigCategory', lambda x: (x == 'Benign').sum()),
        VUS_Count=('SigCategory', lambda x: (x == 'Uncertain Significance').sum()),
        Total_Variants=('SigCategory', 'count')
    ).reset_index()
    
    def classify_gene(row):
        p = row['Pathogenic_Count']
        b = row['Benign_Count']
        if p > 0 and b > 0:
            return 'Multiclass'
        elif p > 0 and b == 0:
            return 'Pathogenic-only'
        elif p == 0 and b > 0:
            return 'Benign-only'
        else:
            return 'VUS/Other-only'
            
    gene_stats['Gene_Class'] = gene_stats.apply(classify_gene, axis=1)
    gene_class_path = os.path.join(output_dir, 'gene_pathogenicity_classification.csv')
    gene_stats.to_csv(gene_class_path, index=False)
    print(f"[EXPORTED] {gene_class_path}")
    
    # 4. Top Pathogenic Genes Ranking
    top_genes = gene_stats.sort_values(by='Pathogenic_Count', ascending=False).head(25).copy()
    top_genes_path = os.path.join(output_dir, 'top_pathogenic_genes.csv')
    top_genes.to_csv(top_genes_path, index=False)
    print(f"[EXPORTED] {top_genes_path}")
    
    # 5. Top Phenotypes Aggregation
    if len(pheno_series) > 0:
        top_pheno_df = pheno_series.value_counts().head(25).reset_index()
        top_pheno_df.columns = ['Phenotype_Name', 'Pathogenic_Variant_Count']
        top_pheno_path = os.path.join(output_dir, 'top_phenotypes.csv')
        top_pheno_df.to_csv(top_pheno_path, index=False)
        print(f"[EXPORTED] {top_pheno_path}")
        
    print("[SUCCESS] All pipeline statistical analyses completed successfully.")

def main():
    args = parse_args()
    df = process_clinvar_chunked(
        file_path=args.input_file,
        target_assembly=args.assembly,
        min_stars=args.min_stars,
        chunk_size=args.chunk_size,
        nrows=args.sample_rows
    )
    run_analyses(df, args.output_dir)

if __name__ == "__main__":
    main()
