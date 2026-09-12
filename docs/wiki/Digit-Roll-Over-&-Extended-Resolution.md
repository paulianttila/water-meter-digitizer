# Digit Roll-Over Correction & Extended Resolution

Mechanical odometer water meters rotate digits gradually as water flows. When a digit is transitioning between two numbers (e.g. roll-over from $4 \rightarrow 5$), raw computer vision models often struggle with ambiguity.

The **Water Meter Digitizer** solves this using **Predecessor Alignment Mathematics**.

---

## 🧮 1. The Roll-Over Ambiguity Problem

Consider a meter reading transitioning from `0044.9` to `0045.0`:
- The least significant digit (LSD) is at `9.8` (almost completed its rotation).
- The preceding digit (tens) is physically halfway between `4` and `5` (model might predict `4.6`).
- A naive integer rounding would prematurely read `5`, causing an erroneous reading of `0055.9` ($+10 \text{ m}^3$ spike error!).

---

## 🔍 2. Predecessor Consistency Algorithm

The digitizer resolves the higher-order digit using the state of its immediate lower-order predecessor:

1. **Predecessor $< 9.0$**: The higher-order digit has NOT yet crossed the boundary; floor the digit (e.g. `4.6` $\rightarrow$ `4`).
2. **Predecessor $\ge 9.0$**: The higher-order digit is actively transitioning but is still part of the lower decade until the predecessor crosses $0.0$.
3. **Predecessor $\ge 0.0$ and $< 1.0$**: The rollover just finished; round to the next decade (`4.6` $\rightarrow$ `5`).

---

## 🔬 3. Extended Resolution (Fractional Sub-Digits)

When `UseExtendedResolution = True` is enabled:
- The digitizer appends the fine-grained fractional decimal position from the lowest-order analog dial or digital drum wheel.
- Example: If the final analog dial needle points to `4.1`, the meter reading yields `00442.01341` instead of `00442.0134`.
- Enables ultra-sensitive leak detection down to fractions of a liter.
