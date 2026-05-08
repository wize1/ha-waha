"""Config flow for the WAHA integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ALLOWED_SENDERS,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_CONVERSATION_AGENT,
    CONF_FORWARD_TO_CONVERSATION,
    CONF_REPLY_WITH_AGENT_RESPONSE,
    CONF_SESSION,
    CONF_WEBHOOK_ID,
    DEFAULT_BASE_URL,
    DEFAULT_SESSION,
    DOMAIN,
)


class WahaConfigFlow(ConfigFlow, domain=DOMAIN):
    """User-driven config flow for WAHA."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            session = user_input[CONF_SESSION]
            await self.async_set_unique_id(f"{user_input[CONF_BASE_URL]}::{session}")
            self._abort_if_unique_id_configured()

            user_input[CONF_BASE_URL] = user_input[CONF_BASE_URL].rstrip("/")
            user_input[CONF_WEBHOOK_ID] = webhook.async_generate_id()

            webhook_url = webhook.async_generate_url(
                self.hass, user_input[CONF_WEBHOOK_ID]
            )

            return self.async_create_entry(
                title=f"WAHA ({session})",
                data=user_input,
                description=f"Configure WAHA to POST events to: {webhook_url}",
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                vol.Optional(CONF_API_KEY): str,
                vol.Required(CONF_SESSION, default=DEFAULT_SESSION): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WahaOptionsFlow()


class WahaOptionsFlow(OptionsFlow):
    """Options flow for WAHA — controls inbound message handling."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            allowed_raw = user_input.get(CONF_ALLOWED_SENDERS, "")
            user_input[CONF_ALLOWED_SENDERS] = [
                s.strip() for s in allowed_raw.split(",") if s.strip()
            ]
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        allowed_default = ", ".join(opts.get(CONF_ALLOWED_SENDERS, []) or [])

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_FORWARD_TO_CONVERSATION,
                    default=opts.get(CONF_FORWARD_TO_CONVERSATION, False),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_CONVERSATION_AGENT,
                    description={
                        "suggested_value": opts.get(CONF_CONVERSATION_AGENT, "")
                    },
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(
                    CONF_REPLY_WITH_AGENT_RESPONSE,
                    default=opts.get(CONF_REPLY_WITH_AGENT_RESPONSE, True),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_ALLOWED_SENDERS,
                    description={"suggested_value": allowed_default},
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
