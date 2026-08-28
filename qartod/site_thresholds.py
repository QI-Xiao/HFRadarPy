"""Per-site QARTOD thresholds. GENERATED -- do not hand-edit.

Regenerate from inside the qartod/ directory:
    python gen_thresholds.py > site_thresholds.py
The redirect is required -- gen_thresholds.py prints to stdout.

Change policy in qc_config.py: percentiles and sigma rules for how these
numbers are derived, FIXED to pin a value across every site, OVERRIDES
to pin one for a single site.

Derived from 11791 files under /Users/xiao.qi/codar/sites.
Q204 percentiles: min=0.02 low=0.1
Q202 percentiles: high=0.99 max=0.999

Q206 (temporal gradient) is NOT derived -- the values below are the
QARTOD manual defaults and should be treated as provisional.

Which of these tests actually run, and which feed PRIM, is decided at
run time by qc_config.TESTS -- not here. Parameters are derived for
every test regardless, so a test can be switched back on without a
regeneration.

There is no fallback: a site+pattern absent from THRESHOLDS is skipped
by qc_walk.py, never processed with substitute numbers. Add a new site
by regenerating this file.
"""

THRESHOLDS = {
    'gerg|ISCY|IdealPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=323, low_count=478),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=140),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=134, warning_threshold=34, failure_threshold=51),
        # files=720 empty=0 (0%)  angRes=5deg velLimit=250 bearSD=17.1
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|ISCY|MeasPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=299, low_count=473),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=140),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=96, warning_threshold=16, failure_threshold=24),
        # files=720 empty=0 (0%)  angRes=5deg velLimit=250 bearSD=8.0
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|MBNP|MeasPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=333, low_count=423),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=50),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=148, warning_threshold=14, failure_threshold=21),
        # files=720 empty=7 (1%)  angRes=5deg velLimit=150 bearSD=7.0
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|PINS|IdealPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=105, low_count=143),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=50),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=183, warning_threshold=20, failure_threshold=30),
        # files=720 empty=0 (0%)  angRes=5deg velLimit=150 bearSD=10.1
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|PINS|MeasPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=308, low_count=443),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=40),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=115, warning_threshold=17, failure_threshold=26),
        # files=720 empty=0 (0%)  angRes=5deg velLimit=150 bearSD=8.6
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|PMGC|IdealPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=10, low_count=107),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=80),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        # files=598 empty=16 (3%)  angRes=5deg velLimit=150 bearSD=31.9
        # Q207 omitted: sigma=32deg, arithmetic-vs-circular mean differ 1deg
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|PMGC|MeasPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=43, low_count=106),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=70),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=108, warning_threshold=24, failure_threshold=35),
        # files=598 empty=11 (2%)  angRes=5deg velLimit=150 bearSD=11.8
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|SSDE|IdealPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=83, low_count=130),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=40),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=192, warning_threshold=29, failure_threshold=43),
        # files=720 empty=0 (0%)  angRes=5deg velLimit=180 bearSD=14.4
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|SSDE|MeasPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=180, low_count=238),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=40),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=148, warning_threshold=15, failure_threshold=23),
        # files=720 empty=0 (0%)  angRes=5deg velLimit=180 bearSD=7.7
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|UASA|IdealPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=170, low_count=249),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=140),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=181, warning_threshold=27, failure_threshold=40),
        # files=708 empty=0 (0%)  angRes=5deg velLimit=150 bearSD=13.3
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'gerg|UASA|MeasPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=131, low_count=247),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=25, smed_current_difference=140),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=113, warning_threshold=10, failure_threshold=15),
        # files=708 empty=0 (0%)  angRes=5deg velLimit=150 bearSD=4.9
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'usm|HBSP|IdealPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=273, low_count=468),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=10, smed_current_difference=50),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=195, warning_threshold=16, failure_threshold=24),
        # files=271 empty=67 (25%)  angRes=1deg velLimit=180 bearSD=8.1
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'usm|HBSP|MeasPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=325, low_count=567),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=10, smed_current_difference=50),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=197, warning_threshold=19, failure_threshold=28),
        # files=300 empty=67 (22%)  angRes=1deg velLimit=180 bearSD=9.3
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'usm|OBSP|IdealPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=10, low_count=11),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=10, smed_current_difference=60),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        # files=692 empty=37 (5%)  angRes=1deg velLimit=150 bearSD=41.0
        # Q207 omitted: sigma=41deg, arithmetic-vs-circular mean differ 0deg
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'usm|PCYC|IdealPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=869, low_count=962),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=10, smed_current_difference=50),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=173, warning_threshold=8, failure_threshold=12),
        # files=720 empty=0 (0%)  angRes=2deg velLimit=80 bearSD=4.0
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'usm|PCYC|MeasPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=253, low_count=356),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=10, smed_current_difference=50),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=160, warning_threshold=11, failure_threshold=17),
        # files=720 empty=0 (0%)  angRes=2deg velLimit=80 bearSD=5.6
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'usm|SGRV|IdealPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=10, low_count=11),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=10, smed_current_difference=60),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=136, warning_threshold=36, failure_threshold=55),
        # files=718 empty=166 (23%)  angRes=1deg velLimit=100 bearSD=18.2
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
    'usm|SGRV|MeasPattern': {
        'qc_qartod_maximum_velocity': dict(high_speed=200, max_speed=300),
        'qc_qartod_radial_count': dict(min_count=10, low_count=11),
        'qc_qartod_spatial_median': dict(smed_range_cell_limit=2.1, smed_angular_limit=10, smed_current_difference=60),
        'qc_qartod_temporal_gradient': dict(gradient_temp_fail=32, gradient_temp_warn=25),
        'qc_qartod_avg_radial_bearing': dict(reference_bearing=131, warning_threshold=20, failure_threshold=30),
        # files=718 empty=31 (4%)  angRes=1deg velLimit=100 bearSD=9.9
        # FIXED from qc_config.py applied: qc_qartod_maximum_velocity
    },
}
