#!/usr/bin/env bash
# ==============================================================================
# Script: sync_wiedzy.sh
# Description: Safely synchronizes the kitchen knowledge base with Synthadoc.
#              Automatically discovers numbered folders, ignores private data,
#              and filters out PDFs larger than 100KB.
# ==============================================================================

# --- Strict Mode ---
set -euo pipefail

# --- Configuration ---
readonly BIG_PDF_FILE="to_ingest_big.txt"
readonly MANIFEST_FILE=".to_ingest_auto.txt"
readonly DRY_RUN_OUTPUT="dry_run_manifest.txt"
readonly MAX_PDF_SIZE="100k"

# Folders to explicitly ignore (exact names)
readonly IGNORE_DIRS=("04_Podwykonawcy_CRM" "06_Realizacje")

# Supported Synthadoc extensions
readonly SUPPORTED_EXTS=("md" "txt" "pdf" "docx" "pptx" "xlsx" "csv" "png" "jpg" "jpeg" "webp" "gif" "tiff")

# --- Logging Setup ---
readonly COLOR_RESET='\033[0m'
readonly COLOR_INFO='\033[0;34m'   # Blue
readonly COLOR_SUCCESS='\033[0;32m' # Green
readonly COLOR_WARN='\033[0;33m'   # Yellow
readonly COLOR_ERROR='\033[0;31m'  # Red

log_info()    { echo -e "${COLOR_INFO}[INFO]${COLOR_RESET} $1"; }
log_success() { echo -e "${COLOR_SUCCESS}[SUCCESS]${COLOR_RESET} $1"; }
log_warn()    { echo -e "${COLOR_WARN}[WARN]${COLOR_RESET} $1"; }
log_error()   { echo -e "${COLOR_ERROR}[ERROR]${COLOR_RESET} $1" >&2; }

# --- Usage / Help ---
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --dry-run    Simulate the process. Finds files and generates lists,"
    echo "                   but does NOT send anything to Synthadoc."
    echo "  -h, --help       Show this help message and exit."
    echo ""
}

# --- Argument Parsing ---
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# --- Dependency Check ---
if [[ "$DRY_RUN" == false ]] && ! command -v synthadoc &> /dev/null; then
    log_error "Synthadoc is not installed or not in PATH. Did you activate your uv environment?"
    exit 1
fi

# --- Main Logic ---
main() {
    if [[ "$DRY_RUN" == true ]]; then
        log_warn "DRY RUN MODE ENABLED. No data will be sent to Synthadoc."
    else
        log_info "Starting Knowledge Base Synchronization..."
    fi

    # 1. Discover valid directories (starts with two digits and underscore)
    local valid_dirs=()
    for dir in [0-9][0-9]_*/; do
        [[ -d "$dir" ]] || continue

        local dir_name
        dir_name=$(basename "$dir")

        local is_ignored=false
        for ignore in "${IGNORE_DIRS[@]}"; do
            if [[ "$dir_name" == "$ignore" ]]; then
                is_ignored=true
                break
            fi
        done

        if [[ "$is_ignored" == true ]]; then
            log_warn "Skipping ignored directory: $dir_name"
        else
            valid_dirs+=("$dir_name")
        fi
    done

    if [[ ${#valid_dirs[@]} -eq 0 ]]; then
        log_warn "No valid knowledge directories found. Exiting."
        exit 0
    fi

    log_info "Scanning directories: ${valid_dirs[*]}"

    # 2. Build the extension filter for the 'find' command
    local ext_args=()
    for ext in "${SUPPORTED_EXTS[@]}"; do
        ext_args+=("-iname" "*.$ext" "-o")
    done
    unset 'ext_args[${#ext_args[@]}-1]' # Remove the trailing "-o"

    # 3. Clear previous output files
    > "$BIG_PDF_FILE"
    > "$MANIFEST_FILE"

    # 4. Find large PDFs and log them
    log_info "Filtering out PDFs larger than ${MAX_PDF_SIZE}..."
    find "${valid_dirs[@]}" -type f -iname "*.pdf" -size "+${MAX_PDF_SIZE}" > "$BIG_PDF_FILE"

    local big_pdf_count
    big_pdf_count=$(wc -l < "$BIG_PDF_FILE" | tr -d ' ')
    if [[ "$big_pdf_count" -gt 0 ]]; then
        log_warn "Found $big_pdf_count large PDF(s). Saved to $BIG_PDF_FILE (These will NOT be ingested)."
    fi

    # 5. Find all valid files, EXCLUDING the large PDFs, and write to manifest
    log_info "Generating ingestion manifest..."
    find "${valid_dirs[@]}" -type f \( "${ext_args[@]}" \) ! \( -iname "*.pdf" -size "+${MAX_PDF_SIZE}" \) > "$MANIFEST_FILE"

    local manifest_count
    manifest_count=$(wc -l < "$MANIFEST_FILE" | tr -d ' ')

    if [[ "$manifest_count" -eq 0 ]]; then
        log_warn "No valid files found to ingest. Exiting."
        rm -f "$MANIFEST_FILE"
        exit 0
    fi

    # 6. Execution Branch (Dry Run vs Real Run)
    if [[ "$DRY_RUN" == true ]]; then
        mv "$MANIFEST_FILE" "$DRY_RUN_OUTPUT"
        log_success "Dry run complete! Found $manifest_count files."
        log_info "Please review the file '$DRY_RUN_OUTPUT' to see exactly what would be ingested."
        exit 0
    fi

    # 7. Execute Synthadoc using the generated manifest
    log_success "Found $manifest_count files ready for ingestion."
    log_info "Sending manifest to Synthadoc queue..."
    synthadoc ingest --file "$MANIFEST_FILE"

    # 8. Cleanup
    rm -f "$MANIFEST_FILE"
    rm -f "$DRY_RUN_OUTPUT" # Clean up old dry run files if they exist
    log_success "Synchronization queued successfully! Run 'synthadoc jobs list' to view progress."
}

# Execute main function
main