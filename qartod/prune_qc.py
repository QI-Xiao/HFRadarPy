#!/usr/bin/env python3
"""
Delete QC output files (LOCAL_BASE/<inst>/<SITE>/qartod/<Pattern>/*.ruv) whose
filename date is older than DAYS.  pull_ruv.py prunes raw/ the same way; this
keeps qartod/ from growing without bound.

    python prune_qc.py            # uses DAYS below
    python prune_qc.py 45         # keep 45 days instead
"""
import re
import sys
from datetime import datetime, timedelta

from qc_config import LOCAL_BASE, QC_DIRNAME

DAYS = 30   # keep this many days, matching pull_ruv.DAYS

RUV_RE = re.compile(r"^RDL[im]_[A-Za-z0-9]+_(\d{4})_(\d{2})_(\d{2})_\d{4}\.ruv$")


def prune(days=DAYS):
    cutoff = (datetime.now() - timedelta(days=days - 1)).strftime("%Y%m%d")
    n = 0
    for f in LOCAL_BASE.glob(f"*/*/{QC_DIRNAME}/*/*.ruv"):
        m = RUV_RE.match(f.name)
        if m and "".join(m.groups()) < cutoff:
            f.unlink()
            n += 1
    print(f"Pruned {n} {QC_DIRNAME} file(s) older than {cutoff}")
    return n


if __name__ == "__main__":
    prune(int(sys.argv[1]) if len(sys.argv) > 1 else DAYS)
