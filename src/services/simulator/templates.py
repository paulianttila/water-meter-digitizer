"""Meter templates and structural configurations for the Mock Camera Simulator.

Defines physical meter archetypes (digits, multi-line flow rate, presence of dials,
decimal drum schemes) while remaining independent of optical perturbations, themes,
and styling parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

STANDARD_DIAL_CONFIGS: list[tuple[int, int, str]] = [
    (430, 300, "x0.1"),
    (360, 365, "x0.01"),
    (280, 365, "x0.001"),
    (210, 300, "x0.0001"),
]


@dataclass(frozen=True)
class MeterTemplate:
    """Structural template defining reading elements on a simulated meter faceplate."""

    id: str
    label: str
    description: str
    counter_type: Literal["drum", "lcd"]
    icon: str = "water_drop"

    # Counter wheel / digit configuration
    digit_count: int = 5  # Total volume digits displayed on the main readout
    drum_decimals: int = 0  # Number of red decimal wheels on drum counters
    has_decimal_dot: bool = False  # Explicit decimal separator dot on digit counter

    # Dial configuration
    has_dials: bool = True
    dial_configs: list[tuple[int, int, str]] = field(
        default_factory=lambda: list(STANDARD_DIAL_CONFIGS)
    )

    # Secondary flow rate display (e.g. m³/h on ultrasonic smart meters)
    has_flow_display: bool = False
    flow_int_digits: int = 2
    flow_dec_digits: int = 3

    # Faceplate aesthetics
    has_flow_indicator: bool = False  # Central rotating star/cog when dials are omitted
    unit: str = "m³"
    flow_unit: str = "m³/h"


# -----------------------------------------------------------------------------
# Template Registry
# -----------------------------------------------------------------------------

METER_TEMPLATES: dict[str, MeterTemplate] = {
    "mechanical_dials": MeterTemplate(
        id="mechanical_dials",
        label="Mechanical Multi-Jet (5 Drums + 4 Dials)",
        description="Standard European multi-jet meter with 5 black integer drums (m³) and 4 rotating needle dials (x0.1 to x0.0001).",
        counter_type="drum",
        icon="tune",
        digit_count=5,
        drum_decimals=0,  # All 5 drums are black integers (m³)
        has_decimal_dot=False,
        has_dials=True,
        has_flow_indicator=False,
    ),
    "mechanical_roller": MeterTemplate(
        id="mechanical_roller",
        label="Mechanical Roller-Only (4 Black + 1 Red)",
        description="Compact single-jet dry meter with 4 black drums (m³) and 1 red drum (x0.1) with decimal dot, no needle dials.",
        counter_type="drum",
        icon="counter_5",
        digit_count=5,
        drum_decimals=1,  # Lowest wheel is red decimal
        has_decimal_dot=True,
        has_dials=False,
        has_flow_indicator=True,  # Central rotating flow indicator spinner
    ),
    "digital_single": MeterTemplate(
        id="digital_single",
        label="Electronic Smart Meter (Single-line LCD)",
        description="Smart water meter with 5 7/14-segment LCD digits for cumulative volume (m³), no needle dials.",
        counter_type="lcd",
        icon="speed",
        digit_count=5,
        drum_decimals=0,
        has_decimal_dot=False,
        has_dials=False,
        has_flow_indicator=False,
    ),
    "digital_flow": MeterTemplate(
        id="digital_flow",
        label="Smart Ultrasonic Meter (Dual-line LCD + Flow)",
        description="Ultrasonic smart meter (Axioma W1 style) with cumulative volume (m³) and separate instantaneous flow rate (m³/h).",
        counter_type="lcd",
        icon="waves",
        digit_count=9,  # 6 integer + 3 decimal
        drum_decimals=0,
        has_decimal_dot=True,
        has_dials=False,
        has_flow_display=True,
        flow_int_digits=2,
        flow_dec_digits=3,
        has_flow_indicator=False,
    ),
}

METER_TEMPLATE_OPTIONS: dict[str, str] = {
    t_id: t.label for t_id, t in METER_TEMPLATES.items()
}


def get_meter_template(template_id: str | None) -> MeterTemplate:
    """Retrieve MeterTemplate by identifier with fallback to mechanical_dials."""
    if not template_id:
        return METER_TEMPLATES["mechanical_dials"]
    key = template_id.lower().strip()
    if key in METER_TEMPLATES:
        return METER_TEMPLATES[key]
    if key == "drum":
        return METER_TEMPLATES["mechanical_dials"]
    if key == "lcd":
        return METER_TEMPLATES["digital_single"]
    return METER_TEMPLATES["mechanical_dials"]


def list_meter_templates() -> list[MeterTemplate]:
    """Return list of available MeterTemplate instances."""
    return list(METER_TEMPLATES.values())
