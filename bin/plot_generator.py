#!/usr/bin/env python3
"""
plot_generator.py - Publication-Quality 300 DPI Figure Generator
Generates publication-ready figures for ClinVar pathogenicity distributions and
gene-phenotype landscape visualizations.
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set global matplotlib publication publication parameters
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 1.0

def parse_args():
    parser = argparse.ArgumentParser(description="Publication 300 DPI Plot Generator for ClinVar Analysis")
    parser.add_argument("--results-dir", type=str, default="results", help="Input results directory containing CSVs")
    parser.add_argument("--output-dir", type=str, default="figures", help="Output directory for generated PNG figures")
    parser.add_argument("--dpi", type=int, default=300, help="Image resolution DPI (default: 300)")
    return parser.parse_args()

def generate_figure1(results_dir, output_dir, dpi):
    print(f"[FIGURE 1] Generating Clinical Significance & Variant Type Distribution plot...")
    sig_path = os.path.join(results_dir, 'clinical_significance_distribution.csv')
    type_path = os.path.join(results_dir, 'variant_type_distribution.csv')
    
    if not os.path.exists(sig_path) or not os.path.exists(type_path):
        print(f"[WARNING] Figure 1 input files missing in {results_dir}. Skipping Figure 1.")
        return
        
    sig_df = pd.read_csv(sig_path)
    type_df = pd.read_csv(type_path)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=dpi)
    
    # Panel A: Clinical Significance Bar Chart (Top 8 categories)
    top_sig = sig_df.head(8).copy()
    palette_a = sns.color_palette("muted", len(top_sig))
    bars_a = axes[0].barh(top_sig['ClinicalSignificance'], top_sig['VariantCount'], color=palette_a, edgecolor='black', linewidth=0.6)
    axes[0].set_title("A. Distribution of Clinical Significance Classifications", fontsize=12, fontweight='bold', pad=12)
    axes[0].set_xlabel("Variant Count", fontsize=10, fontweight='bold')
    axes[0].invert_yaxis()  # Top category on top
    axes[0].grid(axis='x', linestyle='--', alpha=0.5)
    
    # Annotate counts
    for bar in bars_a:
        width = bar.get_width()
        axes[0].text(width + (width * 0.01), bar.get_y() + bar.get_height()/2, f"{width:,.0f}",
                     va='center', ha='left', fontsize=8.5)
                     
    # Panel B: Variant Type Distribution (Pathogenic Variants)
    top_types = type_df.head(8).copy()
    if 'Pathogenic' in top_types.columns:
        y_val = 'Pathogenic'
        panel_title = "B. Variant Types in Pathogenic Cohort"
    else:
        y_val = 'Total'
        panel_title = "B. Variant Type Distribution"
        
    palette_b = sns.color_palette("Blues_r", len(top_types))
    bars_b = axes[1].barh(top_types['Type'], top_types[y_val], color=palette_b, edgecolor='black', linewidth=0.6)
    axes[1].set_title(panel_title, fontsize=12, fontweight='bold', pad=12)
    axes[1].set_xlabel("Pathogenic Variant Count", fontsize=10, fontweight='bold')
    axes[1].invert_yaxis()
    axes[1].grid(axis='x', linestyle='--', alpha=0.5)
    
    for bar in bars_b:
        width = bar.get_width()
        axes[1].text(width + (width * 0.01), bar.get_y() + bar.get_height()/2, f"{width:,.0f}",
                     va='center', ha='left', fontsize=8.5)
                     
    plt.tight_layout()
    out_path = os.path.join(output_dir, 'clinvar_figure1_distributions.png')
    plt.savefig(out_path, dpi=dpi, bbox_inches='tight')
    plt.close()
    print(f"[FIGURE 1 SAVED] {out_path} ({dpi} DPI)")

def generate_figure2(results_dir, output_dir, dpi):
    print(f"[FIGURE 2] Generating Gene-Phenotype Pathogenicity Landscape plot...")
    genes_path = os.path.join(results_dir, 'top_pathogenic_genes.csv')
    gene_class_path = os.path.join(results_dir, 'gene_pathogenicity_classification.csv')
    
    if not os.path.exists(genes_path):
        print(f"[WARNING] Figure 2 input file missing ({genes_path}). Skipping Figure 2.")
        return
        
    genes_df = pd.read_csv(genes_path)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), dpi=dpi)
    
    # Panel A: Top 15 Pathogenic Burden Genes
    top15_genes = genes_df.head(15).copy()
    palette = sns.color_palette("Reds_r", len(top15_genes))
    bars = axes[0].bar(top15_genes['GeneSymbol'], top15_genes['Pathogenic_Count'], color=palette, edgecolor='black', linewidth=0.6)
    axes[0].set_title("A. Top 15 Genes Ranked by Pathogenic Variant Burden", fontsize=12, fontweight='bold', pad=12)
    axes[0].set_ylabel("Pathogenic Variant Count", fontsize=10, fontweight='bold')
    axes[0].set_xlabel("Gene Symbol", fontsize=10, fontweight='bold')
    axes[0].tick_params(axis='x', rotation=45)
    axes[0].grid(axis='y', linestyle='--', alpha=0.5)
    
    for bar in bars:
        height = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width()/2, height + (height * 0.01), f"{height:,.0f}",
                     ha='center', va='bottom', fontsize=8, rotation=0)
                     
    # Panel B: Gene Pathogenicity Profile Categorization (Pathogenic-only vs Benign-only vs Multiclass)
    if os.path.exists(gene_class_path):
        class_df = pd.read_csv(gene_class_path)
        class_counts = class_df['Gene_Class'].value_counts()
        colors = ['#d9534f', '#5cb85c', '#f0ad4e', '#0275d8']
        
        wedges, texts, autotexts = axes[1].pie(
            class_counts.values,
            labels=class_counts.index,
            autopct='%1.1f%%',
            startangle=140,
            colors=colors[:len(class_counts)],
            wedgeprops=dict(edgecolor='black', linewidth=1)
        )
        for t in autotexts:
            t.set_fontsize(9)
            t.set_fontweight('bold')
        axes[1].set_title("B. Gene Categorization Landscape\n(Pathogenic-only, Benign-only, Multiclass)", fontsize=12, fontweight='bold', pad=12)
    else:
        axes[1].axis('off')
        
    plt.tight_layout()
    out_path = os.path.join(output_dir, 'clinvar_figure2_landscape.png')
    plt.savefig(out_path, dpi=dpi, bbox_inches='tight')
    plt.close()
    print(f"[FIGURE 2 SAVED] {out_path} ({dpi} DPI)")

def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    generate_figure1(args.results_dir, args.output_dir, args.dpi)
    generate_figure2(args.results_dir, args.output_dir, args.dpi)
    print(f"[SUCCESS] All publication figures generated successfully in '{args.output_dir}'.")

if __name__ == "__main__":
    main()
