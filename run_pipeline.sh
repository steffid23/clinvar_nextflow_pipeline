#!/usr/bin/env bash
# ==============================================================================
# run_pipeline.sh - POSIX Shell Script Master Bioinformatics Pipeline Runner
# ==============================================================================
# Executable POSIX Bash Master Runner:
# Performs streaming HTTP download via curl/wget, gunzip extraction, header validation,
# AWK/SED data filtering, Shell pathogenic cohort extraction, Python ETL, and figure auditing.
# ==============================================================================

set -euo pipefail

# Directory paths
DATA_DIR="data"
RESULTS_DIR="results"
FIGURES_DIR="figures"
BIN_DIR="bin"

# Input dataset parameters
CLINVAR_URL="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
RAW_GZ_FILE="${DATA_DIR}/variant_summary.txt.gz"
RAW_TXT_FILE="${DATA_DIR}/variant_summary.txt"

# Select Python executable (prefer python3 or py -3)
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    if command -v py &> /dev/null; then
        PYTHON_CMD="py -3.13"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "[ERROR] Python 3 executable not found!"
        exit 1
    fi
fi

echo "================================================================================"
echo "          CLINVAR BIOINFORMATICS ANALYSIS PIPELINE (SHELL & NEXTFLOW)"
echo "================================================================================"
echo "[INFO] Shell Environment: POSIX Bash / Zsh"
echo "[INFO] Python Helper Environment: ${PYTHON_CMD}"
echo "[INFO] Execution Start Time: $(date)"
echo "--------------------------------------------------------------------------------"

# Step 1: Ensure project directories exist via Shell
echo "[STEP 1/6] [SHELL] Setting up project directories..."
mkdir -p "${DATA_DIR}" "${RESULTS_DIR}" "${FIGURES_DIR}" "${BIN_DIR}"
echo "[OK] Project directories verified."

# Step 2: Download & Cache Data using Shell Tools (curl / wget)
echo "--------------------------------------------------------------------------------"
echo "[STEP 2/6] [SHELL] Downloading & Caching ClinVar dataset using curl/wget..."
if [ -f "${RAW_GZ_FILE}" ]; then
    echo "[CACHE HIT] Raw gzip archive already exists: ${RAW_GZ_FILE}"
else
    echo "[SHELL DOWNLOAD] Fetching dataset via curl..."
    if command -v curl &> /dev/null; then
        curl -s -L -o "${RAW_GZ_FILE}" "${CLINVAR_URL}"
    elif command -v wget &> /dev/null; then
        wget -q -O "${RAW_GZ_FILE}" "${CLINVAR_URL}"
    else
        echo "[FALLBACK] Using Python downloader..."
        ${PYTHON_CMD} "${BIN_DIR}/download_data.py" --url "${CLINVAR_URL}" --output-dir "${DATA_DIR}"
    fi
fi

# Step 3: Decompress Gzip via Shell (gunzip / gzip)
echo "--------------------------------------------------------------------------------"
echo "[STEP 3/6] [SHELL] Extracting compressed archive via gunzip..."
if [ -f "${RAW_TXT_FILE}" ]; then
    echo "[CACHE HIT] Decompressed file already exists: ${RAW_TXT_FILE}"
else
    echo "[SHELL DECOMPRESS] Running gzip -d -c..."
    gzip -d -c "${RAW_GZ_FILE}" > "${RAW_TXT_FILE}"
    echo "[SHELL DECOMPRESS COMPLETE] Extracted text size: $(du -sh ${RAW_TXT_FILE} | cut -f1)"
fi

# Step 4: Shell Inspection & AWK/SED Processing
echo "--------------------------------------------------------------------------------"
echo "[STEP 4/6] [SHELL] Executing Shell AWK / SED / GREP Schema Inspection..."
echo "[SHELL INSPECTION] Inspecting header structure (first 2 lines):"
head -n 2 "${RAW_TXT_FILE}" | cut -f 1-8

echo ""
echo "[SHELL INSPECTION] Counting total raw records using wc -l:"
wc -l "${RAW_TXT_FILE}"

echo ""
echo "[SHELL INSPECTION] Filtering GRCh38 Variants using AWK:"
awk -F'\t' 'BEGIN {count=0} $13 == "GRCh38" {count++} END {print "[AWK FILTER] Total GRCh38 Assembly Records: " count}' "${RAW_TXT_FILE}"

echo ""
echo "[SHELL INSPECTION] Extracting Pathogenic Cohort Sample via GREP & SED..."
grep -i "Pathogenic" "${RAW_TXT_FILE}" | grep "GRCh38" | head -n 5 | awk -F'\t' '{print "  Variant ID: " $1 " | Gene: " $5 " | Type: " $2 " | Sig: " $7}'

# Step 5: Execute Main Statistical Filtering Engine & Summary Export
echo "--------------------------------------------------------------------------------"
echo "[STEP 5/6] Executing Low-RAM Chunked Statistical Pipeline Engine..."
${PYTHON_CMD} "${BIN_DIR}/clinvar_pipeline.py" \
    --input-file "${RAW_TXT_FILE}" \
    --output-dir "${RESULTS_DIR}" \
    --assembly "GRCh38" \
    --min-stars 1 \
    --chunk-size 250000

# Step 6: Generate Publication Visualizations & Presentation
echo "--------------------------------------------------------------------------------"
echo "[STEP 6/6] Generating 300 DPI Publication Figures & Presentation Deck..."
${PYTHON_CMD} "${BIN_DIR}/plot_generator.py" \
    --results-dir "${RESULTS_DIR}" \
    --output-dir "${FIGURES_DIR}" \
    --dpi 300

${PYTHON_CMD} "${BIN_DIR}/generate_ppt.py"

echo "--------------------------------------------------------------------------------"
echo "================================================================================"
echo "          CLINVAR PIPELINE EXECUTION COMPLETED SUCCESSFULLY!"
echo "================================================================================"
echo "[SUMMARY] Generated Result Tables:"
ls -lh "${RESULTS_DIR}"/*.csv
echo ""
echo "[SUMMARY] Generated Publication Figures:"
ls -lh "${FIGURES_DIR}"/*.png
echo "================================================================================"
