#!/usr/bin/env bash
# Daily CODAR radial pipeline: harvest .ruv files, QC them, prune old output.
# Run from cron, e.g.:
#   MAILTO=you@tamu.edu
#   30 6 * * *  $HOME/HFRadarPy/qartod/daily_ruv.sh
#
# Exits non-zero if the pull or the QC failed, so cron mails you.
# A failed pull does not stop QC of the files already on disk.

CONDA_SH="$HOME/miniconda3/etc/profile.d/conda.sh"   # conda info --base + /etc/profile.d/conda.sh
CONDA_ENV="hfradarpy"
LOG_DIR="$HOME/codar/logs"

cd "$(dirname "$0")" || exit 1                       # scripts import siblings by name
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/daily_ruv_$(date +%Y%m%d_%H%M%S).log" 2>&1

echo "=== start $(date '+%F %T') ==="
source "$CONDA_SH" && conda activate "$CONDA_ENV" || { echo "conda activate $CONDA_ENV failed"; exit 1; }

status=0
echo; echo "--- pull_ruv.py ---";  python pull_ruv.py  || status=1
echo; echo "--- qc_walk.py ---";   python qc_walk.py   || status=1
echo; echo "--- prune_qc.py ---";  python prune_qc.py

echo; echo "=== end $(date '+%F %T') status=$status ==="
exit $status
