#!/usr/bin/env python3
"""
Pull recent CODAR radial (.ruv) files from every institution's server into one
uniform local layout:

    LOCAL_BASE/<institution>/<SITE>/raw/IdealPattern/RDLi_<SITE>_<YYYY>_<MM>_<DD>_<HHMM>.ruv
    LOCAL_BASE/<institution>/<SITE>/raw/MeasPattern/RDLm_<SITE>_<YYYY>_<MM>_<DD>_<HHMM>.ruv

Nothing is assumed about how the remote side is organised.  The remote radials
folder is listed recursively and each .ruv is placed purely by its filename
prefix (RDLi / RDLm), so a flat folder (usm today), IdealPattern/MeasPattern
sub-folders (gerg today) or any future nesting all end up in the same place.
A final local sweep re-checks every .ruv on disk and moves anything that is
not where its name says it should be.

Adding an institution = adding one entry to INSTITUTIONS.
"""
import re, shlex, subprocess, tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
# import smtplib
# from email.message import EmailMessage

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
INSTITUTIONS = {
    # key  = local folder name under LOCAL_BASE
    # host = ssh alias from ~/.ssh/config (defaults to the key if omitted)
    # base/radials = where each site's radial tree lives on the remote host:
    #                <base>/<SITE>/<radials>/...   (any structure below that)
    "usm":  {"host": "usm",
             "base": "/home/codar/sites",
             "radials": "radials",
             "sites": ["CPFL", "GPTP", "HBSP", "OBSP", "PCYC", "SGRV", "SISL", "SWPP"]},
    "gerg": {"host": "gerg",
             "base": "/data/CODAR",
             "radials": "Radials",
             "sites": "ANWR CPLF ISCY KRGC MBNP PINS PMGC RLVR SSDE SWPP UASA".split()},
}
# Data root and folder names are shared with the QC step -- change them in qc_config.py
from qc_config import LOCAL_BASE, RAW_DIRNAME as RAW_DIR   # "raw" = no QC applied
PATTERN_DIRS = {"RDLi": "IdealPattern", "RDLm": "MeasPattern"}
DAYS = 30
# EMAIL_TO = "xiao.qi@tamu.edu"

# RDLm_GPTP_2026_06_01_1000.ruv
RUV_RE = re.compile(r"^(RDL[im])_([A-Za-z0-9]+)_(\d{4})_(\d{2})_(\d{2})_(\d{4})\.ruv$")

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
log = []
def note(m):
    log.append(m)
    print(m)

def parse_ruv(name):
    """Return (pattern_dir, site, 'YYYYMMDD') for a radial filename, else None."""
    m = RUV_RE.match(name)
    if not m:
        return None
    return PATTERN_DIRS[m.group(1)], m.group(2), m.group(3) + m.group(4) + m.group(5)

def local_home(site_dir, name):
    """Where a file with this name belongs locally, or None if unrecognised."""
    p = parse_ruv(name)
    return site_dir / RAW_DIR / p[0] / name if p else None

def ensure_layout(site_dir):
    for d in PATTERN_DIRS.values():
        (site_dir / RAW_DIR / d).mkdir(parents=True, exist_ok=True)

def list_remote(host, remote_dir, dates):
    """
    Recursively list .ruv files under remote_dir whose name carries one of the
    wanted dates.  Returns a list of absolute remote paths, None if the folder
    does not exist, or raises RuntimeError on ssh/find failure.
    """
    names = " -o ".join(f"-name '*_{d}_*.ruv'" for d in dates)
    q = shlex.quote(remote_dir)
    cmd = f"test -d {q} || exit 3; find {q} -type f \\( {names} \\)"
    r = subprocess.run(["ssh", host, cmd], capture_output=True, text=True)
    if r.returncode == 3:
        return None
    if r.returncode not in (0, 1):            # 1 = find hit unreadable entries but still listed
        raise RuntimeError(f"ssh/find rc={r.returncode}: {r.stderr.strip()}")
    if r.stderr.strip():
        note(f"  WARN remote find: {r.stderr.strip().splitlines()[0]}")
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]

def sync_site(inst, cfg, site, dates):
    """Pull one site's files into LOCAL_BASE/<inst>/<site>/raw/<Pattern>/."""
    host = cfg.get("host", inst)
    remote_dir = f"{cfg['base']}/{site}/{cfg['radials']}"
    site_dir = LOCAL_BASE / inst / site

    remote_files = list_remote(host, remote_dir, dates)
    if remote_files is None:
        return "skip", f"no {cfg['radials']} folder on {host}"
    ensure_layout(site_dir)

    # group wanted files by (remote parent folder, local destination folder)
    groups = defaultdict(list)
    unknown, foreign = [], []
    for rp in remote_files:
        rp = Path(rp)
        parsed = parse_ruv(rp.name)
        if parsed is None:
            unknown.append(rp.name); continue
        pattern_dir, fsite, stamp = parsed
        if fsite != site:
            foreign.append(rp.name)           # still pulled - it sits in this site's folder
        groups[(str(rp.parent), pattern_dir)].append(rp.name)
    if unknown:
        note(f"  WARN {len(unknown)} unrecognised file(s) not pulled, e.g. {unknown[0]}")
    if foreign:
        note(f"  WARN {len(foreign)} file(s) named for another site, e.g. {foreign[0]}")

    n = 0
    for (remote_parent, pattern_dir), names in sorted(groups.items()):
        dest = site_dir / RAW_DIR / pattern_dir
        with tempfile.NamedTemporaryFile("w", suffix=".lst", delete=True) as lst:
            lst.write("\n".join(names) + "\n"); lst.flush()
            cmd = ["rsync", "-az", f"--files-from={lst.name}",
                   f"{host}:{remote_parent}/", f"{dest}/"]
            if subprocess.run(cmd).returncode != 0:
                return "fail", f"rsync from {remote_parent} -> {dest}"
        n += len(names)
    return "ok", f"{n} file(s) in window"

def normalize_site(site_dir):
    """
    Verify every .ruv under the site folder sits at raw/<Pattern>/<name>
    according to its own filename; move anything that doesn't.  Returns the
    number of files moved.  Empty folders left behind are removed.
    """
    if not site_dir.is_dir():
        return 0
    ensure_layout(site_dir)
    moved = 0
    for f in sorted(site_dir.rglob("*.ruv")):
        home = local_home(site_dir, f.name)
        if home is None:
            note(f"  WARN unrecognised local file left alone: {f}"); continue
        if f == home:
            continue
        if home.exists():
            note(f"  WARN duplicate, left alone: {f} (already have {home})"); continue
        home.parent.mkdir(parents=True, exist_ok=True)
        f.rename(home); moved += 1
        note(f"  moved {f.relative_to(site_dir)} -> {home.relative_to(site_dir)}")
    keep = {site_dir / RAW_DIR / d for d in PATTERN_DIRS.values()} | {site_dir / RAW_DIR, site_dir}
    for d in sorted((p for p in site_dir.rglob("*") if p.is_dir()), reverse=True):
        if d not in keep and not any(d.iterdir()):
            d.rmdir()
    return moved

def prune_old(cutoff):
    """Delete local radials whose filename date is older than cutoff (YYYYMMDD)."""
    deleted = 0
    for f in LOCAL_BASE.rglob("*.ruv"):
        p = parse_ruv(f.name)
        if p and p[2] < cutoff:
            f.unlink(); deleted += 1
            print(f"Pruned {f}")
    return deleted

def summarize():
    note("\nLocal inventory:")
    for inst in INSTITUTIONS:
        for site_dir in sorted(p for p in (LOCAL_BASE / inst).glob("*") if p.is_dir()):
            counts = {d: len(list((site_dir / RAW_DIR / d).glob("*.ruv"))) for d in PATTERN_DIRS.values()}
            stray = len(list(site_dir.rglob("*.ruv"))) - sum(counts.values())
            line = f"  {inst}/{site_dir.name:<6}" + "  ".join(f"{d}={n:>5}" for d, n in counts.items())
            note(line + (f"  STRAY={stray}" if stray else ""))

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y_%m_%d") for i in range(DAYS)]
    ok, skipped, failed = [], [], []

    for inst, cfg in INSTITUTIONS.items():
        for site in cfg["sites"]:
            tag = f"{inst}/{site}"
            try:
                status, msg = sync_site(inst, cfg, site, dates)
            except Exception as e:
                status, msg = "fail", str(e)
            note(f"{status.upper()}: {tag} - {msg}")
            {"ok": ok, "skip": skipped, "fail": failed}[status].append(tag)

    # verify placement of everything on disk, whatever its origin
    moved = sum(normalize_site(LOCAL_BASE / inst / site)
                for inst, cfg in INSTITUTIONS.items() for site in cfg["sites"])
    note(f"Re-homed {moved} misplaced file(s)")

    cutoff = (datetime.now() - timedelta(days=DAYS - 1)).strftime("%Y%m%d")
    deleted = prune_old(cutoff)
    note(f"Pruned {deleted} file(s) older than {cutoff}")
    summarize()

    # # email via campus relay (no `mail`/MTA needed)
    # status = "PROBLEM" if failed else "OK"
    # msg = EmailMessage()
    # msg["Subject"] = f"[CODAR pull] {status} - {datetime.now():%Y-%m-%d} - {len(ok)} ok, {len(skipped)} skipped, {len(failed)} failed"
    # msg["From"] = EMAIL_TO
    # msg["To"] = EMAIL_TO
    # msg.set_content(
    #     f"OK:      {ok or 'none'}\nSkipped: {skipped or 'none'}\n"
    #     f"Failed:  {failed or 'none'}\nPruned:  {deleted}\n\n--- log ---\n" + "\n".join(log))
    #
    # with smtplib.SMTP("smtp.tamu.edu", 587) as s:   # same relay info you'd need for msmtp
    #     s.starttls()
    #     # s.login("netid", "password")   # if the relay requires auth
    #     s.send_message(msg)
