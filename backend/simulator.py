"""What-if simulator — model impact of resource changes on pipeline forecast."""
import numpy as np


# Empirical multipliers (calibrated from industry benchmarks)
SDR_PIPELINE_PER_MONTH = 1500000   # ₹15L pipeline per SDR per month
SDR_COST_PER_MONTH = 100000        # ₹1L per SDR per month
DISCOUNT_WINRATE_LIFT = 0.02       # 2% win-rate lift per 1% discount
MEETING_WINRATE_LIFT = 0.03        # 3% win-rate lift per extra meeting per deal
CYCLE_REDUCTION_REVENUE_LIFT = 0.01  # 1% revenue lift per day reduced


def simulate(
    baseline_forecast: float,
    open_deal_count: int,
    avg_deal_size: float,
    avg_win_rate: float,
    add_sdrs: int = 0,
    increase_discount_pct: float = 0.0,
    add_meetings_per_deal: int = 0,
    shorten_cycle_days: int = 0,
    quarter_months: int = 3,
) -> dict:
    """Run a what-if scenario and return adjusted forecast + ROI."""
    adjustments = []
    total_delta = 0.0
    total_cost = 0.0

    # 1) Additional SDRs
    if add_sdrs > 0:
        sdr_pipeline = add_sdrs * SDR_PIPELINE_PER_MONTH * quarter_months
        sdr_revenue = sdr_pipeline * avg_win_rate
        sdr_cost = add_sdrs * SDR_COST_PER_MONTH * quarter_months
        total_delta += sdr_revenue
        total_cost += sdr_cost
        adjustments.append(
            f"+{add_sdrs} SDRs → ₹{sdr_pipeline/100000:.1f}L new pipeline, "
            f"₹{sdr_revenue/100000:.1f}L expected revenue (cost: ₹{sdr_cost/100000:.1f}L)"
        )

    # 2) Discount increase
    if increase_discount_pct > 0:
        winrate_lift = increase_discount_pct * DISCOUNT_WINRATE_LIFT
        discount_rev = open_deal_count * avg_deal_size * winrate_lift
        margin_loss = open_deal_count * avg_deal_size * avg_win_rate * (increase_discount_pct / 100)
        net = discount_rev - margin_loss
        total_delta += net
        adjustments.append(
            f"+{increase_discount_pct:.1f}% discount → win-rate lift {winrate_lift:.1%}, "
            f"net revenue impact ₹{net/100000:.1f}L"
        )

    # 3) More meetings per deal
    if add_meetings_per_deal > 0:
        winrate_lift = add_meetings_per_deal * MEETING_WINRATE_LIFT
        meeting_rev = open_deal_count * avg_deal_size * winrate_lift
        total_delta += meeting_rev
        adjustments.append(
            f"+{add_meetings_per_deal} meetings/deal → win-rate lift {winrate_lift:.1%}, "
            f"₹{meeting_rev/100000:.1f}L added revenue"
        )

    # 4) Shorten sales cycle
    if shorten_cycle_days > 0:
        cycle_lift = shorten_cycle_days * CYCLE_REDUCTION_REVENUE_LIFT
        cycle_rev = baseline_forecast * cycle_lift
        total_delta += cycle_rev
        adjustments.append(
            f"-{shorten_cycle_days} days cycle → {cycle_lift:.1%} throughput lift, "
            f"₹{cycle_rev/100000:.1f}L added revenue"
        )

    adjusted = baseline_forecast + total_delta
    roi = (total_delta / total_cost) if total_cost > 0 else float("inf")

    return {
        "baseline_forecast": round(baseline_forecast, 0),
        "adjusted_forecast": round(adjusted, 0),
        "delta": round(total_delta, 0),
        "delta_pct": round((total_delta / baseline_forecast) * 100 if baseline_forecast else 0, 1),
        "cost_estimate": round(total_cost, 0),
        "roi": round(roi, 1),
        "details": adjustments,
    }
