# QARTOD processing for the local CODAR site tree

Applies the QARTOD radial tests to every `.ruv` file under `LOCAL_BASE`, writing
flagged copies alongside the raw data:

```
LOCAL_BASE/<institution>/<SITE>/raw/<Pattern>/RDLx_SITE_YYYY_MM_DD_HHMM.ruv
                              └─ qartod/<Pattern>/RDLx_SITE_YYYY_MM_DD_HHMM.ruv
```

QC does not modify measurements. It **appends columns** — `Q201`–`Q207` plus
`PRIM` — and records the thresholds it used in the file header, so a flag can
always be traced back to the settings that produced it.

## Order

**Run these from inside `qartod/`.** The scripts import their siblings by name,
and step 2 writes into the current directory.

```bash
cd qartod

# 1. edit policy
$EDITOR qc_config.py

# 2. re-derive the numbers            ← only if you changed a percentile,
python gen_thresholds.py \              a sigma rule, FIXED, or OVERRIDES
    > site_thresholds.py

# 3. see the plan, write nothing
python qc_walk.py --dry-run

# 4. trial one site into a scratch directory
python qc_walk.py --site ISCY --limit 24 --out /tmp/trial

# 5. the real run
python qc_walk.py

# ...or one antenna pattern at a time
python qc_walk.py --pattern MeasPattern
python qc_walk.py --pattern IdealPattern
```

**Step 2 is conditional** — except when a site is new, where it is required;
see below. Changing `TESTS` (which tests run, which feed `PRIM`) takes effect
immediately, since `qc_walk.py` reads it at run time. Only the data-derived
numbers need regenerating.

**Step 2 needs the `>` redirect.** `gen_thresholds.py` prints the module to
stdout rather than writing the file, so running it bare scrolls the thresholds
past you and leaves `site_thresholds.py` untouched — silently, with no error.
If a change to `qc_config.py` seems to have had no effect, check this first.

`qc_walk.py` can also be run from the repo root as `python qartod/qc_walk.py`,
since Python puts a script's own directory on `sys.path`. Do **not** do that
with step 2: `python qartod/gen_thresholds.py > site_thresholds.py` writes the
file to the repo root, where nothing imports it, and the real one in `qartod/`
goes stale without complaint.

## The four files

| File | What it is | Hand-edit? |
|---|---|---|
| `qc_config.py` | Policy: percentiles, test switches, overrides | **Yes** — this is the one you tune |
| `gen_thresholds.py` | Surveys the raw files, emits thresholds | Only to change how derivation works |
| `site_thresholds.py` | The derived numbers, one entry per site+pattern | **No** — regenerated; use `OVERRIDES` |
| `qc_walk.py` | Walks `raw/` → `qartod/` | Rarely |

The two with a `__main__` block are the scripts; the other two are modules the
scripts import. `site_thresholds.py` holds *measured* facts, `qc_config.py`
holds *chosen* ones — keeping that split is what makes the numbers auditable.

## The two switches

`qc_config.TESTS` gives every test two independent booleans:

```python
TESTS = {
    "qc_qartod_syntax":             dict(run=True, prim=True),   # Q201
    "qc_qartod_maximum_velocity":   dict(run=True, prim=True),   # Q202
    "qc_qartod_valid_location":     dict(run=True, prim=True),   # Q203
    "qc_qartod_radial_count":       dict(run=True, prim=True),   # Q204
    "qc_qartod_spatial_median":     dict(run=True, prim=True),   # Q205
    "qc_qartod_temporal_gradient":  dict(run=True,  prim=False),  # Q206
    "qc_qartod_avg_radial_bearing": dict(run=False, prim=False),  # Q207
}
```

(Current state — `Q207` is switched off entirely. Check the file for what is
set now.)

- **`run`** — run the test at all. `False` writes no flag column for it.
- **`prim`** — let its result feed `PRIM`, the column you filter on.

`run=True, prim=False` means the flag is recorded for diagnosis but cannot
condemn individual vectors. That is the right setting for `Q206` and `Q207`:
both are whole-file or coverage-dependent verdicts that should not reject every
row in a file.

**`Q201` and `Q203` cannot be disabled.** `qc_radial_file` calls
`qc_qartod_syntax()` unconditionally (`radials.py:147`) and calls
`qc_qartod_valid_location()` in an `else` branch when you supply no parameters
(`radials.py:153-157`). Setting `run=False` on either is refused at import
rather than silently ignored.

The table is validated when `qc_config.py` loads, so a contradiction stops the
run before any file is touched. It rejects `prim=True` with `run=False`,
non-boolean values, missing keys, disabling a non-optional test, and a table
where nothing feeds `PRIM`.

For a one-off experiment without editing the file:

```bash
python qc_walk.py --no-test qc_qartod_avg_radial_bearing
```

Safe to use freely — every output file records which tests actually ran in its
own `%QCTest` header, so the provenance survives even if you forget the flag.

## Adding a new site

Dropping files into `LOCAL_BASE` is not enough. A site+pattern with no entry in
`site_thresholds.py` is **not processed** — there are no fallback thresholds,
because flags computed against substitute numbers would look valid and mean
nothing. Regenerate first:

```bash
cd qartod
python gen_thresholds.py > site_thresholds.py
python qc_walk.py --dry-run          # confirm the new site now appears
python qc_walk.py
```

Forget the regeneration and the run tells you, before writing anything:

```
NOT PROCESSED -- no entry in site_thresholds.py:
    gerg|NEWX|MeasPattern  (3 files)
  Regenerate to add them, from inside the qartod/ directory:
    python gen_thresholds.py > site_thresholds.py
```

Skipped sites also appear in the table marked `no thresholds`, are listed again
in the summary, and make the **exit status 1** — so a cron job or CI run
notices rather than reporting success on a partial run. Other sites in the same
run are processed normally.

Calibrating a brand-new site means deriving percentiles from a short record, so
its thresholds will move as more data arrives. Re-run step 2 after the first
few weeks.

## Common changes

**Flag more or fewer files on `Q204`.** A percentile *is* a flag rate: setting
`Q204_LOW_PERCENTILE = 0.10` marks roughly 10% of a site's files suspect, by
arithmetic rather than because anything is wrong. Lower it for fewer flags.
Requires step 2.

**Stop deriving a number and just state it.** `FIXED` applies to every site and
merges parameter by parameter, so you can pin one and leave the rest derived:

```python
FIXED = {
    "qc_qartod_maximum_velocity": dict(high_speed=100),  # max_speed stays derived
}
```

Worth knowing before you pin both ends of `Q202`: the derived `max_speed` is
each site's own `%CurrentVelocityLimit`, which ranges 80–250 cm/s here. One
global number is loose for `PCYC` (limit 80) and tight for `ISCY` (limit 250).
Pinning only `high_speed` keeps a physically-correct fail threshold.

Naming a test that has no derived parameters *adds* it — that is how you reach
`Q203`'s `use_mask` and `res`, which are never derived. Requires step 2.

**Pin a threshold for one site.** Put it in `OVERRIDES`, keyed
`"<institution>|<SITE>|<Pattern>"`. It replaces the derived value and survives
regeneration:

```python
OVERRIDES = {
    "usm|OBSP|IdealPattern": {
        "qc_qartod_maximum_velocity": dict(high_speed=100, max_speed=200),
    },
}
```

An override replaces that test's whole parameter dict, where `FIXED` merges.
Other tests for that site are untouched, and the generated entry is annotated
`# OVERRIDES from qc_config.py applied`. Requires step 2.

Precedence is **derived → `FIXED` → `OVERRIDES`**. Values you supply either way
are used verbatim: `max_speed` is **not** capped at the site's
`%CurrentVelocityLimit` the way a derived value is.

Before the walk starts, every resulting parameter dict is checked against the
real `Radial` method signatures — unknown names, missing required ones, and
names `qc_radial_file` supplies itself. A typo fails at startup naming the
parameter, rather than partway through a run after files have been written.

**Stop a test running everywhere.** Set `run=False` in `TESTS`. No regeneration
— and `gen_thresholds.py` keeps deriving its parameters, so switching it back
on later needs no regeneration either.

## Safety

`hfradarpy`'s `to_ruv()` calls `os.remove()` on its target **before** writing,
and its `overwrite=False` guard compares the resolved source path against the
filename string as passed — a relative path defeats it. A mistargeted run would
destroy raw data with nothing to replace it.

`qc_walk.py` therefore asserts every output path contains the `qartod`
directory and never `raw`, before writing anything. **Keep the raw archive
read-only regardless.** Raw radial files are unreproducible instrument output.

Reruns skip existing outputs, so a large run is resumable; pass `--force` to
redo. A per-file failure is counted and reported without aborting the run.

## Requirements

The conda environment must have **`pandas < 3`**. Under pandas 3, `to_ruv()`
raises `TypeError: Invalid value '%%' for dtype 'float64'` and leaves a
truncated file on disk that still advertises its original row count. The pin is
applied to the environment only; `environment_dev.yml` is unchanged. See
`../TODO.md` item 1 for the underlying fix.

## Known limitations

- **`Q206` thresholds are not derived.** Deriving them needs a paired-
  consecutive-hour analysis that has not been run. `qc_config.Q206_FAIL` and
  `Q206_WARN` are the QARTOD manual defaults and should be treated as
  provisional.
- **One month is a thin calibration window.** The percentiles assume the
  survey period was mostly healthy. If a site was faulty during it, the
  thresholds have been calibrated to accept that fault.
- **Only the first file's header is read per site+pattern**
  (`gen_thresholds.py`, `hdr0 = hdr0 or hdr`). If a site's angular resolution
  or velocity limit changed mid-record, the pre-change values are used
  silently. Regenerate after any antenna re-aim, pattern re-measure, or
  resolution change.

- **An interrupted run can leave a bad file.** Ctrl-C during a write leaves a
  truncated file, and reruns skip existing outputs so it is not repaired
  automatically. Worse, three bare `except:` clauses in `hfradarpy/radials.py`
  swallow `KeyboardInterrupt` — the one in `qc_qartod_spatial_median` sets
  `Q205 = 2` for every row and lets the run continue, producing a
  complete-looking file whose spatial-median column is uniformly "not
  evaluated". After an interrupt, rerun the affected site with `--force`.
  See `../TODO.md` item 2b.

## Reference

`reference.html` in this directory is the fuller background — what each test
asks, how every parameter was chosen, the per-site table, and the reasoning
behind the non-obvious decisions. Open it in a browser, or read the published
copy at <https://claude.ai/code/artifact/d6bb82d3-60a3-4c22-a0bc-2260f6cbf0df>.
