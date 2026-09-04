#!/usr/bin/env bash
# Daily CODAR radial pipeline: harvest .ruv files from partner servers, then
# apply QARTOD QC to whatever is new.  Meant to be run from cron, e.g.
#
#   MAILTO=you@tamu.edu
#   30 6 * * *  /path/to/HFRadarPy/qartod/daily_ruv.sh
#
# Cron starts with an almost empty environment, so this script activates the
# conda env itself and never relies on ~/.bashrc or the login PATH.
#
# Exit status: 0 if both steps succeeded, 1 otherwise (so cron mails you).
# A failed pull does NOT stop QC -- files that did arrive are still processed.

# ---------------------------------------------------------------------------
# Settings -- the only lines you should need to edit
# ---------------------------------------------------------------------------
CONDA_ENV="hfradarpy"                      # conda env with hfradarpy + pandas<3
CONDA_SH=""                                # leave empty to auto-detect; else e.g. /opt/miniconda3/etc/profile.d/conda.sh
LOG_DIR="${HOME}/codar/logs"               # one log file per run
KEEP_LOGS=60                               # how many run logs to keep
KEEP_QC_DAYS=30                            # prune qartod/ outputs older than this (pull_ruv.py prunes raw/ itself)
# ---------------------------------------------------------------------------

set -u
QARTOD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily_ruv_$(date +%Y%m%d_%H%M%S).log"
exec >>"$LOG" 2>&1

echo "=== daily_ruv start $(date '+%F %T') on $(hostname) ==="

# --- conda -----------------------------------------------------------------
if [[ -z "$CONDA_SH" ]]; then
    for c in "$HOME/miniconda3" "$HOME/anaconda3" /opt/miniconda3 /opt/anaconda3 /opt/conda /usr/local/miniconda3; do
        [[ -f "$c/etc/profile.d/conda.sh" ]] && { CONDA_SH="$c/etc/profile.d/conda.sh"; break; }
    done
fi
if [[ ! -f "$CONDA_SH" ]]; then
    echo "conda.sh not found -- set CONDA_SH at the top of $0"
    exit 1
fi
# shellcheck disable=SC1090
source "$CONDA_SH"
conda activate "$CONDA_ENV" || { echo "conda activate $CONDA_ENV failed"; exit 1; }
echo "python: $(command -v python) ($(python --version 2>&1))"

# qc_walk.py / gen_thresholds.py import their siblings by name -> must run from qartod/
cd "$QARTOD_DIR" || exit 1
STATUS=0

# --- 1. harvest ------------------------------------------------------------
echo; echo "--- pull_ruv.py $(date '+%T') ---"
if python pull_ruv.py; then
    echo "pull: OK"
else
    echo "pull: FAILED (rc=$?) -- continuing with QC of files already on disk"
    STATUS=1
fi

# --- 2. QC -------------------------------------------------------------------
# Existing outputs are skipped, so this only touches the new hours.
# rc=1 also covers "a site has no entry in site_thresholds.py" -- see README.md.
echo; echo "--- qc_walk.py $(date '+%T') ---"
if python qc_walk.py; then
    echo "qc: OK"
else
    echo "qc: FAILED (rc=$?)"
    STATUS=1
fi

# --- 3. prune old QC outputs ------------------------------------------------
# pull_ruv.py prunes raw/ by filename date; do the same for qartod/ so it does
# not grow without bound.  Uses the date in the filename, not mtime.
echo; echo "--- prune qartod/ older than $KEEP_QC_DAYS days $(date '+%T') ---"
python - "$KEEP_QC_DAYS" <<'PY'
import re, sys
from datetime import datetime, timedelta
from qc_config import LOCAL_BASE, QC_DIRNAME
cutoff = (datetime.now() - timedelta(days=int(sys.argv[1]) - 1)).strftime("%Y%m%d")
rx = re.compile(r"^RDL[im]_[A-Za-z0-9]+_(\d{4})_(\d{2})_(\d{2})_\d{4}\.ruv$")
n = 0
for f in LOCAL_BASE.glob(f"*/*/{QC_DIRNAME}/*/*.ruv"):
    m = rx.match(f.name)
    if m and "".join(m.groups()) < cutoff:
        f.unlink(); n += 1
print(f"pruned {n} {QC_DIRNAME} file(s) older than {cutoff}")
PY

# --- 4. rotate logs ----------------------------------------------------------
ls -1t "$LOG_DIR"/daily_ruv_*.log 2>/dev/null | tail -n +$((KEEP_LOGS + 1)) | xargs -r rm -f --

echo; echo "=== daily_ruv end $(date '+%F %T') status=$STATUS ==="
exit $STATUS
