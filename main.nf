nextflow.enable.dsl=2

/*
================================================================================
                         ClinVar Nextflow DSL2 Pipeline
================================================================================
  Modular bioinformatics analysis pipeline for NCBI ClinVar variant analysis.
================================================================================
*/

// Parameter Defaults
params.url         = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
params.data_dir    = "${projectDir}/data"
params.results_dir = "${projectDir}/results"
params.figures_dir = "${projectDir}/figures"
params.assembly    = "GRCh38"
params.min_stars   = 1
params.sample_rows = 0


process DOWNLOAD_DATA {
    tag "NCBI ClinVar Fetch"
    publishDir "${params.data_dir}", mode: 'copy'

    output:
    path "variant_summary.txt", emit: clinvar_txt

    script:
    """
    python3 "${projectDir}/bin/download_data.py" \
        --url "${params.url}" \
        --output-dir . \
        --filename "variant_summary.txt.gz" \
        --sample-rows ${params.sample_rows}
    """
}

process ANALYZE_CLINVAR {
    tag "Filtering & ETL Engine"
    publishDir "${params.results_dir}", mode: 'copy'

    input:
    path clinvar_file

    output:
    path "*.csv", emit: csv_tables

    script:
    """
    python3 "${projectDir}/bin/clinvar_pipeline.py" \
        --input-file ${clinvar_file} \
        --output-dir . \
        --assembly "${params.assembly}" \
        --min-stars ${params.min_stars}
    """
}

process GENERATE_PLOTS {
    tag "300 DPI Plotting Engine"
    publishDir "${params.figures_dir}", mode: 'copy'

    input:
    path results_tables

    output:
    path "*.png", emit: figures

    script:
    """
    python3 "${projectDir}/bin/plot_generator.py" \
        --results-dir . \
        --output-dir . \
        --dpi 300
    """
}

workflow {
    log.info """
================================================================================
                    CLINVAR NEXTFLOW DSL2 PIPELINE
================================================================================
ClinVar URL      : ${params.url}
Genomic Assembly : ${params.assembly}
Min Star Rating  : ${params.min_stars}
Data Directory   : ${params.data_dir}
Results Directory: ${params.results_dir}
Figures Directory: ${params.figures_dir}
================================================================================
"""

    DOWNLOAD_DATA()
    ANALYZE_CLINVAR(DOWNLOAD_DATA.out.clinvar_txt)
    GENERATE_PLOTS(ANALYZE_CLINVAR.out.csv_tables)
}
