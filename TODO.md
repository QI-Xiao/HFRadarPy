# TODO — fork maintenance notes

Working branch: `updated` (fork: QI-Xiao/HFRadarPy, upstream: rowg/HFRadarPy)

## Done

- [x] **Fix mismatched kwargs in `qc_radial_file` defaults** — commit `da3ec65`.
      `radial_smed_*` keys did not match `qc_qartod_spatial_median`'s
      `smed_*` parameters, so the function raised `TypeError` whenever it
      was called without an explicit `qc_values`.
- [x] **Stop ignoring `tests/`; untrack `.idea/` and notebook checkpoints** — commit `8db2a8f`.
- [x] **Workaround: pin `pandas<3` in the conda env** (option A) so `to_ruv()` runs.
      Applied to the local env only; `environment_dev.yml` is unchanged.

## Open

### 1. Fix `to_ruv()` for pandas 3 (option B)

`hfradarpy/radials.py:2201-2202`

```python
rcopy.data.insert(0, "%%", np.nan)                            # float64 column
rcopy.data.iloc[0, rcopy.data.columns.get_loc("%%")] = "%%"   # string into float64
```

pandas >= 3 raises `TypeError: Invalid value '%%' for dtype 'float64'`.
Older pandas silently upcast the column to object.

Proposed fix — create the column as object dtype:

```python
rcopy.data.insert(0, "%%", pd.Series(np.nan, index=rcopy.data.index, dtype=object))
```

Once fixed, drop the `pandas<3` pin and confirm `.ruv` export still works.

### 2. `to_ruv()` deletes the target before writing

`hfradarpy/radials.py:2130-2131` calls `os.remove(filename)` unconditionally,
*before* the write. If the write then fails, the file is gone and nothing
replaces it.

The `overwrite=False` guard only compares `rcopy.full_file` (an absolute
`os.path.realpath`) against the filename string as passed. Loading with a
relative path and saving to the same relative path defeats it — verified:
a 148 KB source file was deleted with no output produced.

Fix: write to a temp file and rename into place on success, and compare
resolved paths in the guard rather than raw strings.

Mitigation until then: **always write QC output to a directory separate
from the raw inputs, and keep the raw archive read-only.**

### 2b. Interrupting a run can leave a broken or silently wrong file

Same root cause as item 2, but reached by Ctrl-C rather than an exception.
Two distinct outcomes, the second worse than the first.

**Truncated file.** `to_ruv()` removes the target, then writes header before
body. An interrupt mid-write leaves a file whose header claims
`%TableRows: N` above an empty or partial table. Because `qc_walk.py` skips
existing outputs, a later rerun does not repair it — `--force` is required.

**Silently wrong file.** `hfradarpy/radials.py` has three bare `except:`
clauses, which catch `BaseException` and therefore swallow
`KeyboardInterrupt`:

    to_ruv                      line 2191
    qc_qartod_valid_location    line 2360
    qc_qartod_spatial_median    line 2600

The Q205 handler sets `self.data["Q205"] = 2` for every row, logs a warning,
and lets the run continue to the next file. Q205 is the most expensive test,
so it is where an interrupt most often lands. The result is a complete-looking
file whose spatial-median column is uniformly "not evaluated" — and `Q205 = 2`
also happens legitimately when the test genuinely errors, so it is not
self-evidently an interrupted run. Repeated Ctrl-C can degrade several files
this way before the process exits.

`qc_walk.py`'s own handler is `except Exception`, which correctly does not
catch `KeyboardInterrupt`. The problem is entirely inside hfradarpy.

Fix: narrow the three bare `except:` clauses to `except Exception:`, and give
`to_ruv()` the temp-file-plus-rename treatment from item 2 — an interrupt then
leaves either the previous file or nothing, never a half-written one.

Mitigation until then: after an interrupt, rerun the affected site with
`--force`.

Worth adding either way: a verification pass comparing each output's
`%TableRows` against its actual row count, and flagging files whose `Q205`
column is uniformly 2.

### 3. `qc_qartod_stuck_value_version_2` reads the wrong config key

`hfradarpy/radials.py:170` — the branch tests for
`"qc_qartod_stuck_value_version_2" in qc_keys` but then reads
`qc_values["qc_qartod_stuck_value"]`, raising `KeyError` if only the v2
entry was supplied. Opt-in path only; not reachable from the defaults.
Not a QARTOD test (writes `Q901`), so low priority.

### 4. Missing test coverage

Neither `qc_radial_file()` nor `to_ruv()` is called anywhere in `tests/`.
Both were broken and the suite stayed green. Worth a test that runs
`qc_radial_file()` with defaults and reads the resulting `.ruv` back.

### 5. Four NetCDF tabular round-trip tests fail under pandas 2

`test_codar_radial_to_tabular_netcdf`, `test_wera_radial_to_tabular_netcdf`,
`test_wera_raw_to_quality_tabular_nc`, `test_miami_radial_tabular_nc`.

Cause is `datetime64[us]` in memory vs `datetime64[ns]` after round-trip;
`xds.identical()` is strict about dtype. Timestamp values are equal, so
this is a dtype-precision mismatch rather than data corruption. Only
affects the NetCDF path, not `.ruv`.

### 6. hfradmin's stored `qc_settings` use the buggy key names

`hfradmin/app/templates/processing/qc_settings.jinja2:156-158` writes:

    radial_smed_range_cell_limit
    radial_smed_angular_limit
    radial_smed_current_difference

These are the same `radial_`-prefixed names fixed in `da3ec65`. That commit
corrected `qc_radial_file`'s *defaults*; it does nothing for values passed in.
So any future code that reads `sites.qc_settings` from MongoDB and forwards it
to `qc_radial_file` will raise the same `TypeError`.

Fix when the two projects are merged: rename the three fields in the UI and
migrate existing documents. A translation shim in the caller would also work
but hides the mismatch.

Not urgent -- nothing currently reads `qc_settings`; it is storage plus UI only.

### 7. `QCOP` is expected downstream but never produced

`hfradmin/scripts/backfill_qc_vectors.py` lists `QCOP` in `QC_COLS`. hfradarpy
only ever *reads* `QCOP` (`radials.py:1540`) -- it is the manual operator flag,
set by a human, and no QARTOD test produces it. None of the local .ruv files
contain it either. Harmless (the backfill filters to available columns), but
worth knowing the column will be absent from generated qartod/ output.

### 8. `hfradarpy.__version__` reports `0+unknown`

Versioneer is not resolving the version through the editable install
(`git describe` reports `1.0.0.0-6-g05b7e5c` correctly). Cosmetic unless
provenance tracking of QC output is needed later.
