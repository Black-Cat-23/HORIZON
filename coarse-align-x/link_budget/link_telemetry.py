from dataclasses import dataclass

@dataclass(frozen=True)
class LinkBudgetTelemetry:
    """Telemetry for the link‑budget observer (observer‑only)."""
    link_budget_enabled: bool
    pointing_loss_dB: float
    geometric_loss_dB: float
    atm_loss_dB: float
    received_power_W: float
    snr_linear: float
    ber: float
    link_margin_dB: float
    link_status: str

