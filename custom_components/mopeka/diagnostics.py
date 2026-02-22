"""Diagnostics for Mopeka integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MopekaCoordinator

TO_REDACT = {CONF_ADDRESS}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics data for Mopeka config entry."""
    coordinator: MopekaCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "availability": {
            "available": coordinator.available,
            "data_healthy": coordinator.data_healthy,
            "last_seen_age_seconds": coordinator.last_seen_age,
        },
        "last_data": {
            "model_id": data.model_id if data else None,
            "model_name": data.model_name if data else None,
            "battery_percent": data.battery_percent if data else None,
            "temperature_c": data.temperature_c if data else None,
            "quality_percent": data.quality_percent if data else None,
            "quality_raw": data.quality_raw if data else None,
            "distance_raw_mm": data.distance_raw_mm if data else None,
            "compensated_distance_mm": data.compensated_distance_mm if data else None,
            "tank_level_percent": data.tank_level_percent if data else None,
            "accelerometer_x": data.accelerometer_x if data else None,
            "accelerometer_y": data.accelerometer_y if data else None,
            "timestamp": data.timestamp if data else None,
        },
    }
