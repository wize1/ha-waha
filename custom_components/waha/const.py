"""Constants for the WAHA integration."""
from __future__ import annotations

DOMAIN = "waha"

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_SESSION = "session"
CONF_WEBHOOK_ID = "webhook_id"

CONF_FORWARD_TO_CONVERSATION = "forward_to_conversation"
CONF_CONVERSATION_AGENT = "conversation_agent"
CONF_REPLY_WITH_AGENT_RESPONSE = "reply_with_agent_response"
CONF_ALLOWED_SENDERS = "allowed_senders"

DEFAULT_BASE_URL = "http://localhost:3000"
DEFAULT_SESSION = "default"

EVENT_MESSAGE_RECEIVED = "waha_message_received"

SERVICE_SEND_MESSAGE = "send_message"

ATTR_CHAT_ID = "chat_id"
ATTR_TEXT = "text"
ATTR_SESSION = "session"
