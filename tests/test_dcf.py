"""Golden-value tests for the two-stage DCF model."""

import pytest

from mulberry.core.dcf import DCFValuator


@pytest.fixture
def dcf():
    return DCFValuator()


# --- Deterministic helpers -------------------------------------------------

def test_normalized_base_fcf_averages_three_years(dcf):
    assert dcf._normalized_base_fcf([100, 90, 80, 70]) == pytest.approx(90.0)


def test_normalized_base_fcf_ignores_zeros(dcf):
    assert dcf._normalized_base_fcf([100, 0, 80]) == pytest.approx(90.0)
    assert dcf._normalized_base_fcf([0, 0, 0]) == 0.0


def test_capped_growth_clamps_high(dcf):
    # (200/100)^(1/1) - 1 = 1.0, clamped to MAX_STAGE1_GROWTH = 0.15
    assert dcf._capped_growth([200, 100]) == pytest.approx(0.15)


def test_capped_growth_clamps_low(dcf):
    # flat FCF -> 0 growth, clamped at MIN_STAGE1_GROWTH = 0.0
    assert dcf._capped_growth([100, 100]) == pytest.approx(0.0)


def test_capped_growth_thin_history_default(dcf):
    assert dcf._capped_growth([100]) == pytest.approx(0.03)


def test_enterprise_value_growth_equals_discount(dcf):
    # When stage-1 growth == discount rate, each discounted year == base FCF,
    # so PV(stage1) = base * years = 500; plus discounted Gordon terminal value.
    ev = dcf._enterprise_value(base_fcf=100, stage1_growth=0.10,
                               discount_rate=0.10, terminal_growth=0.025)
    assert ev == pytest.approx(1866.66, rel=1e-3)


def test_enterprise_value_zero_when_rate_below_terminal(dcf):
    assert dcf._enterprise_value(100, 0.05, 0.02, 0.03) == 0.0


# --- Full valuation --------------------------------------------------------

def test_valuate_flat_fcf(dcf):
    result = dcf.valuate(
        fcf_history=[100, 100, 100],
        shares_outstanding=100,
        current_price=10.0,
    )
    assert result.stage1_growth == pytest.approx(0.0)
    assert result.intrinsic_value_per_share == pytest.approx(12.28, abs=0.02)
    assert result.margin_of_safety == pytest.approx(0.185, abs=0.005)
    # 3x3 sensitivity grid
    assert len(result.sensitivity) == 3
    assert len(result.sensitivity[0]["values"]) == 3


def test_valuate_not_computable_without_positive_fcf(dcf):
    result = dcf.valuate(
        fcf_history=[-10, -5, -8],
        shares_outstanding=100,
        current_price=10.0,
    )
    assert result.intrinsic_value_per_share == 0.0
    assert result.margin_of_safety == -1.0


def test_net_cash_adjustment_raises_value(dcf):
    with_cash = dcf.valuate([100, 100, 100], 100, 10.0, cash=500, total_debt=0)
    with_debt = dcf.valuate([100, 100, 100], 100, 10.0, cash=0, total_debt=500)
    assert with_cash.intrinsic_value_per_share > with_debt.intrinsic_value_per_share
    # $1000 net-cash swing over 100 shares = $10/share difference
    assert (with_cash.intrinsic_value_per_share
            - with_debt.intrinsic_value_per_share) == pytest.approx(10.0, abs=1e-6)
