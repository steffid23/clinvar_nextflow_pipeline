#!/usr/bin/env bash
# ==============================================================================
# run_pipeline.sh - ClinVar Bioinformatics Analysis Pipeline Runner
# ==============================================================================
# Executable POSIX Bash Master Runner:
# Performs streaming download, awk/sed column validation, Python ETL execution,
# statistical summaries, publication figure creation, and output auditing.
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
        PYTHON_CMD="py -3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "[ERROR] Python 3 executable not found!"
        exit 1
    fi
fi

echo "================================================================================"
echo "          CLINVAR BIOINFORMATICS ANALYSIS PIPELINE RUNNER"
echo "================================================================================"
echo "[INFO] Using Python environment: ${PYTHON_CMD}"
echo "[INFO] Start time: $(date)"
echo "--------------------------------------------------------------------------------"

# Step 1: Ensure project directories exist
echo "[STEP 1/5] Setting up project directories..."
mkdir -p "${DATA_DIR}" "${RESULTS_DIR}" "${FIGURES_DIR}" "${BIN_DIR}"
echo "[OK] Project directories verified."

# Step 2: Download & Cache Data
echo "[STEP 2/5] Downloading & Caching ClinVar dataset..."
${PYTHON_CMD} "${BIN_DIR}/download_data.py" \
    --url "${CLINVAR_URL}" \
    --output-dir "${DATA_DIR}" \
    --filename "variant_summary.txt.gz"

# Step 3: Shell Inspection with AWK / SED / HEAD
echo "--------------------------------------------------------------------------------"
echo "[STEP 3/5] Executing Shell AWK/SED Schema Inspection..."
if [ -f "${RAW_TXT_FILE}" ]; then
    echo "[SHELL INSPECTION] Inspecting first 2 header lines using head:"
    head -n 2 "${RAW_TXT_FILE}" | cut -f 1-10
    echo ""
    echo "[SHELL INSPECTION] Quantifying total rows using wc -l:"
    wc -l "${RAW_TXT_FILE}"
    echo ""
    echo "[SHELL INSPECTION] Counting GRCh38 variants using AWK:"
    awk -F'\t' '$13 == "GRCh38" {count++} END {print "GRCh38 Variant Count: " count}' "${RAW_TXT_FILE}" || true
else
    echo "[WARNING] ${RAW_TXT_FILE} not found. Skipping AWK column inspection."
fi
echo "--------------------------------------------------------------------------------"

# Step 4: Run Python ETL & Statistical Analysis (Optimized Low-RAM Chunking)
echo "[STEP 4/5] Executing Python ETL & Statistical Filtering Engine..."
TARGET_INPUT="${RAW_TXT_FILE}"
if [ ! -f "${TARGET_INPUT}" ]; then
    TARGET_INPUT=$(ls ${DATA_DIR}/variant_summary*.txt | head -n 1)
fi

${PYTHON_CMD} "${BIN_DIR}/clinvar_pipeline.py" \
    --input-file "${TARGET_INPUT}" \
    --output-dir "${RESULTS_DIR}" \
    --assembly "GRCh38" \
    --min-stars 1 \
    --chunk-size 250000

# Step 5: Generate Publication Visualizations (300 DPI)
echo "--------------------------------------------------------------------------------"
echo "[STEP 5/5] Generating 300 DPI Publication Figures..."
${PYTHON_CMD} "${BIN_DIR}/plot_generator.py" \
    --results-dir "${RESULTS_DIR}" \
    --output-dir "${FIGURES_DIR}" \
    --dpi 300

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
