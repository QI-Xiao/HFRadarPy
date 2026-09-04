# pull_ruv.py -- harvesting radial files

Daily harvesting of CODAR HF-radar radial files (`.ruv`) from partner
institutions' servers into one uniform local layout.

## Local layout

```
LOCAL_BASE/                       (qc_config.LOCAL_BASE, default ~/codar/sites)
└── <institution>/                usm, gerg, ...
    └── <SITE>/                   4-letter site code
        └── raw/                  raw = no QC applied
            ├── IdealPattern/     RDLi_<SITE>_<YYYY>_<MM>_<DD>_<HHMM>.ruv
            └── MeasPattern/      RDLm_<SITE>_<YYYY>_<MM>_<DD>_<HHMM>.ruv
```

Every institution and site has exactly this shape, regardless of how the
files are organised on the remote server. Only the last `DAYS` (30) days of
data, by filename date, are kept locally.

## `pull_ruv.py`

Run daily by `daily_ruv.sh` (or by hand from inside `qartod/`, since it imports
`qc_config.py` for the data root). For each configured site it:

1. Lists the remote radials folder **recursively** over ssh
   (`find ... -name '*_<date>_*.ruv'` for each date in the window).
   Nothing is assumed about the remote folder structure — flat folders
   (usm), `IdealPattern/MeasPattern` sub-folders (gerg) or any future
   nesting are all handled the same way.
2. Decides each file's local home **from its own filename prefix**
   (`RDLi_` → `raw/IdealPattern/`, `RDLm_` → `raw/MeasPattern/`).
   Unrecognised names are reported and not pulled; files named for a
   different site are pulled with a warning.
3. Transfers with `rsync --files-from`, straight into the final folder, so
   rsync compares against the real local path and nothing is re-downloaded
   on later runs (only new or changed files are transferred).
4. Runs a local verification sweep over every `.ruv` under each site folder
   and moves anything not sitting at `raw/<Pattern>/<name>`. On a routine
   run this moves 0 files; it also re-homes an old-style `radials/` tree on
   the first run.
5. Prunes local files whose filename date is older than the window.
6. Prints a per-site inventory (`IdealPattern=N MeasPattern=N`, plus
   `STRAY=N` if anything is out of place) for a quick check.

Per-site outcomes are logged as `OK` / `SKIP` (no radials folder on the
remote) / `FAIL`.

### Adding an institution

Add one entry to `INSTITUTIONS` in `pull_ruv.py`:

```python
"name": {"host": "ssh-alias",            # from ~/.ssh/config (defaults to the key)
         "base": "/path/on/remote",      # <base>/<SITE>/<radials>/... holds the files
         "radials": "Radials",           # folder name under each site
         "sites": ["AAAA", "BBBB"]},
```

No other changes are needed; the remote structure below `<radials>` does
not matter.

### Requirements

- Python 3.8+ (standard library only, plus the sibling `qc_config.py`)
- `ssh` and `rsync` on the local machine; passwordless ssh to each `host`
- `find` on the remote hosts

### Email report

A commented-out block at the end of the script sends a summary through the
campus SMTP relay; fill in `EMAIL_TO` and uncomment to enable.
