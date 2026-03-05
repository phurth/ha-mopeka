"""Config flow for Mopeka BLE integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ADDRESS

from .const import (
    CONF_CUSTOM_TANK_HEIGHT_MM,
    CONF_MEDIUM_TYPE,
    CONF_MINIMUM_QUALITY,
    CONF_TANK_TYPE,
    CUSTOM_TANK_KEYS,
    DOMAIN,
    MANUFACTURER_ID,
    MediumType,
    QUALITY_THRESHOLDS,
    TANK_SPECS,
)

# Human-readable labels for the tank type dropdown, keyed by TANK_SPECS id.
_TANK_TYPE_LABELS: dict[str, str] = {k: v.name for k, v in TANK_SPECS.items()}

# Default custom height (mm) shown as placeholder when a custom type is chosen.
_DEFAULT_CUSTOM_HEIGHT_MM = 300
_MM_PER_INCH = 25.4


def _display_in_inches(hass) -> bool:
    """Return True if the HA unit system is imperial (US customary)."""
    return not hass.config.units.is_metric


def _core_schema(defaults: dict[str, Any], address_field: vol.Marker | None = None) -> vol.Schema:
    """Build the main configuration schema (Step 1)."""
    fields: dict[vol.Marker, Any] = {}
    if address_field is not None:
        fields[address_field] = str
    fields[vol.Required(CONF_MEDIUM_TYPE, default=defaults.get(CONF_MEDIUM_TYPE, MediumType.PROPANE.value))] = vol.In(
        [item.value for item in MediumType]
    )
    fields[vol.Required(CONF_TANK_TYPE, default=defaults.get(CONF_TANK_TYPE, "20lb_v"))] = vol.In(
        _TANK_TYPE_LABELS
    )
    fields[vol.Required(CONF_MINIMUM_QUALITY, default=int(defaults.get(CONF_MINIMUM_QUALITY, 0)))] = vol.In(
        list(QUALITY_THRESHOLDS)
    )
    return vol.Schema(fields)


def _custom_dimensions_schema(defaults: dict[str, Any], use_inches: bool) -> vol.Schema:
    """Schema for Step 2: custom tank height entry.

    Stores value in mm internally; presents in inches for imperial users.
    """
    stored_mm = float(defaults.get(CONF_CUSTOM_TANK_HEIGHT_MM, _DEFAULT_CUSTOM_HEIGHT_MM))
    if use_inches:
        display_default = round(stored_mm / _MM_PER_INCH)
        validator = vol.All(vol.Coerce(int), vol.Range(min=1, max=394))
    else:
        display_default = round(stored_mm)
        validator = vol.All(vol.Coerce(int), vol.Range(min=1, max=10000))
    return vol.Schema(
        {
            vol.Required(CONF_CUSTOM_TANK_HEIGHT_MM, default=display_default): validator,
        }
    )


class MopekaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Mopeka."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._pending_data: dict[str, Any] = {}

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        """Handle BLE discovery."""
        if MANUFACTURER_ID not in discovery_info.manufacturer_data:
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name or discovery_info.address}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm BLE discovery and collect options (Step 1)."""
        if self._discovery_info is None:
            return self.async_abort(reason="no_device")

        if user_input is not None:
            self._pending_data = {
                CONF_ADDRESS: self._discovery_info.address,
                **user_input,
            }
            if user_input[CONF_TANK_TYPE] in CUSTOM_TANK_KEYS:
                return await self.async_step_custom_dimensions()
            return self.async_create_entry(
                title=f"Mopeka {self._discovery_info.address}",
                data=self._pending_data,
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=_core_schema({}),
        )

    async def async_step_custom_dimensions(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 2: collect custom tank height (only for custom tank types)."""
        use_inches = _display_in_inches(self.hass)
        if user_input is not None:
            raw = user_input[CONF_CUSTOM_TANK_HEIGHT_MM]
            mm_value = round(raw * _MM_PER_INCH) if use_inches else raw
            self._pending_data[CONF_CUSTOM_TANK_HEIGHT_MM] = mm_value
            title = f"Mopeka {self._pending_data.get(CONF_ADDRESS, 'sensor')}"
            return self.async_create_entry(title=title, data=self._pending_data)

        tank_type = self._pending_data.get(CONF_TANK_TYPE, "custom")
        return self.async_show_form(
            step_id="custom_dimensions",
            data_schema=_custom_dimensions_schema(self._pending_data, use_inches),
            description_placeholders={
                "tank_type": TANK_SPECS[tank_type].name,
                "unit": "inches" if use_inches else "mm",
            },
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manual setup flow (Step 1)."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            self._pending_data = dict(user_input)
            if user_input[CONF_TANK_TYPE] in CUSTOM_TANK_KEYS:
                return await self.async_step_custom_dimensions()
            return self.async_create_entry(title=f"Mopeka {address}", data=self._pending_data)

        discovered: dict[str, str] = {}
        for info in async_discovered_service_info(self.hass):
            if MANUFACTURER_ID in info.manufacturer_data:
                discovered[info.address] = f"{info.name or 'Mopeka'} ({info.address})"

        address_field: vol.Marker = (
            vol.Required(CONF_ADDRESS, default=next(iter(discovered)))
            if discovered
            else vol.Required(CONF_ADDRESS)
        )
        address_validator = vol.In(discovered) if discovered else str

        schema = _core_schema({}, address_field=address_field)
        # Replace the address field validator with the appropriate one
        schema = vol.Schema({**{k: (address_validator if k == address_field else v) for k, v in schema.schema.items()}})

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry):
        return MopekaOptionsFlow(config_entry)


class MopekaOptionsFlow(OptionsFlow):
    """Options flow for Mopeka."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry
        self._pending_options: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 1: core options."""
        if user_input is not None:
            self._pending_options = dict(user_input)
            if user_input[CONF_TANK_TYPE] in CUSTOM_TANK_KEYS:
                return await self.async_step_custom_dimensions()
            return self.async_create_entry(title="", data=self._pending_options)

        defaults = {
            CONF_MEDIUM_TYPE: self.config_entry.options.get(
                CONF_MEDIUM_TYPE, self.config_entry.data.get(CONF_MEDIUM_TYPE, MediumType.PROPANE.value)
            ),
            CONF_TANK_TYPE: self.config_entry.options.get(
                CONF_TANK_TYPE, self.config_entry.data.get(CONF_TANK_TYPE, "20lb_v")
            ),
            CONF_MINIMUM_QUALITY: self.config_entry.options.get(
                CONF_MINIMUM_QUALITY, self.config_entry.data.get(CONF_MINIMUM_QUALITY, 0)
            ),
        }
        return self.async_show_form(step_id="init", data_schema=_core_schema(defaults))

    async def async_step_custom_dimensions(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 2: custom tank height."""
        use_inches = _display_in_inches(self.hass)
        if user_input is not None:
            raw = user_input[CONF_CUSTOM_TANK_HEIGHT_MM]
            mm_value = round(raw * _MM_PER_INCH) if use_inches else raw
            self._pending_options[CONF_CUSTOM_TANK_HEIGHT_MM] = mm_value
            return self.async_create_entry(title="", data=self._pending_options)

        existing_height = self.config_entry.options.get(
            CONF_CUSTOM_TANK_HEIGHT_MM,
            self.config_entry.data.get(CONF_CUSTOM_TANK_HEIGHT_MM, _DEFAULT_CUSTOM_HEIGHT_MM),
        )
        tank_type = self._pending_options.get(CONF_TANK_TYPE, "custom")
        return self.async_show_form(
            step_id="custom_dimensions",
            data_schema=_custom_dimensions_schema({CONF_CUSTOM_TANK_HEIGHT_MM: existing_height}, use_inches),
            description_placeholders={
                "tank_type": TANK_SPECS[tank_type].name,
                "unit": "inches" if use_inches else "mm",
            },
        )
