"""Binary sensor entities for Mopeka."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MopekaCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MopekaCoordinator = hass.data[DOMAIN][entry.entry_id]
    address = entry.data[CONF_ADDRESS]
    async_add_entities([MopekaDataHealthyBinarySensor(coordinator, address)])


class MopekaDataHealthyBinarySensor(CoordinatorEntity[MopekaCoordinator], BinarySensorEntity):
    """Diagnostic health binary sensor."""

    _attr_has_entity_name = True
    _attr_name = "Data Healthy"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MopekaCoordinator, address: str) -> None:
        super().__init__(coordinator)
        mac = address.replace(":", "").lower()
        self._attr_unique_id = f"{mac}_data_healthy"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=f"Mopeka {address}",
            manufacturer="Mopeka",
            model="Mopeka Pro Series",
            connections={("bluetooth", address)},
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data_healthy

    @property
    def available(self) -> bool:
        return self.coordinator.available
