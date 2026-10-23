#!/usr/bin/env bash
# QARTOD QC step for the local CODAR site tree: flags every raw .ruv under
# LOCAL_BASE (qc_config.py) that has no qartod/ twin yet.
#
# This script does NOT harvest or prune. The radial files arrive from the
# hfradmin repo's pull (scripts/pull_radials.py, run by its
# daily_radials.sh), which also deletes raw/ and qartod/ files older than
# the retention window. hfradmin calls this script between its pull and
# its loader when its .env has
#
#   RADIAL_QC_COMMAND=$HOME/HFRadarPy/qartod/run_qc.sh
#
# Run by hand from anywhere:
#   ~/HFRadarPy/qartod/run_qc.sh              # QC everything new
#   ~/HFRadarPy/qartod/run_qc.sh --dry-run    # plan only (any qc_walk.py flag passes through)
#
# Exits non-zero if QC failed or a site has no thresholds (see README.md,
# "Adding a new site"), so the caller can notice a partial run.

CONDA_SH="$HOME/miniconda3/etc/profile.d/conda.sh"   # conda info --base + /etc/profile.d/conda.sh
CONDA_ENV="hfradarpy"
LOG_DIR="$HOME/codar/logs"

cd "$(dirname "$0")" || exit 1                       # scripts import siblings by name
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/run_qc_$(date +%Y%m%d_%H%M%S).log"
if [ -t 1 ]; then exec > >(tee -a "$LOG") 2>&1; else exec >>"$LOG" 2>&1; fi   # show output when run by hand

echo "=== run_qc start $(date '+%F %T') ==="
source "$CONDA_SH" && conda activate "$CONDA_ENV" || { echo "conda activate $CONDA_ENV failed"; exit 1; }

python qc_walk.py "$@"
status=$?

echo "=== run_qc end $(date '+%F %T') status=$status ==="
exit $status
