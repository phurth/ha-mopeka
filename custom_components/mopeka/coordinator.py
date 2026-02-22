"""Passive BLE coordinator for Mopeka sensors."""

from __future__ import annotations

from datetime import timedelta
import logging
import time

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_MEDIUM_TYPE,
    CONF_MINIMUM_QUALITY,
    CONF_TANK_TYPE,
    DATA_HEALTH_TIMEOUT_SECONDS,
    DOMAIN,
    MediumType,
    OFFLINE_TIMEOUT_SECONDS,
)
from .model import MopekaSensorData
from .parser import extract_mopeka_manufacturer_payload, parse_mopeka_data

_LOGGER = logging.getLogger(__name__)


class MopekaCoordinator(DataUpdateCoordinator[MopekaSensorData | None]):
    """Coordinator that updates state from passive BLE advertisements."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Mopeka {entry.data[CONF_ADDRESS]}",
            update_interval=timedelta(seconds=60),
        )
        self.entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self.medium_type = MediumType(entry.options.get(CONF_MEDIUM_TYPE, entry.data.get(CONF_MEDIUM_TYPE, MediumType.PROPANE.value)))
        self.tank_type: str = entry.options.get(CONF_TANK_TYPE, entry.data.get(CONF_TANK_TYPE, "20lb_v"))
        self.minimum_quality: int = int(entry.options.get(CONF_MINIMUM_QUALITY, entry.data.get(CONF_MINIMUM_QUALITY, 0)))
        self._last_seen_monotonic: float | None = None
        self._unsub_ble: callable | None = None

    async def async_start(self) -> None:
        """Start BLE callback subscription."""

        @callback
        def _ble_callback(service_info: BluetoothServiceInfoBleak, change: BluetoothChange) -> None:
            self._handle_service_info(service_info)

        self._unsub_ble = bluetooth.async_register_callback(
            self.hass,
            _ble_callback,
            {"address": self.address},
            BluetoothScanningMode.PASSIVE,
        )

        last_info = bluetooth.async_last_service_info(self.hass, self.address, connectable=False)
        if last_info is not None:
            self._handle_service_info(last_info)

    async def async_stop(self) -> None:
        """Stop BLE callback subscription."""
        if self._unsub_ble is not None:
            self._unsub_ble()
            self._unsub_ble = None

    @property
    def data_healthy(self) -> bool:
        """Return true when data has been received recently."""
        if self._last_seen_monotonic is None:
            return False
        return (time.monotonic() - self._last_seen_monotonic) < DATA_HEALTH_TIMEOUT_SECONDS

    @property
    def available(self) -> bool:
        """Return true while the sensor is not stale/offline."""
        if self._last_seen_monotonic is None:
            return False
        return (time.monotonic() - self._last_seen_monotonic) < OFFLINE_TIMEOUT_SECONDS

    @property
    def last_seen_age(self) -> float | None:
        """Seconds since last advertisement."""
        if self._last_seen_monotonic is None:
            return None
        return time.monotonic() - self._last_seen_monotonic

    def _handle_service_info(self, service_info: BluetoothServiceInfoBleak) -> None:
        payload = extract_mopeka_manufacturer_payload(service_info.manufacturer_data)
        if payload is None:
            return
        parsed = parse_mopeka_data(
            address=service_info.address,
            manufacturer_data=payload,
            medium_type=self.medium_type,
            tank_type=self.tank_type,
        )
        if parsed is None:
            return
        if parsed.quality_percent < self.minimum_quality:
            return
        self._last_seen_monotonic = time.monotonic()
        self.async_set_updated_data(parsed)

    async def _async_update_data(self) -> MopekaSensorData | None:
        """Periodic refresh for stale availability and listeners."""
        return self.data
