#!/usr/bin/env python
"""Derive per-site QARTOD thresholds from the raw tree.

Run from inside the qartod/ directory, and keep the redirect -- this script
prints the module to stdout rather than writing the file itself:

    cd qartod
    python gen_thresholds.py > site_thresholds.py

Without the redirect the thresholds scroll past and site_thresholds.py is left
untouched. Run from the repo root, the file lands in the wrong directory and
the real one goes stale. Progress goes to stderr so it survives the redirect.

Reads the policy knobs from qc_config.py and every .ruv file under
LOCAL_BASE/<institution>/<SITE>/raw/<Pattern>/, and emits a site_thresholds.py
module holding one qc_values dict per site+pattern.

Only the header and the first (LLUV radial) table of each file are parsed.
Column positions come from %TableColumnTypes rather than being assumed, because
the sites do not all use the same column set.
"""
import math
import statistics as st
import sys
from pathlib import Path

import qc_config as cfg

HEADER_KEYS = ("AntennaBearing", "CurrentVelocityLimit", "AngularResolution",
               "RangeResolutionKMeters", "PatternType", "Origin")


def parse(path):
    """Return (header dict, [(BEAR, VELO, VFLG), ...]) for the first table."""
    hdr, rows, cols, in_table = {}, [], None, False
    with open(path, errors="replace") as fh:
        for line in fh:
            if line.startswith("%"):
                key = line[1:].split(":")[0]
                if key in HEADER_KEYS and key not in hdr:
                    hdr[key] = line.split(":", 1)[1].strip()
                elif key == "TableColumnTypes" and cols is None:
                    cols = line.split(":", 1)[1].split()
                elif key == "TableStart" and cols is not None:
                    in_table = True
                elif key == "TableEnd" and in_table:
                    break
                continue
            if in_table and line.strip():
                p = line.split()
                if len(p) == len(cols):
                    try:
                        rows.append((
                            float(p[cols.index("BEAR")]),
                            float(p[cols.index("VELO")]),
                            float(p[cols.index("VFLG")]) if "VFLG" in cols else 0.0,
                        ))
                    except (ValueError, IndexError):
                        pass
    return hdr, rows


def pct(values, q):
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * q))]


def circ_mean(degrees):
    s = sum(math.sin(math.radians(d)) for d in degrees)
    c = sum(math.cos(math.radians(d)) for d in degrees)
    return math.degrees(math.atan2(s, c)) % 360


def survey():
    """Walk every raw pattern directory and summarise it."""
    results = []
    pattern_dirs = sorted(cfg.LOCAL_BASE.glob(f"*/*/{cfg.RAW_DIRNAME}/*"))
    if not pattern_dirs:
        sys.exit(f"no raw pattern directories under {cfg.LOCAL_BASE}")

    for raw_dir in pattern_dirs:
        files = sorted(raw_dir.glob("*.ruv"))
        if not files:
            continue
        # <institution>/<SITE>/raw/<Pattern> -- the institution is part of the
        # key so two networks can use the same site code without colliding.
        institution, site, pattern = raw_dir.parts[-4], raw_dir.parts[-3], raw_dir.name
        counts, bear_means, velos, hdr0, empty = [], [], [], None, 0

        for fp in files:
            hdr, rows = parse(fp)
            hdr0 = hdr0 or hdr
            if not rows:
                empty += 1
                continue
            # qc_qartod_radial_count counts only rows with VFLG != 128,
            # so the statistic we derive the threshold from must match.
            counts.append(sum(1 for r in rows if r[2] != 128))
            bear_means.append(st.mean(r[0] for r in rows))
            velos.extend(abs(r[1]) for r in rows)

        if counts:
            results.append(dict(
                key=f"{institution}|{site}|{pattern}", n_files=len(files),
                empty=empty, counts=counts, bear_means=bear_means,
                velos=velos, hdr=hdr0))
    return results


def thresholds_for(s):
    """Turn one site's survey into a qc_values dict plus provenance notes."""
    hdr = s["hdr"]
    vel_limit = float(hdr.get("CurrentVelocityLimit") or 0)

    high = max(round(pct(s["velos"], cfg.Q202_HIGH_PERCENTILE) / 10) * 10, 10)
    mx = max(round(pct(s["velos"], cfg.Q202_MAX_PERCENTILE) / 10) * 10, high + 10)
    if vel_limit:
        mx = min(mx, vel_limit)

    min_count = max(round(pct(s["counts"], cfg.Q204_MIN_PERCENTILE)),
                    cfg.Q204_ABSOLUTE_FLOOR)
    low_count = max(round(pct(s["counts"], cfg.Q204_LOW_PERCENTILE)), min_count + 1)

    ang_res = float((hdr.get("AngularResolution") or "5").split()[0])
    ang_limit = int(max(cfg.Q205_ANGULAR_MINIMUM,
                        cfg.Q205_ANGULAR_MULTIPLIER * ang_res))

    bm = s["bear_means"]
    ref = round(st.median(bm))
    sigma = st.pstdev(bm) if len(bm) > 1 else 0.0
    disagree = abs(((st.mean(bm) - circ_mean(bm) + 180) % 360) - 180)
    q207_ok = sigma < cfg.Q207_MAX_SIGMA and disagree < cfg.Q207_MAX_CIRCULAR_DISAGREEMENT

    values = {
        "qc_qartod_maximum_velocity": dict(high_speed=high, max_speed=mx),
        "qc_qartod_radial_count": dict(min_count=min_count, low_count=low_count),
        "qc_qartod_spatial_median": dict(
            smed_range_cell_limit=cfg.Q205_RANGE_CELL_LIMIT,
            smed_angular_limit=ang_limit,
            smed_current_difference=high),
        "qc_qartod_temporal_gradient": dict(gradient_temp_fail=cfg.Q206_FAIL,
                                            gradient_temp_warn=cfg.Q206_WARN),
    }
    if q207_ok:
        values["qc_qartod_avg_radial_bearing"] = dict(
            reference_bearing=ref,
            warning_threshold=max(round(cfg.Q207_WARN_SIGMA * sigma), 5),
            failure_threshold=max(round(cfg.Q207_FAIL_SIGMA * sigma), 10))

    # No qc_qartod_primary_flag here: PRIM membership is policy, not a derived
    # number, and qc_walk.py injects it at run time from cfg.TESTS.

    # Precedence: derived -> FIXED (every site) -> OVERRIDES (this site).
    # FIXED merges parameter by parameter so one can be pinned while the rest
    # stay derived; OVERRIDES replaces a test's parameters wholesale.
    for test, params in cfg.FIXED.items():
        values.setdefault(test, {}).update(params)
    values.update(cfg.OVERRIDES.get(s["key"], {}))

    note = (f"files={s['n_files']} empty={s['empty']} "
            f"({s['empty'] / s['n_files'] * 100:.0f}%)  "
            f"angRes={ang_res:g}deg velLimit={vel_limit:g} bearSD={sigma:.1f}")
    if not q207_ok:
        note += (f"\n        # Q207 omitted: sigma={sigma:.0f}deg, "
                 f"arithmetic-vs-circular mean differ {disagree:.0f}deg")
    if cfg.FIXED:
        note += ("\n        # FIXED from qc_config.py applied: "
                 + ", ".join(sorted(cfg.FIXED)))
    if s["key"] in cfg.OVERRIDES:
        note += "\n        # OVERRIDES from qc_config.py applied"
    return values, note


def main():
    sites = survey()

    out = [
        '"""Per-site QARTOD thresholds. GENERATED -- do not hand-edit.',
        "",
        "Regenerate from inside the qartod/ directory:",
        "    python gen_thresholds.py > site_thresholds.py",
        "The redirect is required -- gen_thresholds.py prints to stdout.",
        "",
        "Change policy in qc_config.py: percentiles and sigma rules for how these",
        "numbers are derived, FIXED to pin a value across every site, OVERRIDES",
        "to pin one for a single site.",
        "",
        f"Derived from {sum(s['n_files'] for s in sites)} files under {cfg.LOCAL_BASE}.",
        f"Q204 percentiles: min={cfg.Q204_MIN_PERCENTILE} low={cfg.Q204_LOW_PERCENTILE}",
        f"Q202 percentiles: high={cfg.Q202_HIGH_PERCENTILE} max={cfg.Q202_MAX_PERCENTILE}",
        "",
        "Q206 (temporal gradient) is NOT derived -- the values below are the",
        "QARTOD manual defaults and should be treated as provisional.",
        "",
        "Which of these tests actually run, and which feed PRIM, is decided at",
        "run time by qc_config.TESTS -- not here. Parameters are derived for",
        "every test regardless, so a test can be switched back on without a",
        "regeneration.",
        "",
        "There is no fallback: a site+pattern absent from THRESHOLDS is skipped",
        "by qc_walk.py, never processed with substitute numbers. Add a new site",
        "by regenerating this file.",
        '"""',
        "",
        "THRESHOLDS = {",
    ]
    for s in sites:
        values, note = thresholds_for(s)
        out.append(f"    {s['key']!r}: {{")
        for test, params in values.items():
            args = ", ".join(f"{k}={v!r}" for k, v in params.items())
            out.append(f"        {test!r}: dict({args}),")
        out.append(f"        # {note}")
        out.append("    },")
    out.append("}")
    print("\n".join(out))


if __name__ == "__main__":
    main()
