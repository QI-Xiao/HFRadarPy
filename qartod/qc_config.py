"""Tunable knobs for QARTOD processing of the local CODAR site tree.

Edit this file, then re-run, from inside the qartod/ directory:

    cd qartod
    python gen_thresholds.py > site_thresholds.py

The redirect matters: gen_thresholds.py prints to stdout, so without it your
change is derived and then thrown away. Changing TESTS is the exception -- it
is read at run time and needs no regeneration.

Nothing here is derived from the data -- these are the *policy* choices that
decide how the derived numbers in site_thresholds.py come out. The data-derived
numbers themselves live in site_thresholds.py and should not be hand-edited
(they get regenerated); put deliberate overrides in OVERRIDES below instead.
"""
from pathlib import Path

# --------------------------------------------------------------------------
# Where the data lives
# --------------------------------------------------------------------------
#   LOCAL_BASE/<institution>/<SITE>/raw/<Pattern>/RDLx_SITE_YYYY_MM_DD_HHMM.ruv
#   LOCAL_BASE/<institution>/<SITE>/qartod/<Pattern>/  <- written by qc_walk.py
LOCAL_BASE = Path.home() / "codar/sites"

RAW_DIRNAME = "raw"
QC_DIRNAME = "qartod"


# --------------------------------------------------------------------------
# Q202  maximum velocity
# --------------------------------------------------------------------------
# max_speed is capped at the site's own %CurrentVelocityLimit: the radar cannot
# report a current faster than that, so anything sitting at the limit is a
# processing artefact rather than water movement.
Q202_HIGH_PERCENTILE = 0.99    # above this -> suspect
Q202_MAX_PERCENTILE = 0.999    # above this -> fail


# --------------------------------------------------------------------------
# Q204  radial count  -- HOW MUCH OF YOUR DATA GETS FLAGGED
# --------------------------------------------------------------------------
# The test compares each file's vector count against two numbers:
#
#     count <  min_count               -> 4  fail
#     min_count <= count <= low_count  -> 3  suspect
#     count >  low_count               -> 1  pass
#
# Both are chosen as percentiles of what each site actually produces. A
# percentile IS a flag rate: setting low_count at the 25th percentile means
# roughly 25% of that site's files will come back suspect -- by arithmetic,
# not because anything is wrong with them.
#
#   0.25 -> ~25% suspect.  Aggressive; surfaces every thin hour.
#   0.10 -> ~10% suspect.  Middle ground.
#   0.05 -> ~5%  suspect.  Conservative; only genuine outliers.
#
# Start wherever you like and change it -- regenerating is cheap.
Q204_MIN_PERCENTILE = 0.02   # below this -> fail
Q204_LOW_PERCENTILE = 0.10   # below this -> suspect

# Never let a derived min_count fall below this; a file with almost no vectors
# should fail regardless of how sparse the site normally is.
Q204_ABSOLUTE_FLOOR = 10


# --------------------------------------------------------------------------
# Q205  spatial median
# --------------------------------------------------------------------------
# The angular window is scaled by the site's %AngularResolution so the
# neighbourhood covers a comparable arc at 1, 2 and 5 degree sites. A fixed
# 10 degrees means ~2 neighbours at 5 deg but ~20 at 1 deg.
Q205_ANGULAR_MULTIPLIER = 5
Q205_ANGULAR_MINIMUM = 10
Q205_RANGE_CELL_LIMIT = 2.1


# --------------------------------------------------------------------------
# Q206  temporal gradient  -- NOT DERIVED FROM YOUR DATA
# --------------------------------------------------------------------------
# Deriving these needs a paired-consecutive-hour analysis that has not been
# run yet. These are the QARTOD manual defaults; treat them as provisional.
Q206_FAIL = 32
Q206_WARN = 25


# --------------------------------------------------------------------------
# Q207  average radial bearing
# --------------------------------------------------------------------------
# Q207 tests whether the mean bearing stays CONSTANT, so the thresholds follow
# each site's own hour-to-hour variability rather than a fixed 15/30.
Q207_WARN_SIGMA = 2
Q207_FAIL_SIGMA = 3

# The library averages BEAR arithmetically, which is meaningless when a site's
# coverage wraps through 0/360 (mostly the Ideal patterns, which span the full
# compass). Sites failing either check below get Q207 omitted entirely.
Q207_MAX_SIGMA = 20            # too jittery to test constancy
Q207_MAX_CIRCULAR_DISAGREEMENT = 15   # arithmetic mean is not a real direction


# --------------------------------------------------------------------------
# Which tests run, and which of them roll up into PRIM
# --------------------------------------------------------------------------
# Two independent switches per test:
#
#   run  -- run the test at all. False means no flag column is written.
#   prim -- let its result feed PRIM, the column you filter on.
#
# A test can run without feeding PRIM (run=True, prim=False): the flag is
# recorded for diagnosis but cannot condemn individual vectors. That is why
# Q206 and Q207 are off by default -- both are whole-file or coverage-dependent
# verdicts that should not reject every row in a file.
#
# Applied by qc_walk.py at RUN time, not baked into site_thresholds.py, so
# changing anything here takes effect on the next run with no regeneration.
# gen_thresholds.py keeps deriving parameters for disabled tests, so switching
# one back on needs no regeneration either.
#
# NON-OPTIONAL (see below): Q201 and Q203 always run regardless of what is set
# here, because hfradarpy's qc_radial_file calls them unconditionally.
TESTS = {
    "qc_qartod_syntax":             dict(run=True, prim=True),   # Q201
    "qc_qartod_maximum_velocity":   dict(run=True, prim=True),   # Q202
    "qc_qartod_valid_location":     dict(run=True, prim=True),   # Q203
    "qc_qartod_radial_count":       dict(run=True, prim=True),   # Q204
    "qc_qartod_spatial_median":     dict(run=True, prim=True),   # Q205
    "qc_qartod_temporal_gradient":  dict(run=True, prim=False),  # Q206
    "qc_qartod_avg_radial_bearing": dict(run=False, prim=False),  # Q207
}

# Tests hfradarpy runs whether or not you ask for them, so run=False would be
# a lie. radials.py:147 calls qc_qartod_syntax() flat out, and :153-157 calls
# qc_qartod_valid_location() in an else branch when no parameters are supplied.
# Turning these off means not using qc_radial_file at all.
NON_OPTIONAL = ("qc_qartod_syntax", "qc_qartod_valid_location")


def _validate_tests():
    """Fail loudly at import if the TESTS table is inconsistent.

    qc_qartod_primary_flag silently ignores names for tests that did not run,
    so an unnoticed contradiction here would produce a PRIM column that looks
    fine but quietly omits a test. Better to refuse to start.
    """
    known = set(TESTS)
    problems = []

    for name in NON_OPTIONAL:
        if name not in known:
            problems.append(f"{name}: non-optional but missing from TESTS")

    for name, flags in TESTS.items():
        if not name.startswith("qc_qartod_"):
            problems.append(f"{name}: not a qc_qartod_* test name")
        missing = {"run", "prim"} - set(flags)
        if missing:
            problems.append(f"{name}: missing {', '.join(sorted(missing))}")
            continue
        if not isinstance(flags["run"], bool) or not isinstance(flags["prim"], bool):
            problems.append(f"{name}: run and prim must be True or False")
            continue
        if flags["prim"] and not flags["run"]:
            problems.append(
                f"{name}: prim=True requires run=True -- a test that does not "
                f"run cannot feed PRIM, and it would be dropped silently")
        if name in NON_OPTIONAL and not flags["run"]:
            problems.append(
                f"{name}: cannot be disabled -- qc_radial_file always calls it. "
                f"Set run=True, or stop using qc_radial_file.")

    if not any(f["prim"] for f in TESTS.values() if isinstance(f.get("prim"), bool)):
        problems.append("no test has prim=True -- PRIM would flag every row as pass")

    if problems:
        raise ValueError(
            "qc_config.TESTS is invalid:\n  - " + "\n  - ".join(problems))


_validate_tests()


# --------------------------------------------------------------------------
# Fixed parameters, applied to EVERY site
# --------------------------------------------------------------------------
# Use this to stop deriving a number and just state it. Merged parameter by
# parameter, so you can pin one and leave the rest derived:
#
#     FIXED = {
#         # pin both ends of Q202 everywhere
#         "qc_qartod_maximum_velocity": dict(high_speed=100, max_speed=200),
#
#         # or pin only the suspect threshold and let max_speed stay derived
#         # (derived max_speed is the site's own %CurrentVelocityLimit, which
#         #  ranges 80-250 across these sites -- often worth keeping)
#         "qc_qartod_maximum_velocity": dict(high_speed=100),
#
#         # Q203 takes no derived parameters, so this is the only way to set it
#         "qc_qartod_valid_location": dict(res="low"),
#     }
#
# Precedence:  derived  ->  FIXED  ->  OVERRIDES
#
# Values are used verbatim. A derived max_speed is capped at the site's
# %CurrentVelocityLimit; a value you pin here is not.
#
# Naming a test that has no derived parameters ADDS it, which is how you enable
# a test the deriver skipped -- but supply every parameter it needs. Pinning
# only `warning_threshold` for Q207 at a site where the deriver omitted it
# leaves `reference_bearing` missing; qc_walk.py catches that before the run.
#
# Changing this requires regenerating site_thresholds.py.
FIXED = {
    "qc_qartod_maximum_velocity": dict(high_speed=200, max_speed=300),
}


# --------------------------------------------------------------------------
# Manual overrides, applied on top of the derived numbers
# --------------------------------------------------------------------------
# Keyed by "<institution>|<SITE>|<Pattern>". Anything here wins over the
# generated value. Use this when you know something the data does not show --
# an antenna that was re-aimed mid-record, a site you want to run loose while
# it is being repaired, and so on.
#
# Example:
#     OVERRIDES = {
#         "usm|OBSP|IdealPattern": {
#             "qc_qartod_radial_count": dict(min_count=10, low_count=30),
#         },
#     }
OVERRIDES = {}
