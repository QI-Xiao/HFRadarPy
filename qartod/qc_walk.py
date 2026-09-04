#!/usr/bin/env python
"""Walk the raw CODAR site tree and write QARTOD-flagged copies.

    LOCAL_BASE/<institution>/<SITE>/raw/<Pattern>/RDLx_SITE_YYYY_MM_DD_HHMM.ruv
 -> LOCAL_BASE/<institution>/<SITE>/qartod/<Pattern>/RDLx_SITE_YYYY_MM_DD_HHMM.ruv

Run from inside this directory (qartod/), which is where its sibling modules
qc_config.py and site_thresholds.py live:

    python qc_walk.py --dry-run                  # plan only, writes nothing
    python qc_walk.py --site ISCY --limit 5      # small real run
    python qc_walk.py --institution usm          # one network
    python qc_walk.py --pattern MeasPattern      # measured antenna patterns only
    python qc_walk.py --pattern IdealPattern     # ideal antenna patterns only
    python qc_walk.py                            # everything
    python qc_walk.py --out /tmp/trial           # write to a scratch root

Safety:
  * Output paths are asserted to contain the qartod directory and never the raw
    one. hfradarpy's to_ruv() calls os.remove() on its target *before* writing,
    so a mistargeted run would destroy raw data with nothing to replace it.
  * Existing outputs are skipped unless --force, so reruns are cheap.
  * A per-file failure is counted and reported, never fatal.
  * A raw file whose data table has no rows (an empty radial -- the site
    produced no vectors that hour) is counted in the 'empty' column and left
    alone: qc_radial_file would silently write nothing for it anyway. Since no
    output file exists to mark it done, it is re-examined on every run; that
    costs one header parse per file per run, nothing more.
  * A site+pattern with no entry in site_thresholds.py is NOT processed. There
    are no fallback thresholds -- flags computed against substitute numbers
    would look valid and mean nothing. Such sites are listed before the run and
    again at the end, and make the exit status 1. Add one by regenerating
    site_thresholds.py.
"""
import argparse
import sys
import traceback
from collections import Counter
from pathlib import Path

import qc_config as cfg

try:
    from site_thresholds import THRESHOLDS
except ImportError:
    sys.exit("site_thresholds.py not found. From inside the qartod/ directory, "
             "run:\n    python gen_thresholds.py > site_thresholds.py\n"
             "(the redirect is required -- the script prints to stdout)")


def discover(base):
    """Yield (institution, site, pattern, [files]) per raw pattern directory."""
    for raw_dir in sorted(base.glob(f"*/*/{cfg.RAW_DIRNAME}/*")):
        if not raw_dir.is_dir():
            continue
        files = sorted(raw_dir.glob("*.ruv"))
        if files:
            yield raw_dir.parts[-4], raw_dir.parts[-3], raw_dir.name, files


def out_path(raw_file, base, out_base=None):
    """Map a raw file path to its qartod counterpart."""
    parts = list(raw_file.relative_to(base).parts)
    try:
        parts[parts.index(cfg.RAW_DIRNAME)] = cfg.QC_DIRNAME
    except ValueError:
        raise ValueError(f"no {cfg.RAW_DIRNAME!r} component in {raw_file}")
    return (out_base or base).joinpath(*parts)


def assert_safe(dst):
    """Refuse to write anywhere that is not a qartod directory."""
    parts = Path(dst).parts
    if cfg.QC_DIRNAME not in parts:
        raise RuntimeError(f"refusing to write outside {cfg.QC_DIRNAME}/: {dst}")
    if cfg.RAW_DIRNAME in parts:
        raise RuntimeError(f"refusing to write into {cfg.RAW_DIRNAME}/: {dst}")


def resolve_policy(disabled=()):
    """Return (tests to run, tests feeding PRIM) from cfg.TESTS.

    `disabled` is the --no-test escape hatch: names switched off for this run
    only. The choice is still recorded, because every output file carries its
    own %QCTest header listing exactly what ran.
    """
    unknown = set(disabled) - set(cfg.TESTS)
    if unknown:
        sys.exit(f"--no-test: unknown test(s) {', '.join(sorted(unknown))}\n"
                 f"known: {', '.join(cfg.TESTS)}")

    forced = [n for n in disabled if n in cfg.NON_OPTIONAL]
    if forced:
        sys.exit(f"--no-test: {', '.join(forced)} cannot be disabled -- "
                 f"qc_radial_file always calls them.")

    run = [n for n, f in cfg.TESTS.items() if f["run"] and n not in disabled]
    prim = [n for n in run if cfg.TESTS[n]["prim"]]
    if not prim:
        sys.exit("every PRIM test was disabled -- PRIM would mark every row as "
                 "pass. Nothing would be filtered.")
    return run, prim


# Parameters qc_radial_file supplies itself, so they must not appear in
# qc_values: it passes the previous hour's file to the temporal gradient test.
SUPPLIED_BY_CALLER = {"qc_qartod_temporal_gradient": {"r0"}}


def validate_params(dicts):
    """Check every qc_values dict against the real method signatures.

    This is the check that would have caught the radial_smed_* bug: a wrong
    keyword name only fails when the test is finally called, which in a long
    run means partway through, after files have already been written. Doing it
    up front turns that into a startup error naming the exact parameter.
    """
    import inspect

    from hfradarpy.radials import Radial

    problems = set()
    for label, values in dicts:
        for test, params in values.items():
            method = getattr(Radial, test, None)
            if method is None:
                problems.add(f"{label}: {test} is not a Radial method")
                continue
            sig = inspect.signature(method)
            supplied = SUPPLIED_BY_CALLER.get(test, set())
            accepted = {p for p in sig.parameters if p != "self"}
            required = {
                name for name, p in sig.parameters.items()
                if p.default is inspect.Parameter.empty
                and name != "self" and name not in supplied
            }

            for bad in sorted(set(params) - accepted):
                near = [a for a in sorted(accepted) if bad.endswith(a) or a.endswith(bad)]
                hint = f" -- did you mean {near[0]}?" if near else ""
                problems.add(f"{label}: {test} has no parameter {bad!r}{hint}")
            for miss in sorted(required - set(params)):
                problems.add(f"{label}: {test} needs {miss!r}, which is not set")
            for clash in sorted(set(params) & supplied):
                problems.add(f"{label}: {test} parameter {clash!r} is supplied "
                             f"by qc_radial_file and must not be set here")

    if problems:
        sys.exit("qc_values are invalid -- nothing was processed:\n  - "
                 + "\n  - ".join(sorted(problems)))


def apply_policy(qc_values, run, prim):
    """Drop parameters for disabled tests and attach the PRIM rollup.

    A test runs only if its key is present in qc_values, so dropping the key
    is what switches it off. Keys unknown to cfg.TESTS are passed through
    untouched rather than silently discarded.
    """
    out = {test: params for test, params in qc_values.items()
           if test not in cfg.TESTS or test in run}
    out["qc_qartod_primary_flag"] = dict(include=list(prim))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, default=cfg.LOCAL_BASE)
    ap.add_argument("--out", type=Path, default=None,
                    help="alternate output root (default: alongside raw)")
    ap.add_argument("--institution", action="append",
                    help="restrict to these institutions (e.g. gerg, usm)")
    ap.add_argument("--site", action="append", help="restrict to these site codes")
    ap.add_argument("--pattern", help="IdealPattern or MeasPattern")
    ap.add_argument("--limit", type=int, help="max files per site+pattern")
    ap.add_argument("--force", action="store_true", help="redo existing outputs")
    ap.add_argument("--dry-run", action="store_true", help="plan only")
    ap.add_argument("--no-test", action="append", default=[], metavar="NAME",
                    help="disable a test for this run only (repeatable); "
                         "the durable setting is cfg.TESTS")
    args = ap.parse_args(argv)

    run_tests, prim_tests = resolve_policy(args.no_test)

    if not args.dry_run:
        from hfradarpy.radials import Radial, qc_radial_file

        # Check every dict we might use before touching a single file, so a
        # bad parameter name fails at startup rather than mid-run.
        validate_params([(k, apply_policy(v, run_tests, prim_tests))
                         for k, v in THRESHOLDS.items()])

    off = [n for n in cfg.TESTS if n not in run_tests]
    print("tests run :", ", ".join(t.replace("qc_qartod_", "") for t in run_tests))
    print("into PRIM :", ", ".join(t.replace("qc_qartod_", "") for t in prim_tests))
    if off:
        print("disabled  :", ", ".join(t.replace("qc_qartod_", "") for t in off))
    print()

    # Split discovery before doing any work, so a site with no thresholds is
    # reported up front rather than after its files would have been written.
    # There is no fallback: without derived parameters a site is not processed.
    selected, unconfigured = [], []
    for institution, site, pattern, files in discover(args.base):
        if args.institution and institution not in args.institution:
            continue
        if args.site and site not in args.site:
            continue
        if args.pattern and pattern != args.pattern:
            continue
        key = f"{institution}|{site}|{pattern}"
        (selected if key in THRESHOLDS else unconfigured).append((key, files))

    if unconfigured:
        print("NOT PROCESSED -- no entry in site_thresholds.py:")
        for key, files in unconfigured:
            print(f"    {key}  ({len(files)} files)")
        print("  Regenerate to add them, from inside the qartod/ directory:")
        print("    python gen_thresholds.py > site_thresholds.py")
        print()

    total = Counter()
    print(f"{'institution|site|pattern':34} {'files':>6} {'todo':>6} {'ok':>6} "
          f"{'empty':>6} {'skip':>6} {'err':>5}")
    print("-" * 77)

    for key, files in unconfigured:
        print(f"{key:34} {len(files):>6} {'--':>6} {'--':>6} {'--':>6} {'--':>6} "
              f"{'--':>5}   no thresholds")

    for key, files in selected:
        qc_values = apply_policy(THRESHOLDS[key], run_tests, prim_tests)
        if args.limit:
            files = files[:args.limit]

        todo, skipped = [], 0
        for src in files:
            dst = out_path(src, args.base, args.out)
            assert_safe(dst)
            if dst.exists() and not args.force:
                skipped += 1
            else:
                todo.append((src, dst))

        ok = err = empty = 0
        if not args.dry_run:
            for src, dst in todo:
                try:
                    radial = Radial(str(src))
                    if not radial.is_valid():
                        # No data rows: qc_radial_file would run no tests and
                        # write no output. Count it as what it is, not as ok.
                        empty += 1
                        continue
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    qc_radial_file(radial, qc_values=qc_values,
                                   export="radial", save_path=str(dst.parent))
                    ok += 1
                except Exception:
                    err += 1
                    if err <= 3:
                        print(f"  ! {src.name}", file=sys.stderr)
                        traceback.print_exc(limit=2, file=sys.stderr)

        print(f"{key:34} {len(files):>6} {len(todo):>6} {ok:>6} "
              f"{empty:>6} {skipped:>6} {err:>5}")
        total.update(files=len(files), todo=len(todo), ok=ok,
                     empty=empty, skip=skipped, err=err)

    print("-" * 77)
    print(f"{'TOTAL':34} {total['files']:>6} {total['todo']:>6} "
          f"{total['ok']:>6} {total['empty']:>6} {total['skip']:>6} "
          f"{total['err']:>5}")

    if unconfigured:
        n = sum(len(files) for _, files in unconfigured)
        print(f"\n{len(unconfigured)} site+pattern(s), {n} files, were NOT "
              f"processed for lack of thresholds:")
        print("    " + "\n    ".join(key for key, _ in unconfigured))
    return 1 if total["err"] or unconfigured else 0


if __name__ == "__main__":
    sys.exit(main())
