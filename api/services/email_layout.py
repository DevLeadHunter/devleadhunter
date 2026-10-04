"""Dressing of a prospecting email: the card of the sender, and the offer laid out as a table."""

from __future__ import annotations

import re

from enums.email_template_layout import EmailTemplateLayout
from services.email_variables import EmailVariables
from services.unsubscribe_service import UnsubscribeService


class EmailLayout:
    """
    Dresses a rendered email body and its signature for the layout its template chose.

    The body arrives rendered: variables substituted, a follow-up possibly rewritten by the
    behaviour personalisation. Nothing here reads the template, so the offer is recognised by the
    values of the send: the links of the demo, the price, the withdrawal date. Whatever the body
    does not let recognise stays plain text in the card, in the order it was written.
    """

    DEFAULT_ACCENT_COLOR: str = "#141414"

    _PAGE_COLOR: str = "#f6f6f3"
    _CARD_COLOR: str = "#ffffff"
    _TEXT_COLOR: str = "#4b4b47"
    _INK_COLOR: str = "#141414"
    _MUTED_COLOR: str = "#66665f"
    _RULE_COLOR: str = "#ebebe7"
    _FONT_STACK: str = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"
    _CARD_COLUMN_WIDTH: int = 520
    _OFFER_TABLE_TITLE: str = "L'essentiel"
    _PRICE_LABEL: str = "Prix"
    _DATE_LABEL: str = "Date"
    _ANSWER_LABEL: str = "Réponse"
    _MINIMUM_TABLE_ROWS: int = 2

    _HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")
    _TOP_LEVEL_BLOCK = re.compile(r"<(p|ul|ol)\b[^>]*>.*?</\1\s*>", re.DOTALL | re.IGNORECASE)
    _PARAGRAPH = re.compile(r"<p\b[^>]*>(.*)</p\s*>", re.DOTALL | re.IGNORECASE)
    _HREF = re.compile(r'href="([^"]+)"')
    _FIRST_SENTENCE = re.compile(r"(.+?[.?!])\s+(\S.*)", re.DOTALL)
    _CLIPBOARD_MARKER = re.compile(r"<!--(?:Start|End)Fragment-->")
    _TRAILING_BREAKS = re.compile(r"(?:\s|<br\s*/?>)+(</div>)\s*$", re.IGNORECASE)
    _PHONE_STYLE: str = (
        "<style>@media only screen and (max-width:480px){"
        ".em-outer{padding:0 !important;}"
        ".em-top{height:0 !important;}"
        ".em-card{padding:28px 20px !important;border-radius:0 !important;}"
        ".em-label{width:96px !important;}"
        ".em-foot{padding:24px 20px 40px !important;}"
        "}</style>"
    )

    @classmethod
    def dress(
        cls,
        layout: str | None,
        body_html: str,
        signature_html: str,
        variables: dict[str, str],
        accent_color: str | None = None,
    ) -> str:
        """
        Present a rendered body and its signature in the layout of the template.

        Args:
            layout: The template's ``EmailTemplateLayout`` value; anything unknown reads as plain.
            body_html: The rendered body, variables already substituted.
            signature_html: The signature block to append ("" without a signature).
            variables: The substitution map of the send, read for its links, prices and date.
            accent_color: The sender's ``#RRGGBB`` colour for links and the button; ink when missing or malformed.

        Returns:
            The body followed by the signature for a plain template, a full HTML document otherwise,
            holding the slot the unsubscribe footer is written in.
        """
        if layout not in (EmailTemplateLayout.CARD.value, EmailTemplateLayout.CARD_TABLE.value):
            return body_html + signature_html
        accent: str = (
            accent_color if accent_color and cls._HEX_COLOR.fullmatch(accent_color) else cls.DEFAULT_ACCENT_COLOR
        )
        blocks: list[str] | None = cls._split_top_level_blocks(body_html)
        if blocks is None:
            content: str = cls._emphasise_offer_values(body_html, variables)
        else:
            content = cls._build_content(
                blocks, variables, accent, with_table=layout == EmailTemplateLayout.CARD_TABLE.value
            )
        return cls._build_document(cls._apply_card_colours(content, accent), cls._tidy_signature(signature_html))

    @classmethod
    def _split_top_level_blocks(cls, body_html: str) -> list[str] | None:
        """The paragraphs and lists of a body, or None when it holds anything else (it is then left as written)."""
        if cls._TOP_LEVEL_BLOCK.sub("", body_html).strip():
            return None
        return [match.group(0) for match in cls._TOP_LEVEL_BLOCK.finditer(body_html)]

    @classmethod
    def _build_content(cls, blocks: list[str], variables: dict[str, str], accent: str, *, with_table: bool) -> str:
        """Lay the blocks out: text down to the last link, a button under each link, then the offer."""
        button_labels: dict[str, str] = cls._collect_button_labels(variables)
        demo_hrefs: list[str | None] = [cls._find_demo_href(block, button_labels) for block in blocks]
        last_demo_link_index: int = max(
            (index for index, href in enumerate(demo_hrefs) if href is not None), default=-1
        )
        rows, remaining = (
            cls._split_offer_rows(blocks[last_demo_link_index + 1 :], variables)
            if with_table and last_demo_link_index >= 0
            else ([], blocks[last_demo_link_index + 1 :])
        )
        parts: list[str] = []
        buttoned: set[str] = set()
        for block, href in zip(blocks[: last_demo_link_index + 1], demo_hrefs, strict=False):
            parts.append(cls._emphasise_offer_values(cls._space_bare_tags(block), variables))
            label: str = button_labels.get(href, "") if href else ""
            if href and label and "<img" not in block and href not in buttoned:
                parts.append(cls._build_button(href, label, accent))
                buttoned.add(href)
        if rows:
            parts.append(cls._build_offer_table(rows))
        parts.extend(cls._emphasise_offer_values(cls._space_bare_tags(block), variables) for block in remaining)
        return "".join(parts)

    @classmethod
    def _collect_button_labels(cls, variables: dict[str, str]) -> dict[str, str]:
        """Each demo address of the send and the wording of its button; a video has none, its thumbnail is the link."""
        receptionist_first_name: str = variables.get(EmailVariables.RECEPTIONIST_FIRST_NAME, "")
        wordings: dict[str, str] = {
            EmailVariables.DEMO_LINK: "Voir mon site",
            EmailVariables.ASSISTANT_LINK: f"Parler à {receptionist_first_name}"
            if receptionist_first_name
            else "Voir la démo",
            EmailVariables.CARD_LINK: "Voir ma carte",
            EmailVariables.VIDEO_THUMBNAIL: "",
            EmailVariables.ASSISTANT_VIDEO_THUMBNAIL: "",
        }
        labels: dict[str, str] = {}
        for key, wording in wordings.items():
            for href in cls._HREF.findall(variables.get(key, "")):
                labels.setdefault(href, wording)
        return labels

    @staticmethod
    def _find_demo_href(block: str, button_labels: dict[str, str]) -> str | None:
        """The demo address a block links to, or None when it links to none."""
        return next((href for href in button_labels if f'href="{href}"' in block), None)

    @classmethod
    def _split_offer_rows(cls, blocks: list[str], variables: dict[str, str]) -> tuple[list[tuple[str, str]], list[str]]:
        """
        Split the blocks that follow the last link into the rows of the offer table and the text left under it.

        The rows are the leading paragraphs that state the price or the date; the paragraph right
        after them becomes the answer row when it closes the email. Nothing is reordered, and under
        two rows there is no table at all.

        Returns:
            The (label, paragraph text) rows and the blocks kept as text; no row when the table would be too thin.
        """
        prices: list[str] = [
            variables.get(key, "")
            for key in (EmailVariables.PRICE, EmailVariables.PRICE_ASSISTANT, EmailVariables.CARD_PRICE)
        ]
        expiry_date: str = variables.get(EmailVariables.EXPIRY_DATE, "")
        rows: list[tuple[str, str]] = []
        for block in blocks:
            paragraph = cls._PARAGRAPH.fullmatch(block)
            if paragraph is None:
                break
            text: str = paragraph.group(1)
            if any(cls._mentions(text, price) for price in prices):
                rows.append((cls._PRICE_LABEL, text))
            elif cls._mentions(text, expiry_date):
                rows.append((cls._DATE_LABEL, text))
            else:
                break
        remaining: list[str] = blocks[len(rows) :]
        closing = cls._PARAGRAPH.fullmatch(remaining[0]) if len(remaining) == 1 else None
        if rows and closing is not None:
            rows.append((cls._ANSWER_LABEL, closing.group(1)))
            remaining = []
        if len(rows) < cls._MINIMUM_TABLE_ROWS:
            return [], blocks
        return rows, remaining

    @staticmethod
    def _mentions(text: str, value: str) -> bool:
        """Whether a text states a value of the send, a longer number containing it left aside (« 12 novembre » for « 2 novembre »)."""
        return bool(value) and re.search(rf"(?<!\d){re.escape(value)}(?!\d)", text) is not None

    @classmethod
    def _emphasise_offer_values(cls, html: str, variables: dict[str, str]) -> str:
        """The price and the withdrawal date in ink, so a skimming reader still meets both."""
        keys: tuple[str, ...] = (
            EmailVariables.PRICE,
            EmailVariables.PRICE_ASSISTANT,
            EmailVariables.CARD_PRICE,
            EmailVariables.EXPIRY_DATE,
        )
        for value in dict.fromkeys(variables.get(key, "") for key in keys):
            if value:
                html = re.sub(
                    rf"(?<!\d){re.escape(value)}(?!\d)",
                    f'<strong style="font-weight:600;color:{cls._INK_COLOR};">{value}</strong>',
                    html,
                )
        return html

    @staticmethod
    def _space_bare_tags(block: str) -> str:
        """Give the bare tags of a block the spacing mail clients would otherwise decide for themselves."""
        return (
            block.replace("<p>", '<p style="margin:0 0 16px;">')
            .replace("<ul>", '<ul style="margin:0 0 16px;padding:0 0 0 22px;">')
            .replace("<ol>", '<ol style="margin:0 0 16px;padding:0 0 0 22px;">')
            .replace("<li>", '<li style="margin:0 0 6px;">')
        )

    @classmethod
    def _build_button(cls, href: str, label: str, accent: str) -> str:
        return (
            f'<p style="margin:0 0 16px;"><a href="{href}" target="_blank" rel="noopener noreferrer" '
            f'style="display:inline-block;padding:12px 22px;background-color:{accent};border-radius:8px;'
            f'font-size:15px;line-height:24px;font-weight:500;color:#ffffff;text-decoration:none;">{label}</a></p>'
        )

    @classmethod
    def _build_offer_table(cls, rows: list[tuple[str, str]]) -> str:
        """The offer as label and value rows separated by hairlines; the first sentence of a value leads in ink."""
        cells: list[str] = []
        for index, (label, text) in enumerate(rows):
            closing_rule: str = f"border-bottom:1px solid {cls._RULE_COLOR};" if index == len(rows) - 1 else ""
            sentences = cls._FIRST_SENTENCE.fullmatch(text) if "<" not in text else None
            value: str = (
                f'{sentences.group(1)}<span style="display:block;margin:2px 0 0;font-weight:400;'
                f'color:{cls._TEXT_COLOR};">{sentences.group(2)}</span>'
                if sentences
                else text
            )
            cells.append(
                f'<tr><td class="em-label" width="120" valign="top" style="width:120px;padding:10px 12px 10px 0;'
                f"border-top:1px solid {cls._RULE_COLOR};{closing_rule}font-size:14px;line-height:20px;"
                f'color:{cls._MUTED_COLOR};">{label}</td>'
                f'<td valign="top" style="padding:10px 0;border-top:1px solid {cls._RULE_COLOR};{closing_rule}'
                f"font-size:14px;line-height:20px;font-weight:500;color:{cls._INK_COLOR};"
                f'word-break:break-word;">{value}</td></tr>'
            )
        return (
            f'<p style="margin:12px 0 12px;font-size:15px;line-height:22px;font-weight:600;color:{cls._INK_COLOR};">'
            f"{cls._OFFER_TABLE_TITLE}</p>"
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="border-collapse:collapse;margin:0 0 32px;">{"".join(cells)}</table>'
        )

    @classmethod
    def _apply_card_colours(cls, content: str, accent: str) -> str:
        """Re-dress the blocks ``EmailVariables`` generated for a plain email: accent links, a thumbnail as wide as the card."""
        thumbnail_width: int = EmailVariables.THUMBNAIL_WIDTH
        return (
            content.replace(
                f'style="{EmailVariables.LINK_STYLE}"',
                f'style="color:{accent};font-weight:500;text-decoration:none;word-break:break-word;"',
            )
            .replace(f'style="{EmailVariables.THUMBNAIL_PARAGRAPH_STYLE}"', 'style="margin:0 0 6px;"')
            .replace(
                f'style="{EmailVariables.THUMBNAIL_NOTE_STYLE}"',
                f'style="margin:0 0 16px;font-size:13px;line-height:19px;color:{cls._MUTED_COLOR};"',
            )
            .replace(f'width="{thumbnail_width}"', f'width="{cls._CARD_COLUMN_WIDTH}"')
            .replace(f"max-width:{thumbnail_width}px", f"max-width:{cls._CARD_COLUMN_WIDTH}px")
        )

    @classmethod
    def _tidy_signature(cls, signature_html: str) -> str:
        """Drop the clipboard markers and the trailing line break of a pasted signature: the card ends on its own padding."""
        return cls._TRAILING_BREAKS.sub(r"\1", cls._CLIPBOARD_MARKER.sub("", signature_html))

    @classmethod
    def _build_document(cls, content: str, signature_html: str) -> str:
        return (
            '<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n{cls._PHONE_STYLE}\n</head>\n'
            f'<body style="margin:0;padding:0;background-color:{cls._PAGE_COLOR};">\n'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="background-color:{cls._PAGE_COLOR};">\n<tr>\n'
            '<td class="em-outer" align="center" style="padding:0 16px;">\n'
            '<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" '
            'style="width:100%;max-width:600px;">\n'
            '<tr>\n<td class="em-top" height="32" style="height:32px;font-size:0;line-height:0;">&nbsp;</td>\n</tr>\n'
            f'<tr>\n<td class="em-card" style="padding:40px;background-color:{cls._CARD_COLOR};border-radius:16px;'
            f"font-family:{cls._FONT_STACK};font-size:15px;line-height:24px;color:{cls._TEXT_COLOR};"
            f'text-align:left;">\n{content}\n{signature_html}\n</td>\n</tr>\n'
            f'<tr>\n<td class="em-foot" style="padding:24px 0 40px;font-family:{cls._FONT_STACK};font-size:12px;'
            f'line-height:18px;color:{cls._MUTED_COLOR};text-align:left;">{UnsubscribeService.FOOTER_SLOT}</td>\n</tr>\n'
            "</table>\n</td>\n</tr>\n</table>\n</body>\n</html>"
        )
