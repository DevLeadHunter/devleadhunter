"""
Enum for the live-chat and chatbot vendors detected on a prospect's website.

Stored as plain strings, following the WebsiteStatus convention. A prospect
whose site already runs one of these widgets is "déjà équipé" for the
Réceptionniste IA pitch.
"""

from enum import Enum


class ChatWidgetProvider(str, Enum):
    """Vendor whose chat embed script was found in a website's HTML."""

    BOTPRESS = "botpress"
    BREVO = "brevo"
    CHATBASE = "chatbase"
    CHATRA = "chatra"
    CHATWOOT = "chatwoot"
    CHAPORT = "chaport"
    CRISP = "crisp"
    DRIFT = "drift"
    FRESHCHAT = "freshchat"
    GORGIAS = "gorgias"
    HUBSPOT = "hubspot"
    IADVIZE = "iadvize"
    INTERCOM = "intercom"
    IONOS = "ionos"
    JIVOCHAT = "jivochat"
    LANDBOT = "landbot"
    LIVECHAT = "livechat"
    OLARK = "olark"
    SMARTSUPP = "smartsupp"
    TAWK = "tawk"
    TIDIO = "tidio"
    TRENGO = "trengo"
    USERLIKE = "userlike"
    VOICEFLOW = "voiceflow"
    ZENDESK = "zendesk"
    ZOHO_SALESIQ = "zoho_salesiq"
