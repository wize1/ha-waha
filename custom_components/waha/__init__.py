"""WAHA (WhatsApp HTTP API) integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import web
from aiohttp.hdrs import METH_POST

from homeassistant.components import conversation, webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    ATTR_CHAT_ID,
    ATTR_SESSION,
    ATTR_TEXT,
    CONF_ALLOWED_SENDERS,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_CONVERSATION_AGENT,
    CONF_FORWARD_TO_CONVERSATION,
    CONF_REPLY_WITH_AGENT_RESPONSE,
    CONF_SESSION,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_MESSAGE_RECEIVED,
    SERVICE_SEND_MESSAGE,
)

_LOGGER = logging.getLogger(__name__)

SEND_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CHAT_ID): cv.string,
        vol.Required(ATTR_TEXT): cv.string,
        vol.Optional(ATTR_SESSION): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WAHA from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "base_url": entry.data[CONF_BASE_URL].rstrip("/"),
        "api_key": entry.data.get(CONF_API_KEY),
        "session": entry.data.get(CONF_SESSION),
        "client": async_get_clientsession(hass),
    }

    webhook.async_register(
        hass,
        DOMAIN,
        f"WAHA ({entry.title})",
        entry.data[CONF_WEBHOOK_ID],
        _make_webhook_handler(entry),
        allowed_methods=[METH_POST],
    )

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_MESSAGE,
            _make_send_message_handler(hass),
            schema=SEND_MESSAGE_SCHEMA,
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a WAHA config entry."""
    webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
    hass.data[DOMAIN].pop(entry.entry_id, None)

    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_SEND_MESSAGE)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry on options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _make_webhook_handler(entry: ConfigEntry):
    """Build the per-entry webhook handler."""

    async def handle(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        try:
            payload = await request.json()
        except ValueError:
            _LOGGER.warning("WAHA webhook received non-JSON body")
            return web.Response(status=400)

        if payload.get("event") != "message":
            return web.Response(status=200)

        message = payload.get("payload") or {}
        if message.get("fromMe"):
            return web.Response(status=200)

        sender = message.get("from")
        body = message.get("body")

        allowed = entry.options.get(CONF_ALLOWED_SENDERS) or []
        if allowed and sender not in allowed:
            _LOGGER.debug("WAHA: ignoring message from disallowed sender %s", sender)
            return web.Response(status=200)

        hass.bus.async_fire(
            EVENT_MESSAGE_RECEIVED,
            {
                "session": payload.get("session"),
                "from": sender,
                "body": body,
                "raw": message,
                "entry_id": entry.entry_id,
            },
        )

        if entry.options.get(CONF_FORWARD_TO_CONVERSATION) and body and sender:
            await _forward_to_conversation(hass, entry, sender, body)

        return web.Response(status=200)

    return handle


async def _forward_to_conversation(
    hass: HomeAssistant, entry: ConfigEntry, sender: str, body: str
) -> None:
    """Send the message body to the conversation agent and optionally reply."""
    agent_id = entry.options.get(CONF_CONVERSATION_AGENT) or None
    try:
        result = await conversation.async_converse(
            hass,
            text=body,
            conversation_id=f"{DOMAIN}:{sender}",
            context=None,
            language=hass.config.language,
            agent_id=agent_id,
        )
    except Exception:  # noqa: BLE001
        _LOGGER.exception("WAHA: conversation agent failed")
        return

    if not entry.options.get(CONF_REPLY_WITH_AGENT_RESPONSE, True):
        return

    speech = None
    response = getattr(result, "response", None)
    if response is not None and getattr(response, "speech", None):
        speech = response.speech.get("plain", {}).get("speech")
    if speech:
        await _async_send_text(hass, entry.entry_id, sender, speech)


def _make_send_message_handler(hass: HomeAssistant):
    """Build the waha.send_message service handler.

    Routes to the matching entry by `session` if multiple entries are configured,
    otherwise falls back to the first entry.
    """

    async def handle(call: ServiceCall) -> None:
        entries = hass.data.get(DOMAIN, {})
        if not entries:
            _LOGGER.error("WAHA: no config entry loaded")
            return

        target_session = call.data.get(ATTR_SESSION)
        entry_id: str | None = None
        if target_session:
            for eid, data in entries.items():
                if data["session"] == target_session:
                    entry_id = eid
                    break
            if entry_id is None:
                _LOGGER.error("WAHA: no entry for session %s", target_session)
                return
        else:
            entry_id = next(iter(entries))

        await _async_send_text(
            hass, entry_id, call.data[ATTR_CHAT_ID], call.data[ATTR_TEXT]
        )

    return handle


async def _async_send_text(
    hass: HomeAssistant, entry_id: str, chat_id: str, text: str
) -> None:
    """POST a text message to WAHA's /api/sendText endpoint."""
    data = hass.data[DOMAIN].get(entry_id)
    if not data:
        _LOGGER.error("WAHA: entry %s not loaded", entry_id)
        return

    url = f"{data['base_url']}/api/sendText"
    headers: dict[str, str] = {}
    if data["api_key"]:
        headers["X-Api-Key"] = data["api_key"]

    body: dict[str, Any] = {
        "session": data["session"],
        "chatId": chat_id,
        "text": text,
    }

    try:
        async with data["client"].post(url, json=body, headers=headers) as resp:
            if resp.status >= 400:
                error_text = await resp.text()
                _LOGGER.error(
                    "WAHA sendText to %s failed (HTTP %s): %s",
                    chat_id,
                    resp.status,
                    error_text,
                )
    except Exception:  # noqa: BLE001
        _LOGGER.exception("WAHA: sendText request failed")
