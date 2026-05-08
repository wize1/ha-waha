# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Home Assistant custom integration that bridges [WAHA](https://waha.devlike.pro/) (self-hosted WhatsApp HTTP API) with Home Assistant — bidirectional. Distributed via HACS.

- **Outbound:** `waha.send_message` service → WAHA `POST /api/sendText`.
- **Inbound:** WAHA webhook → HA → fires `waha_message_received` event AND optionally forwards the body to HA's conversation agent (Assist), with the agent's reply sent back to the WhatsApp sender.

## Layout

```
custom_components/waha/
  __init__.py            # config-entry setup, webhook handler, send_message service
  manifest.json
  config_flow.py         # UI config flow (user step) + options flow (inbound behavior)
  const.py
  services.yaml
  strings.json
  translations/en.json
hacs.json                # HACS metadata (root)
README.md                # user-facing docs
```

## Architecture notes

- **Single domain (`waha`), config-entry driven.** All state lives under `hass.data["waha"][entry_id]`. No YAML configuration path.
- **Webhook ID is the inbound secret.** Generated in `config_flow.async_step_user` via `webhook.async_generate_id()` and stored in `entry.data[CONF_WEBHOOK_ID]`. The webhook URL is what the user pastes into WAHA's webhook config.
- **Webhook handler filters before firing:** ignores non-`message` events, ignores `fromMe: true`, and ignores senders not in `allowed_senders` (when set). Only after filtering does it fire `waha_message_received`.
- **Conversation forwarding uses `conversation.async_converse`** with `conversation_id=f"waha:{sender}"` so each WhatsApp contact gets its own conversation thread. Reply path: `result.response.speech["plain"]["speech"]` → `_async_send_text`.
- **Service routing across multiple entries:** if the user adds multiple WAHA entries (different sessions), `waha.send_message` routes by the `session` field; without it, it picks the first loaded entry.
- **Options flow reload:** the entry registers an `add_update_listener` that calls `async_reload` whenever options change, so the webhook handler always sees fresh option values via the closed-over `entry`.

## Working in this repo

- **Code style:** target HA core conventions — `from __future__ import annotations`, type hints, `_LOGGER = logging.getLogger(__name__)`, async everywhere. Match the patterns already in `custom_components/waha/__init__.py`.
- **Minimum HA version is 2024.12** (set in `hacs.json`). The options flow uses the modern pattern (no `self.config_entry = ...` assignment — provided by the base class). Don't reintroduce the old pattern.
- **Don't add a `notify` platform** unless explicitly asked. Outbound is intentionally a service (`waha.send_message`) — simpler, gives the user full control, and avoids the legacy/NotifyEntity migration tax.
- **Strings + translations stay in sync.** When editing `strings.json`, mirror changes into `translations/en.json`. HA loads translations from the latter.
- **Webhook payload assumptions:** code assumes the WAHA payload shape `{ event, session, payload: { from, body, fromMe, ... } }`. If WAHA's webhook format changes or the user enables a different event family, update `_make_webhook_handler` accordingly.

## Working with Home Assistant tooling

The `home-assistant` MCP server is connected and pre-allowed in [.claude/settings.json](.claude/settings.json) (`mcp__home-assistant__ha_*`). Prefer MCP tools over hand-written REST/YAML when interacting with a live HA instance.

When creating or editing automations, scripts, scenes, dashboards, helpers, or Zigbee bindings on a live HA instance, **first** read the `home-assistant-best-practices` skill via `skill://home-assistant-best-practices/SKILL.md` and follow its Reference Files table. This skill is for HA *usage* (config), not for editing this Python integration's source.

## Pre-allowed permissions

[.claude/settings.json](.claude/settings.json) auto-approves: all `git` and `gh` commands, `WebFetch` to `api.iot.decast.com`, and all `mcp__home-assistant__*` tools.

## Not yet wired up

- No tests. If adding any, use `pytest-homeassistant-custom-component`.
- No CI/lint config. No `pyproject.toml`. Add only when needed.
- No git repo initialized — `git init` before first commit.
- Media messages (images, audio, voice notes) are not handled. Only `event: "message"` with `body` is processed.
- Repository: `github.com/wize1/ha-waha`. Keep `manifest.json` (`documentation`, `issue_tracker`, `codeowners`) and `README.md` aligned if it moves.
