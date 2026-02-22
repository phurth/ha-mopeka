# Home Assistant Mopeka (HACS)

Mopeka Pro Check/Pro Plus/Pro H2O BLE tank sensor integration for Home Assistant.

This integration ports the Android BLE Plugin Bridge Mopeka implementation to native HA custom integration form.

## Features

- Passive BLE advertisement parsing (no GATT connection)
- Tank level percentage using geometric tank formulas
- Temperature compensation by medium type
- Multi-sensor support (one config entry per sensor MAC)
- Primary sensors:
  - Tank Level (%)
  - Temperature (°C)
  - Battery (%)
- Diagnostic entities:
  - Read Quality (raw 0-3 and %)
  - Data Healthy (binary sensor)
  - Raw/compensated distance
  - Model ID/Model Name
  - Accelerometer X/Y
  - Medium Type / Tank Type

## Configuration

1. Add integration: **Mopeka Tank Sensor**
2. Select discovered BLE device (or enter MAC)
3. Configure:
   - Medium type (`propane`, `fresh_water`, `diesel`, etc.)
   - Tank type (`20lb_v`, `500gal_h`, etc.)
   - Minimum quality threshold (0/20/50/80)

## Notes

- Designed from:
  - `docs/INTERNALS.md` section `7.6. Mopeka Tank Sensor Protocol`
  - Android plugin files under `plugins/mopeka/`
- Passive integration: availability depends on receiving advertisements.

## Debug Logging

To enable verbose logs for troubleshooting:

```yaml
logger:
  logs:
    custom_components.mopeka: debug
```

Use **Download diagnostics** from the integration page for runtime state, last parsed payload, and availability health details.
