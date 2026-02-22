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
    CONF_MEDIUM_TYPE,
    CONF_MINIMUM_QUALITY,
    CONF_TANK_TYPE,
    DOMAIN,
    MANUFACTURER_ID,
    MediumType,
    QUALITY_THRESHOLDS,
    TANK_SPECS,
)


def _options_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_MEDIUM_TYPE,
                default=defaults.get(CONF_MEDIUM_TYPE, MediumType.PROPANE.value),
            ): vol.In([item.value for item in MediumType]),
            vol.Required(
                CONF_TANK_TYPE,
                default=defaults.get(CONF_TANK_TYPE, "20lb_v"),
            ): vol.In(list(TANK_SPECS.keys())),
            vol.Required(
                CONF_MINIMUM_QUALITY,
                default=int(defaults.get(CONF_MINIMUM_QUALITY, 0)),
            ): vol.In(list(QUALITY_THRESHOLDS)),
        }
    )


class MopekaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Mopeka."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None

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
        """Confirm BLE discovery and collect options."""
        if self._discovery_info is None:
            return self.async_abort(reason="no_device")

        if user_input is not None:
            return self.async_create_entry(
                title=f"Mopeka {self._discovery_info.address}",
                data={
                    CONF_ADDRESS: self._discovery_info.address,
                    CONF_MEDIUM_TYPE: user_input[CONF_MEDIUM_TYPE],
                    CONF_TANK_TYPE: user_input[CONF_TANK_TYPE],
                    CONF_MINIMUM_QUALITY: user_input[CONF_MINIMUM_QUALITY],
                },
            )

        return self.async_show_form(step_id="confirm", data_schema=_options_schema())

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manual setup flow."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Mopeka {address}",
                data=user_input,
            )

        discovered: dict[str, str] = {}
        for info in async_discovered_service_info(self.hass):
            if MANUFACTURER_ID in info.manufacturer_data:
                discovered[info.address] = f"{info.name or 'Mopeka'} ({info.address})"

        if discovered:
            schema = vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(discovered),
                    vol.Required(CONF_MEDIUM_TYPE, default=MediumType.PROPANE.value): vol.In([item.value for item in MediumType]),
                    vol.Required(CONF_TANK_TYPE, default="20lb_v"): vol.In(list(TANK_SPECS.keys())),
                    vol.Required(CONF_MINIMUM_QUALITY, default=0): vol.In(list(QUALITY_THRESHOLDS)),
                }
            )
        else:
            schema = vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Required(CONF_MEDIUM_TYPE, default=MediumType.PROPANE.value): vol.In([item.value for item in MediumType]),
                    vol.Required(CONF_TANK_TYPE, default="20lb_v"): vol.In(list(TANK_SPECS.keys())),
                    vol.Required(CONF_MINIMUM_QUALITY, default=0): vol.In(list(QUALITY_THRESHOLDS)),
                }
            )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry):
        return MopekaOptionsFlow(config_entry)


class MopekaOptionsFlow(OptionsFlow):
    """Options flow for Mopeka."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {
            CONF_MEDIUM_TYPE: self.config_entry.options.get(CONF_MEDIUM_TYPE, self.config_entry.data.get(CONF_MEDIUM_TYPE, MediumType.PROPANE.value)),
            CONF_TANK_TYPE: self.config_entry.options.get(CONF_TANK_TYPE, self.config_entry.data.get(CONF_TANK_TYPE, "20lb_v")),
            CONF_MINIMUM_QUALITY: self.config_entry.options.get(CONF_MINIMUM_QUALITY, self.config_entry.data.get(CONF_MINIMUM_QUALITY, 0)),
        }
        return self.async_show_form(step_id="init", data_schema=_options_schema(defaults))
