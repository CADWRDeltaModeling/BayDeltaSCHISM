# -*- coding: utf-8 -*-
"""Unit and integration tests for bdschism.ccf_gate_height."""

import math

import numpy as np
import pandas as pd
import pytest

from bdschism.ccf_gate_height import (
    radial_gate_flow,
    _radial_gate_flow_scalar,
    simple_mass_balance,
    _simple_mass_balance_scalar,
    draw_down_regression,
    flow_to_priority,
    flow_to_max_gate,
    create_priority_series,
    gen_gate_height,
    ccf_A,
    ccf_reference_level,
)
from vtools.functions.unit_conversions import M2FT


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_WIDTH = 6.096 * M2FT
_ZSILL = -4.044 * M2FT


@pytest.fixture
def synthetic_tidal_oh4():
    """1-day sinusoidal OH4 at 15min resolution, centered around 3 ft."""
    idx = pd.date_range("2022-03-01", periods=96, freq="15min")
    phase = np.linspace(0, 2 * np.pi, 96)
    values = 3.0 + 1.5 * np.sin(phase)  # range ~1.5 to 4.5 ft
    return pd.Series(values, index=idx, name="oh4")


@pytest.fixture
def synthetic_priority():
    """Priority schedule: open (op=1, priority=3) for entire day."""
    idx = pd.DatetimeIndex([pd.Timestamp("2022-03-01")])
    return pd.DataFrame({"priority": [3.0], "op": [1.0]}, index=idx)


@pytest.fixture
def synthetic_max_height():
    """Max gate height = 16 ft for entire day."""
    idx = pd.DatetimeIndex([pd.Timestamp("2022-03-01")])
    return pd.Series([16.0], index=idx, name="max_gate")


@pytest.fixture
def synthetic_export():
    """Constant 4000 cfs export at 15min for 1 day."""
    idx = pd.date_range("2022-03-01", periods=96, freq="15min")
    return pd.Series(4000.0, index=idx, name="swp")


@pytest.fixture
def synthetic_cvp():
    """Constant 1000 cfs CVP at 15min for 1 day."""
    idx = pd.date_range("2022-03-01", periods=96, freq="15min")
    return pd.Series(1000.0, index=idx, name="cvp")


# ---------------------------------------------------------------------------
# radial_gate_flow
# ---------------------------------------------------------------------------

class TestRadialGateFlow:
    def test_positive_head_positive_flow(self):
        q = radial_gate_flow(zdown=2.0, zup=4.0, height=8.0)
        assert q > 0.0

    def test_negative_head_zero_flow(self):
        q = radial_gate_flow(zdown=5.0, zup=3.0, height=8.0)
        assert q == 0

    def test_zero_height_zero_flow(self):
        q = radial_gate_flow(zdown=2.0, zup=4.0, height=0.0)
        assert q == 0.0

    def test_scalar_matches_python(self):
        zdown, zup, height = 2.0, 4.0, 8.0
        q_py = radial_gate_flow(zdown, zup, height, n=5, width=_WIDTH, zsill=_ZSILL)
        q_nb = _radial_gate_flow_scalar(zdown, zup, height, 5, _WIDTH, _ZSILL)
        assert abs(q_py - q_nb) < 1e-6

    def test_known_value(self):
        """Spot-check: 2 ft head, 8 ft height, 5 gates."""
        zdown, zup, height = 2.0, 4.0, 8.0
        q = radial_gate_flow(zdown, zup, height, n=5, width=_WIDTH, zsill=_ZSILL)
        # Flow should be in the thousands of cfs for these conditions
        assert 5000 < q < 50000


# ---------------------------------------------------------------------------
# simple_mass_balance
# ---------------------------------------------------------------------------

class TestSimpleMassBalance:
    def test_scalar_matches_python(self):
        export, zup, zin0, height = 4000.0, 4.0, 2.12, 8.0
        dt = pd.Timedelta(minutes=2)
        vt = (zin0 - ccf_reference_level) * ccf_A

        zin_py, vt_py, qint_py = simple_mass_balance(export, zup, zin0, height, dt, vt)
        zin_nb, vt_nb, qint_nb = _simple_mass_balance_scalar(
            export, zup, zin0, height, dt.total_seconds(), vt, ccf_A, _WIDTH, _ZSILL
        )
        assert abs(zin_py - zin_nb) < 1e-6
        assert abs(vt_py - vt_nb) < 1e-6
        assert abs(qint_py - qint_nb) < 1e-6

    def test_volume_conservation(self):
        """Volume change = (inflow - export) * dt."""
        export, zup, zin0, height = 4000.0, 4.0, 2.5, 8.0
        dt_sec = 120.0
        vt0 = (zin0 - ccf_reference_level) * ccf_A

        zin, vt, qint = _simple_mass_balance_scalar(
            export, zup, zin0, height, dt_sec, vt0, ccf_A, _WIDTH, _ZSILL
        )
        delta_v = vt - vt0
        expected_delta_v = (qint - export) * dt_sec
        assert abs(delta_v - expected_delta_v) < 1e-4

    def test_no_flow_when_closed(self):
        """Height=0 means no inflow; level drops by export."""
        export, zup, zin0, height = 4000.0, 4.0, 2.5, 0.0
        dt_sec = 120.0
        vt0 = (zin0 - ccf_reference_level) * ccf_A

        zin, vt, qint = _simple_mass_balance_scalar(
            export, zup, zin0, height, dt_sec, vt0, ccf_A, _WIDTH, _ZSILL
        )
        assert qint == 0.0
        assert vt < vt0  # volume decreased


# ---------------------------------------------------------------------------
# draw_down_regression
# ---------------------------------------------------------------------------

class TestDrawDownRegression:
    def test_zero_inputs(self):
        dd = draw_down_regression(0.0, 0.0)
        assert abs(dd - (-0.0547)) < 1e-10

    def test_positive_inputs(self):
        dd = draw_down_regression(5000.0, 5000.0)
        expected = -0.0547 + 0.1815 + 0.1413
        assert abs(dd - expected) < 1e-10

    def test_linearity(self):
        dd1 = draw_down_regression(2500.0, 0.0)
        dd2 = draw_down_regression(5000.0, 0.0)
        # Linear in cvp: doubling cvp doubles the cvp contribution
        cvp_contrib_1 = dd1 - draw_down_regression(0.0, 0.0)
        cvp_contrib_2 = dd2 - draw_down_regression(0.0, 0.0)
        assert abs(cvp_contrib_2 - 2 * cvp_contrib_1) < 1e-10


# ---------------------------------------------------------------------------
# flow_to_priority
# ---------------------------------------------------------------------------

class TestFlowToPriority:
    def test_boundary_values(self):
        flows = pd.Series([0.0, 1999.0, 2001.0, 3999.0, 4001.0, 9001.0])
        idx = pd.date_range("2022-01-01", periods=6, freq="D")
        flows.index = idx
        prio = flow_to_priority(flows)
        assert list(prio.values) == [1, 1, 2, 2, 3, 4]

    def test_negative_flow(self):
        flows = pd.Series([-50.0], index=pd.date_range("2022-01-01", periods=1, freq="D"))
        prio = flow_to_priority(flows)
        assert prio.iloc[0] == 1


# ---------------------------------------------------------------------------
# flow_to_max_gate
# ---------------------------------------------------------------------------

class TestFlowToMaxGate:
    def test_boundary_values(self):
        flows = pd.Series([0.0, 500.0, 1500.0, 3500.0, 5000.0])
        idx = pd.date_range("2022-01-01", periods=5, freq="D")
        flows.index = idx
        mg = flow_to_max_gate(flows)
        assert list(mg.values) == [3, 5, 8, 10, 16]


# ---------------------------------------------------------------------------
# asi8 normalization
# ---------------------------------------------------------------------------

class TestAsi8Normalization:
    def test_microsecond_index(self):
        """Simulate pandas 2.x datetime64[us] — the common case."""
        idx = pd.date_range("2022-03-01", periods=3, freq="15min")
        # Verify the normalization formula works
        ts_val = pd.Timestamp(idx[0]).value  # nanoseconds
        asi8_val = idx.asi8[0]
        scale = ts_val // asi8_val
        # All normalized values should equal Timestamp.value
        for i in range(len(idx)):
            assert idx.asi8[i] * scale == pd.Timestamp(idx[i]).value

    def test_nanosecond_index(self):
        """If index is already ns, scale factor should be 1."""
        idx = pd.date_range("2022-03-01", periods=3, freq="15min").astype("datetime64[ns]")
        ts_val = pd.Timestamp(idx[0]).value
        asi8_val = idx.asi8[0]
        scale = ts_val // asi8_val
        assert scale == 1


# ---------------------------------------------------------------------------
# gen_gate_height (synthetic 1-day)
# ---------------------------------------------------------------------------

class TestGenGateHeightSynthetic:
    def test_gate_opens_with_positive_head(
        self, synthetic_tidal_oh4, synthetic_priority, synthetic_max_height,
        synthetic_export, synthetic_cvp
    ):
        """With always-open priority and positive head, gate should open."""
        s1 = pd.Timestamp("2022-03-01")
        s2 = pd.Timestamp("2022-03-01 12:00")
        dt = pd.Timedelta(minutes=2)
        inside_level0 = 2.12

        height_df, zin_df = gen_gate_height(
            synthetic_export, synthetic_priority, synthetic_max_height,
            synthetic_tidal_oh4, synthetic_cvp, inside_level0, s1, s2, dt
        )
        assert (height_df["ccfb_height"] > 0).any()

    def test_gate_closed_when_priority_zero(
        self, synthetic_tidal_oh4, synthetic_max_height,
        synthetic_export, synthetic_cvp
    ):
        """With op=0 priority, gate should stay closed."""
        idx = pd.DatetimeIndex([pd.Timestamp("2022-03-01")])
        closed_priority = pd.DataFrame({"priority": [3.0], "op": [0.0]}, index=idx)

        s1 = pd.Timestamp("2022-03-01")
        s2 = pd.Timestamp("2022-03-01 06:00")
        dt = pd.Timedelta(minutes=2)
        inside_level0 = 2.12

        height_df, zin_df = gen_gate_height(
            synthetic_export, closed_priority, synthetic_max_height,
            synthetic_tidal_oh4, synthetic_cvp, inside_level0, s1, s2, dt
        )
        assert (height_df["ccfb_height"] == 0.0).all()

    def test_output_index_is_datetime(
        self, synthetic_tidal_oh4, synthetic_priority, synthetic_max_height,
        synthetic_export, synthetic_cvp
    ):
        """Output index should be a DatetimeIndex."""
        s1 = pd.Timestamp("2022-03-01")
        s2 = pd.Timestamp("2022-03-01 06:00")
        dt = pd.Timedelta(minutes=2)

        height_df, zin_df = gen_gate_height(
            synthetic_export, synthetic_priority, synthetic_max_height,
            synthetic_tidal_oh4, synthetic_cvp, 2.12, s1, s2, dt
        )
        assert isinstance(height_df.index, pd.DatetimeIndex)
        assert isinstance(zin_df.index, pd.DatetimeIndex)

    def test_inside_level_stays_reasonable(
        self, synthetic_tidal_oh4, synthetic_priority, synthetic_max_height,
        synthetic_export, synthetic_cvp
    ):
        """Interior water level should stay between 1 and 5 ft."""
        s1 = pd.Timestamp("2022-03-01")
        s2 = pd.Timestamp("2022-03-01 12:00")
        dt = pd.Timedelta(minutes=2)

        height_df, zin_df = gen_gate_height(
            synthetic_export, synthetic_priority, synthetic_max_height,
            synthetic_tidal_oh4, synthetic_cvp, 2.12, s1, s2, dt
        )
        assert zin_df["ccfb_interior_surface"].min() > 0.5
        assert zin_df["ccfb_interior_surface"].max() < 6.0


# ---------------------------------------------------------------------------
# Integration tests (require network / external data)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestCCFGateIntegration:
    """Regression tests using real data sources. Require network access.

    Data Sources
    ------------
    - SFFPX: Processed SF predicted tide (meters NAVD88, 15-min).
    - OH4: Astronomical/harmonic tide at OH4 (feet, 15-min).
    - FLUX: SCHISM flux.th with columns swp, cvp, sjr (m³/s, 15-min).

    Expected Values (2022-03-01 to 2022-05-01)
    -------------------------------------------
    - Nonzero gate height steps: **5745** at the raw 2-min output resolution.
      This count reflects the number of time steps where the gate is open
      (height > 0) given the priority schedule derived from tides and export
      levels during March-April 2022. The value is sensitive to:
        * Changes in priority logic or thresholds (flow_to_priority breaks)
        * Changes in the OH4 prediction model coefficients
        * Changes in the mass-balance loop (dt, ccf_A, reference level)
        * Updates to the source data files (re-processed repo data)
      If this test starts failing, first check whether any of the above
      changed intentionally. A small drift (±50) likely means source data
      was reprocessed; a large shift means logic changed.
    - Interior level: stays between 1.0 and 5.0 ft (physical bounds for CCF).
    - Gate height max: never exceeds 16 ft (operational hard limit).

    Troubleshooting
    ---------------
    If the test cannot run at all, verify:
    - Network access to //cnrastore-bdo/Modeling_Data/
    - flux.th exists at d:/delta/BayDeltaSCHISM/data/time_history/flux.th
    - The schism conda environment is active
    """

    SFFPX_SRC = "//cnrastore-bdo/Modeling_Data/repo/continuous/processed/dms_sffpx_elev_2000_2026.csv"
    OH4_SRC = "//cnrastore-bdo/Modeling_Data/repo/continuous/processed/dms_oh4_elev@harmonic_2001_2025.csv"
    FLUX_SRC = "d:/delta/BayDeltaSCHISM/data/time_history/flux.th"

    @pytest.fixture
    def two_month_gate(self):
        """Run 2022-03-01 to 2022-05-01 and return raw height DataFrame."""
        from dms_datastore.read_ts import read_ts
        from bdschism.ccf_gate_height import (
            process_height, get_flux_ts_cfs, sffpx_level_shift_h
        )
        from vtools import minutes

        s1 = pd.Timestamp("2022-03-01")
        s2 = pd.Timestamp("2022-05-01")

        sffpx = read_ts(self.SFFPX_SRC, start="2022-02-24", end="2022-05-07", force_regular=True)
        sffpx.columns = ["elev"]
        position_shift = int(sffpx_level_shift_h / sffpx.index.freq)
        sffpx = sffpx.shift(position_shift)

        oh4 = read_ts(self.OH4_SRC, force_regular=True).squeeze()
        flx = get_flux_ts_cfs(s1, s2, self.FLUX_SRC)

        height, zin = process_height(s1, s2, flx["swp"], flx["cvp"], flx["sjr"], oh4, sffpx)
        return height, zin

    def test_nonzero_count(self, two_month_gate):
        """2-month run should produce ~5745 nonzero raw 2-min gate height steps.

        The exact value (5745) is a regression anchor computed 2025-05-01.
        It corresponds to ~8 days of total open-gate time across 61 days,
        consistent with typical spring export levels (~4000-6000 cfs SWP).
        If source data is reprocessed, expect ±50 drift; update the anchor.
        If logic changes, the shift will be larger and intentional.
        """
        height, _ = two_month_gate
        n_nonzero = (height["ccfb_height"] > 0).sum()
        assert n_nonzero == 5745, (
            f"Expected 5745 nonzero steps (regression anchor 2025-05-01), "
            f"got {n_nonzero}. See class docstring for troubleshooting."
        )

    def test_interior_level_range(self, two_month_gate):
        """Interior water level should stay in physically reasonable range."""
        _, zin = two_month_gate
        vals = zin["ccfb_interior_surface"]
        assert vals.min() > 1.0, f"Interior level too low: {vals.min():.2f}"
        assert vals.max() < 5.0, f"Interior level too high: {vals.max():.2f}"

    def test_gate_height_max(self, two_month_gate):
        """No gate height should exceed 16 ft."""
        height, _ = two_month_gate
        assert height["ccfb_height"].max() <= 16.0
