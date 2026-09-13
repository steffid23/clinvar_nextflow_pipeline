#!/usr/bin/env bash
# ==============================================================================
# pure_shell_pipeline.sh - 100% Pure POSIX Bash & AWK ClinVar Analysis Engine
# ==============================================================================
# Performs data streaming download, decompression, GRCh38 filtering, star-rating
# confidence parsing, gene categorization, and summary table exports 100% natively
# using pure Bash, AWK, SED, GREP, CUT, and SORT (Zero Python dependency).
# ==============================================================================

set -euo pipefail

DATA_DIR="data"
RESULTS_DIR="results"
CLINVAR_URL="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
RAW_GZ="${DATA_DIR}/variant_summary.txt.gz"
RAW_TXT="${DATA_DIR}/variant_summary.txt"

echo "================================================================================"
echo "          100% PURE POSIX BASH & AWK CLINVAR BIOINFORMATICS PIPELINE"
echo "================================================================================"

mkdir -p "${DATA_DIR}" "${RESULTS_DIR}"

# 1. Shell Download
if [ ! -f "${RAW_GZ}" ]; then
    echo "[SHELL] Downloading dataset via curl..."
    curl -s -L -o "${RAW_GZ}" "${CLINVAR_URL}"
fi

# 2. Shell Decompression
if [ ! -f "${RAW_TXT}" ]; then
    echo "[SHELL] Extracting via gzip..."
    gzip -d -c "${RAW_GZ}" > "${RAW_TXT}"
fi

# 3. Pure AWK Filtering & Statistical ETL (GRCh38, Star Rating >= 1, Cohort Summary)
echo "[SHELL & AWK] Processing 9M+ records natively in AWK..."

awk -F'\t' '
BEGIN {
    total_eval = 0;
    grc38_cnt = 0;
    star_cnt = 0;
    patho_cnt = 0;
    benign_cnt = 0;
    vus_cnt = 0;
}
NR > 1 {
    total_eval++;
    assembly = $13;
    review = $20;
    sig = $7;
    gene = $5;
    
    if (toupper(assembly) == "GRCH38") {
        grc38_cnt++;
        
        # Star rating check (exclude unasserted)
        rev_lower = tolower(review);
        if (index(rev_lower, "no assertion") == 0 && index(rev_lower, "no interpretation") == 0) {
            star_cnt++;
            
            sig_lower = tolower(sig);
            if (index(sig_lower, "pathogenic") > 0 && index(sig_lower, "benign") == 0) {
                patho_cnt++;
                if (gene != "" && gene != "-") {
                    patho_genes[gene]++;
                }
            } else if (index(sig_lower, "benign") > 0 && index(sig_lower, "pathogenic") == 0) {
                benign_cnt++;
                if (gene != "" && gene != "-") {
                    benign_genes[gene]++;
                }
            } else if (index(sig_lower, "uncertain significance") > 0) {
                vus_cnt++;
            }
        }
    }
}
END {
    print "Metric,Value" > "'"${RESULTS_DIR}"'/shell_pathogenic_cohort_summary.csv";
    print "Total ClinVar Records Evaluated," total_eval > "'"${RESULTS_DIR}"'/shell_pathogenic_cohort_summary.csv";
    print "GRCh38 Assembly Retained," grc38_cnt > "'"${RESULTS_DIR}"'/shell_pathogenic_cohort_summary.csv";
    print "High-Confidence (>=1-Star) Variants," star_cnt > "'"${RESULTS_DIR}"'/shell_pathogenic_cohort_summary.csv";
    print "Pathogenic / Likely Pathogenic Variants," patho_cnt > "'"${RESULTS_DIR}"'/shell_pathogenic_cohort_summary.csv";
    print "Benign / Likely Benign Variants," benign_cnt > "'"${RESULTS_DIR}"'/shell_pathogenic_cohort_summary.csv";
    print "Uncertain Significance (VUS) Variants," vus_cnt > "'"${RESULTS_DIR}"'/shell_pathogenic_cohort_summary.csv";
    
    # Export Gene Pathogenic Counts for Shell sorting
    print "GeneSymbol,Pathogenic_Count" > "'"${RESULTS_DIR}"'/shell_gene_patho_counts.tmp";
    for (g in patho_genes) {
        print g "," patho_genes[g] >> "'"${RESULTS_DIR}"'/shell_gene_patho_counts.tmp";
    }
}
' "${RAW_TXT}"

# 4. Pure Shell Sort & Top Gene Ranking
echo "[SHELL SORT] Ranking top pathogenic genes via Unix sort & head..."
(head -n 1 "${RESULTS_DIR}/shell_gene_patho_counts.tmp" && tail -n +2 "${RESULTS_DIR}/shell_gene_patho_counts.tmp" | sort -t',' -k2 -nr) | head -n 21 > "${RESULTS_DIR}/shell_top_pathogenic_genes.csv"
rm -f "${RESULTS_DIR}/shell_gene_patho_counts.tmp"

echo "================================================================================"
echo "[SUCCESS] Pure Shell & AWK pipeline execution completed successfully!"
echo "[SUMMARY] Output tables generated purely in Shell:"
ls -lh "${RESULTS_DIR}"/shell_*.csv
echo "================================================================================"
