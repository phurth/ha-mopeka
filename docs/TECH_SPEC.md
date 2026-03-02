# Mopeka Tank Sensor HACS Integration — Technical Specification

## 1. Purpose and Scope

`ha_mopeka` is a passive BLE advertisement integration for Mopeka tank sensors. It publishes tank level, temperature, battery, and diagnostics without creating a GATT connection.

## 2. Integration Snapshot

- **Domain:** `ha_mopeka`
- **Primary runtime component:** `MopekaCoordinator`
- **Platforms:** `sensor`, `binary_sensor`
- **Transport:** passive BLE manufacturer advertisements
- **Coordinator mode:** callback-driven updates with periodic availability refresh

## 3. Configuration and Entry Setup

- one config entry per sensor MAC
- required options:
	- `medium_type`
	- `tank_type`
	- `minimum_quality`
- options flow supports runtime tuning of quality threshold and geometry assumptions

## 4. Runtime Lifecycle

1. Entry setup creates coordinator and starts passive BLE callback registration.
2. Advertisements for the configured MAC are filtered and parsed.
3. Valid readings update coordinator data immediately.
4. Periodic coordinator refresh handles stale/offline transitions.
5. Unload path removes callback subscription.

## 5. Protocol and Transport Model

### 5.1 Advertisement parsing

- extract payload by Mopeka manufacturer id
- validate payload length and sync/model byte
- decode battery/temperature/distance/quality/accelerometer fields

Protocol constants:

- manufacturer id: `0x0059`
- minimum payload length: `10` bytes
- known model sync bytes include `0x03`, `0x04`, `0x05`, `0x08`, `0x09`, `0x0A`, `0x0B`, `0x0C`

Field extraction details:

- byte `0`: model sync id
- byte `1`: battery raw (`battery_voltage = raw / 32.0`)
- byte `2`: temperature raw (`temp_c = (raw & 0x7F) - 40`)
- bytes `3-4`: 14-bit distance + 2-bit quality (`distance_raw_mm`, `quality_raw`)
- bytes `8-9`: accelerometer X/Y

### 5.2 Computation pipeline

- apply medium-specific temperature compensation
- convert compensated depth to fill percentage using tank geometry formulas
- apply quality threshold gating before state commit

Compensation uses medium-specific polynomial coefficients `(c0, c1, c2)` and computes:

`compensated_distance = raw_distance * (c0 + c1*T + c2*T^2)`

Tank conversion uses orientation-specific geometry (`vertical` and `horizontal`) with internal dimensions derived from wall thickness and nominal tank spec.

## 6. State and Entity Model

- `MopekaSensorData` stores raw and computed values with timestamp.
- sensor entities expose level/temperature/battery and diagnostics.
- binary health entities represent freshness/availability behavior.
- no connected-session state exists by design (passive architecture).

## 7. Command and Control Surface

No active command/control writes are implemented. The integration is receive-only by design.

## 8. Reliability and Recovery

- passive design avoids connect/disconnect churn
- health recency and offline timeout windows model sensor freshness
- quality filtering prevents noisy low-confidence updates

Health windows:

- `DATA_HEALTH_TIMEOUT_SECONDS = 120`
- `OFFLINE_TIMEOUT_SECONDS = 1800`
- quality thresholds: `0`, `20`, `50`, `80`

## 9. Diagnostics and Observability

- raw vs compensated distance visibility
- quality raw/percent diagnostics
- model id/name and parse metadata
- last-seen timing behavior via coordinator-backed entities

## 10. Security and Safety Notes

- no active control channel reduces command-side risk
- local BLE advertisement processing only
- geometry/medium configuration must match real hardware for safe interpretation

## 11. Evolution Notes (Commit History)

Recent trajectory includes:

- initial scaffold from protocol parity work
- logging and diagnostics alignment
- migration to `ha_mopeka` domain naming
- HACS/CI metadata hardening

## 12. Known Constraints

- depends on advertisement cadence and RF environment quality
- quality threshold can intentionally suppress updates
- level accuracy depends on correct medium/tank configuration

## 13. Extension Guidelines

1. Keep parser signature/length validation strict.
2. Add tank presets in geometry constants before exposing UI options.
3. Version and centralize compensation coefficients.
4. Preserve distinction between user sensors and deep diagnostics.
5. Keep passive architecture unless an explicit design change is planned.
