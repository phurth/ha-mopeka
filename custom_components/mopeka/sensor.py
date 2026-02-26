"""Sensor entities for Mopeka."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EntityCategory, UnitOfLength, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MopekaCoordinator
from .model import MopekaSensorData


@dataclass(frozen=True, kw_only=True)
class MopekaSensorDescription(SensorEntityDescription):
    value_fn: Callable[[MopekaSensorData], float | int | str | None]


SENSOR_DESCRIPTIONS: tuple[MopekaSensorDescription, ...] = (
    MopekaSensorDescription(
        key="tank_level",
        name="Tank Level",
        native_unit_of_measurement="%",
        icon="mdi:propane-tank",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: round(d.tank_level_percent, 1),
    ),
    MopekaSensorDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.temperature_c,
    ),
    MopekaSensorDescription(
        key="battery",
        name="Battery",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.battery_percent,
    ),
    MopekaSensorDescription(
        key="read_quality",
        name="Read Quality",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:signal",
        value_fn=lambda d: d.quality_raw,
    ),
    MopekaSensorDescription(
        key="quality_percent",
        name="Read Quality Percent",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:signal",
        value_fn=lambda d: d.quality_percent,
    ),
    MopekaSensorDescription(
        key="distance_raw_mm",
        name="Distance Raw",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.distance_raw_mm,
    ),
    MopekaSensorDescription(
        key="distance_compensated_mm",
        name="Distance Compensated",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.compensated_distance_mm,
    ),
    MopekaSensorDescription(
        key="accelerometer_x",
        name="Accelerometer X",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.accelerometer_x,
    ),
    MopekaSensorDescription(
        key="accelerometer_y",
        name="Accelerometer Y",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.accelerometer_y,
    ),
    MopekaSensorDescription(
        key="model_name",
        name="Model",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.model_name,
    ),
    MopekaSensorDescription(
        key="model_id",
        name="Model ID",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.model_id,
    ),
    MopekaSensorDescription(
        key="medium_type",
        name="Medium Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.medium_type.value,
    ),
    MopekaSensorDescription(
        key="tank_type",
        name="Tank Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.tank_type,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MopekaCoordinator = hass.data[DOMAIN][entry.entry_id]
    address = entry.data[CONF_ADDRESS]
    async_add_entities(MopekaSensor(coordinator, address, desc) for desc in SENSOR_DESCRIPTIONS)


class MopekaSensor(CoordinatorEntity[MopekaCoordinator], SensorEntity):
    """Mopeka sensor entity."""

    entity_description: MopekaSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MopekaCoordinator,
        address: str,
        description: MopekaSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        mac = address.replace(":", "").lower()
        self._attr_unique_id = f"{mac}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=f"Mopeka {address}",
            manufacturer="Mopeka",
            model="Mopeka Pro Series",
            connections={("bluetooth", address)},
        )

    @property
    def available(self) -> bool:
        return self.coordinator.available and self.coordinator.data is not None

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, float | int] | None:
        if self.coordinator.data is None:
            return None
        if self.entity_description.key != "tank_level":
            return None
        inches = self.coordinator.data.compensated_distance_mm / 25.4
        return {
            "distance_mm": self.coordinator.data.compensated_distance_mm,
            "distance_in": round(inches, 1),
        }
