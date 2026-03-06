# Home Assistant Mopeka (HACS)

Mopeka Pro Check/Pro Plus/Pro H2O BLE tank sensor integration for Home Assistant.

This integration ports the Android BLE Plugin Bridge Mopeka implementation to native HA custom integration form.

> **Disclaimer:** This is an independent community integration and is not affiliated with, endorsed by, or supported by Mopeka or any of its affiliates. Use it at your own risk.

## Features

- Passive BLE advertisement parsing (no GATT connection)
- Tank level percentage using geometric tank formulas matching the official Mopeka app
- Temperature compensation by medium type
- Quality-based empty detection with bounce gate (see below)
- Multi-sensor support (one config entry per sensor MAC)
- Primary sensors:
  - Tank Level (%)
  - Temperature (°C)
  - Battery (%)
- Diagnostic entities:
  - Read Quality (raw 0–3)
  - Read Quality Percent
  - Data Healthy (binary sensor)
  - Raw/compensated distance (mm)
  - Model ID/Model Name
  - Accelerometer X/Y
  - Medium Type / Tank Type

## Configuration

1. Add integration: **Mopeka Tank Sensor**
2. Select a discovered BLE device from the dropdown, or enter the MAC address manually
3. **Step 1 — Core settings:**
   - **Medium type** — the fluid in the tank (`propane`, `fresh_water`, `diesel`, etc.). Determines the temperature compensation curve applied to the raw distance reading.
   - **Tank type** — the physical tank shape and size (see Tank Types below). Determines which percentage formula is used.
4. **Step 2 — Custom dimensions** (only shown when a `custom` tank type is selected):
   - Enter the usable interior height (vertical/rectangular) or interior diameter (horizontal cylinder). Displayed in inches on imperial HA instances, stored internally in mm.

No quality threshold setting is required — empty-tank detection is automatic (see below).

## Tank Types

| Key | Name | Shape |
|-----|------|-------|
| `20lb_v` | 20 lb Vertical | Vertical cylinder |
| `30lb_v` | 30 lb Vertical | Vertical cylinder |
| `40lb_v` | 40 lb Vertical | Vertical cylinder |
| `100lb_v` | 100 lb Vertical | Vertical cylinder |
| `120gal_v` | 120 gal Vertical | Vertical cylinder |
| `120gal_h` | 120 gal Horizontal | Horizontal cylinder |
| `150gal_h` | 150 gal Horizontal | Horizontal cylinder |
| `250gal_h` | 250 gal Horizontal | Horizontal cylinder |
| `500gal_h` | 500 gal Horizontal | Horizontal cylinder |
| `1000gal_h` | 1000 gal Horizontal | Horizontal cylinder |
| `europe_6kg` | 6 kg Vertical (EU) | Vertical cylinder |
| `europe_11kg` | 11 kg Vertical (EU) | Vertical cylinder |
| `europe_14kg` | 14 kg Vertical (EU) | Vertical cylinder |
| `custom` | Custom Vertical Cylinder | Vertical cylinder |
| `custom_horizontal` | Custom Horizontal Cylinder | Horizontal cylinder |
| `custom_rectangular` | Custom Rectangular | Rectangular |

## How Tank Level is Calculated

Each BLE advertisement contains a raw ultrasonic distance reading and a temperature value. The integration applies these steps:

### 1. Temperature compensation

The raw distance is adjusted using a medium-specific quadratic formula matching the official Mopeka app:

```
compensated_mm = raw_mm × (c₀ + c₁·T + c₂·T²)
```

where `T` is the raw temperature value from the advertisement and the coefficients `c₀`/`c₁`/`c₂` depend on medium type (e.g. propane, water, diesel).

### 2. Percentage formula

Three formulas are used depending on tank shape:

**Vertical cylinder** (propane bottles, upright tanks):

Mopeka's linear formula with a dead-zone offset at the bottom (38.1 mm empirical constant):

```
pct = 100 × (depth - 38.1) / (height - 38.1)
```

Readings at or below 38.1 mm are treated as 0%. `height` is the calibrated usable sensor range for each tank size (matching the official app).

**Horizontal cylinder** (fixed RV/residential tanks):

A cubic-polynomial approximation of the circular-segment fill formula, matching the official Mopeka app:

```
t = depth / diameter
pct = 100 × (-1.16533·t³ + 1.7615·t² + 0.40923·t)
```

**Rectangular** (water/grey/black water tanks):

Simple linear fill, no dead zone:

```
pct = 100 × depth / height
```

### 3. Quality-based empty detection (bounce gate)

The sensor MCU encodes a 2-bit read quality value (0–3) in each advertisement indicating echo confidence — 0 means no reliable return (empty tank or signal lost), 3 is highest confidence.

When quality drops to 0, the level is immediately clamped to **0%** regardless of what the formula returns (ultrasonic sensors can ring off the tank body and produce a false non-zero reading on empty tanks).

A **bounce gate** prevents brief quality=1 blips from prematurely restoring a false reading:

- Quality = 0 → lock engaged, level = 0%
- Quality = 1 while locked → remain locked, level = 0%
- Quality ≥ 2 while locked → lock released, normal formula result used

The `Tank Level` entity exposes a `level_status` attribute reflecting the current gate state:

| `level_status` | Meaning |
|---|---|
| `OK` | Normal operation, formula result used |
| `Empty or signal lost` | Quality=0, level clamped to 0% |
| `Recovering (signal unstable)` | Gate held, waiting for quality ≥ 2 |

## Notes

- Designed from:
  - `docs/INTERNALS.md` section `7.6. Mopeka Tank Sensor Protocol`
  - Android plugin files under `plugins/mopeka/`
- Passive integration: availability depends on receiving advertisements.
- A sensor is marked unavailable if no advertisement has been received within 30 minutes.

## Debug Logging

To enable verbose logs for troubleshooting:

```yaml
logger:
  logs:
    custom_components.ha_mopeka: debug
```

Use **Download diagnostics** from the integration page for runtime state, last parsed payload, and availability health details.
