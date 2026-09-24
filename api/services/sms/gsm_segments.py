"""Count SMS segments, GSM-7 vs Unicode aware.

A French accent (é, è, à…) that is NOT in the GSM-7 alphabet forces the whole
message into UCS-2, dropping the per-segment budget from 160/153 to 70/67
characters — so a short-looking SMS can silently cost two segments. We count so
the compose UI can warn and the message stays sober (one segment when possible).
"""

from __future__ import annotations

# GSM 03.38 basic character set (the chars that stay single-byte).
_GSM7_BASIC: frozenset[str] = frozenset(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ ÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
# GSM-7 chars that take TWO septets (the extension table).
_GSM7_EXTENDED: frozenset[str] = frozenset("^{}\\[~]|€")

_GSM_SINGLE: int = 160
_GSM_MULTI: int = 153
_UCS2_SINGLE: int = 70
_UCS2_MULTI: int = 67

# Closest GSM-7 equivalent for the common characters that would otherwise force UCS-2.
# The GSM-7 accents (é è à ù ì ò ä ö ñ ü…) are deliberately absent — they are kept as-is.
# Note: lowercase « ç » is NOT in GSM-7 (only « Ç » is), so it is simplified to « c ».
_TRANSLITERATIONS: dict[str, str] = {
    "â": "a", "ê": "e", "î": "i", "ô": "o", "û": "u",
    "Â": "A", "Ê": "E", "Î": "I", "Ô": "O", "Û": "U",
    "ë": "e", "ï": "i", "Ë": "E", "Ï": "I", "ÿ": "y", "Ÿ": "Y",
    "ç": "c", "á": "a", "í": "i", "ó": "o", "ú": "u", "ã": "a", "õ": "o",
    "Á": "A", "Í": "I", "Ó": "O", "Ú": "U", "Ã": "A", "Õ": "O",
    "œ": "oe", "Œ": "OE",
    "’": "'", "‘": "'", "“": '"', "”": '"', "«": '"', "»": '"',
    "–": "-", "—": "-", "…": "...", "•": "-",
    "\u00a0": " ", "\u202f": " ",
}  # fmt: skip


def to_gsm7(text: str) -> str:
    """Simplify the non-GSM-7 characters of *text* to their closest GSM-7 equivalent.

    Keeps every accent that is already GSM-7 (é, è, à, ù…): only the characters that would
    force the whole message into UCS-2 — circumflex letters (â, ê…), the lowercase cedilla
    (ç, absent from GSM-7) and typographic punctuation (curly quotes, long dashes, ellipsis)
    — are replaced, so a normal French message stays one segment. Anything else is untouched.

    Args:
        text: The raw message body.

    Returns:
        The body with non-GSM-7 characters transliterated.
    """
    if not text:
        return text
    return "".join(_TRANSLITERATIONS.get(ch, ch) for ch in text)


def to_strict_gsm7(text: str) -> str:
    """Transliterate *text* to GSM-7 and drop what has no equivalent (emoji, °, ™…), collapsing whitespace.

    A single such character would send the whole message as UCS-2 (70 characters a segment).

    Args:
        text: The message body.

    Returns:
        The body, every character GSM-7 encodable.
    """
    simplified = to_gsm7(" ".join(text.split()))
    return "".join(char for char in simplified if is_gsm7(char))


def is_gsm7(text: str) -> bool:
    """Whether *text* fits the GSM-7 alphabet (else it is sent as UCS-2).

    Args:
        text: The message body.

    Returns:
        ``True`` when every character is GSM-7 encodable.
    """
    return all(ch in _GSM7_BASIC or ch in _GSM7_EXTENDED for ch in text)


def segment_count(text: str) -> int:
    """Number of SMS segments *text* costs (each segment is billed).

    Args:
        text: The message body.

    Returns:
        The segment count (``0`` for an empty body).
    """
    if not text:
        return 0
    if is_gsm7(text):
        length = sum(2 if ch in _GSM7_EXTENDED else 1 for ch in text)
        single, multi = _GSM_SINGLE, _GSM_MULTI
    else:
        length = len(text)
        single, multi = _UCS2_SINGLE, _UCS2_MULTI
    if length <= single:
        return 1
    return -(-length // multi)  # ceil division
