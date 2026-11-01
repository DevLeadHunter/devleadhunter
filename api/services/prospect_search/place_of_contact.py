"""
Place of a contact — whether an email belongs to the business, judged by the place its page and its words point to.

A namesake elsewhere in France shares the business's name and its trade: its email reads like the business's own.
The place tells them apart. A page giving an email tells whose it is by what stands beside it: a directory lists
businesses one after the other, so the number written nearest the address is its owner's; a page placing the
business nowhere (no phone of its, no town, no postal code of its département) proves nothing about it. The address
itself may name a place (« rg.elec.89@… » is written in the Yonne, « …occitanie@… » in the south), and so may the
address of a Facebook page (« facebook.com/Exemple84700 »). A page written in another script (a Korean job offer
whose phone shares the number's digits) is never about a French-speaking tradesman.
"""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

from services.decision_maker.french_departments import FrenchDepartments
from services.decision_maker.normalize import fold
from services.french_overseas import FrenchOverseas
from services.prospect_search.candidate_facts import CandidateFacts

# An international number (« +33 6 81 15 68 06 »), a national one (« 04.73.28.04.37 », « 078 757 57 42 »), or a
# North American one (« (819) 555-0199 »).
_PHONE_RE: re.Pattern[str] = re.compile(
    r"\+\d{2,3}[\s.\-]?(?:\(0\)[\s.\-]?)?\d(?:[\s.\-]?\d){7,9}"
    r"|\b0\d{1,3}(?:[\s./-]?\d{2,3}){3,4}\b"
    r"|\(?\b\d{3}\)?[\s.\-]?\d{3}[\s.\-]\d{4}\b"
)
_NON_DIGITS_RE: re.Pattern[str] = re.compile(r"\D")
_POSTAL_CODE_RE: re.Pattern[str] = re.compile(r"(?<!\d)(\d{5})(?!\d)")
_DIGIT_RUN_RE: re.Pattern[str] = re.compile(r"\d+")
_ADDRESS_SEPARATORS_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
# National numbers are nine digits after the trunk zero in France, Switzerland and Belgium.
_PHONE_DIGITS_COMPARED: int = 9
_OVERSEAS_DEPARTMENTS: frozenset[str] = frozenset({"971", "972", "973", "974", "976"})
_HIGHEST_MAINLAND_DEPARTMENT: int = 95
# Letters of the scripts a French, Swiss or Québec tradesman never writes in: Cyrillic, Greek, Hebrew, Arabic, Thai,
# Hangul, the Japanese kana and the Chinese characters.
_FOREIGN_SCRIPT_RE: re.Pattern[str] = re.compile(
    r"[Ͱ-ϿЀ-ӿ֐-׿؀-ۿ฀-๿ᄀ-ᇿ぀-ヿ㐀-鿿"
    r"가-힯]"
)
_LATIN_LETTER_RE: re.Pattern[str] = re.compile(r"[a-zA-ZÀ-ɏ]")
# A street as an address writes it, read on folded text: its kind, then the first word of its name (« Rte de la
# Bourgeoisie 5 » names « bourgeoisie », « 2 rue des Gorges » « gorges »).
_STREET_NAME_RE: re.Pattern[str] = re.compile(
    r"\b(?:rue|route|rte|chemin|ch|avenue|av|boulevard|bd|place|pl|impasse|imp|allee|quai|chaussee|faubourg|sentier"
    r"|passage|square|cours|ruelle|promenade)\b\.?\s+(?:(?:de|du|des|la|le|les|d|l)\b['’\s]*)*([a-z][a-z-]{2,})"
)
_MAINLAND_DEPARTMENTS: frozenset[str] = frozenset(
    f"{number:02d}" for number in range(1, _HIGHEST_MAINLAND_DEPARTMENT + 1)
) - {"20"}
# Regions, provinces and neighbouring countries an address may name, with the départements they cover.
_DEPARTMENTS_BY_PLACE_WORD: dict[str, frozenset[str]] = {
    "occitanie": frozenset({"09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"}),
    "languedoc": frozenset({"11", "30", "34", "48", "66"}),
    "roussillon": frozenset({"66"}),
    "bretagne": frozenset({"22", "29", "35", "44", "56"}),
    "breizh": frozenset({"22", "29", "35", "44", "56"}),
    "bzh": frozenset({"22", "29", "35", "44", "56"}),
    "paysdelaloire": frozenset({"44", "49", "53", "72", "85"}),
    "pdl": frozenset({"44", "49", "53", "72", "85"}),
    "centrevaldeloire": frozenset({"18", "28", "36", "37", "41", "45"}),
    "cvl": frozenset({"18", "28", "36", "37", "41", "45"}),
    "normandie": frozenset({"14", "27", "50", "61", "76"}),
    "alsace": frozenset({"67", "68"}),
    "lorraine": frozenset({"54", "55", "57", "88"}),
    "champagne": frozenset({"08", "10", "51", "52"}),
    "grandest": frozenset({"08", "10", "51", "52", "54", "55", "57", "67", "68", "88"}),
    "provence": frozenset({"04", "05", "06", "13", "83", "84"}),
    "paca": frozenset({"04", "05", "06", "13", "83", "84"}),
    "cotedazur": frozenset({"06", "83"}),
    "auvergne": frozenset({"03", "15", "43", "63"}),
    "auvergnerhonealpes": frozenset({"01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"}),
    "aura": frozenset({"01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"}),
    "ara": frozenset({"01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"}),
    "aquitaine": frozenset({"16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"}),
    "limousin": frozenset({"19", "23", "87"}),
    "poitou": frozenset({"16", "17", "79", "86"}),
    "charente": frozenset({"16", "17"}),
    "bourgogne": frozenset({"21", "58", "71", "89"}),
    "franchecomte": frozenset({"25", "39", "70", "90"}),
    "bfc": frozenset({"21", "25", "39", "58", "70", "71", "89", "90"}),
    "picardie": frozenset({"02", "60", "80"}),
    "nordpasdecalais": frozenset({"59", "62"}),
    "npdc": frozenset({"59", "62"}),
    "hautsdefrance": frozenset({"02", "59", "60", "62", "80"}),
    "hdf": frozenset({"02", "59", "60", "62", "80"}),
    "iledefrance": frozenset({"75", "77", "78", "91", "92", "93", "94", "95"}),
    "idf": frozenset({"75", "77", "78", "91", "92", "93", "94", "95"}),
    "savoie": frozenset({"73", "74"}),
    "rhonealpes": frozenset({"01", "07", "26", "38", "42", "69", "73", "74"}),
    "vendee": frozenset({"85"}),
    "perigord": frozenset({"24"}),
    "belux": frozenset(),
    "belgique": frozenset(),
    "suisse": frozenset(),
    "luxembourg": frozenset(),
    "quebec": frozenset(),
}
# A place word this short only counts as a whole part of the address, or as its ending (« flashelecidf »).
_SHORT_PLACE_WORD_MAX_CHARS: int = 5
_PLACE_WORDS_ENDING_FIRST_NAMES: frozenset[str] = frozenset({"ara", "aura"})
_FACEBOOK_PAGE_PREFIXES: frozenset[str] = frozenset({"p", "pages", "people"})
_EMAIL_SOURCE: str = "Son email"
_EMAIL_PAGE_SOURCE: str = "La page Facebook de son email"
_FACEBOOK_PAGE_SOURCE: str = "Sa page Facebook"


class PlaceOfContact:
    """Tells whether an email and the pages giving it point to the business's place or to another one."""

    @classmethod
    def is_beside_another_phone(cls, text: str, email: str, phone: str | None) -> bool:
        """
        Whether the phone number written nearest the email in a text is not the business's: another entry's address.

        Args:
            text: A result's title and snippet.
            email: An address read in it.
            phone: The business's phone number.

        Returns:
            True when the text shows numbers and the closest one to the address is another's; False when it shows
            none, or the business has no number to compare.
        """
        own_digits = _NON_DIGITS_RE.sub("", phone or "")[-_PHONE_DIGITS_COMPARED:]
        nearest_digits = cls._number_nearest(text, email)
        if len(own_digits) < _PHONE_DIGITS_COMPARED or nearest_digits is None:
            return False
        return not nearest_digits.endswith(own_digits)

    @classmethod
    def is_beside_own_phone(cls, text: str, email: str, phone: str | None) -> bool:
        """
        Whether the phone number written nearest the email in a text is the business's own (« Tél. 078 … • E-mail: … »).

        Args:
            text: A result's title and snippet.
            email: An address read in it.
            phone: The business's phone number.

        Returns:
            True when the closest number to the address is the business's.
        """
        own_digits = _NON_DIGITS_RE.sub("", phone or "")[-_PHONE_DIGITS_COMPARED:]
        nearest_digits = cls._number_nearest(text, email)
        return (
            len(own_digits) == _PHONE_DIGITS_COMPARED and bool(nearest_digits) and nearest_digits.endswith(own_digits)
        )

    @staticmethod
    def _number_nearest(text: str, email: str) -> str | None:
        """The digits of the phone number written nearest an email in a text, or None when it shows none."""
        email_start = text.lower().find(email.lower())
        if email_start < 0:
            return None
        email_end = email_start + len(email)
        # At equal distance, the number written before the address is its owner's (« Exemple · 05 … · contact@… »).
        numbers = [
            (
                max(match.start() - email_end, email_start - match.end(), 0),
                match.start() > email_start,
                _NON_DIGITS_RE.sub("", match.group(0)),
            )
            for match in _PHONE_RE.finditer(text)
        ]
        return min(numbers)[2] if numbers else None

    @staticmethod
    def street_names(text: str | None) -> set[str]:
        """
        The streets a text writes, by the first word of their name (« Rte de la Bourgeoisie 5 » gives « bourgeoisie »).

        Args:
            text: An address, a result's snippet.

        Returns:
            The folded first words of the streets' names.
        """
        return set(_STREET_NAME_RE.findall(fold(text or "")))

    @classmethod
    def shows_another_street(cls, text: str, facts: CandidateFacts) -> bool:
        """
        Whether a text writes street addresses, none of them the business's: the entry of a business living elsewhere.

        Args:
            text: A result's title and snippet.
            facts: The business, with its street address.

        Returns:
            True when the text names streets and the business's street is not among them; False when the business's
            address names no street.
        """
        own_streets = cls.street_names(facts.address)
        written_streets = cls.street_names(text)
        return bool(own_streets) and bool(written_streets) and not own_streets & written_streets

    @staticmethod
    def is_in_foreign_script(text: str) -> bool:
        """Whether a text is written mostly in a script no French-speaking tradesman writes in (Hangul, Cyrillic…)."""
        foreign_letters = len(_FOREIGN_SCRIPT_RE.findall(text))
        return foreign_letters > 0 and foreign_letters >= len(_LATIN_LETTER_RE.findall(text))

    @classmethod
    def shows_place_of(cls, text: str, facts: CandidateFacts, department: str | None) -> bool:
        """
        Whether a page places the business where it is: its phone, its town, or a postal code of its département.

        Args:
            text: The page's words (a result's title and snippet).
            facts: The business: its phone, town and address.
            department: The business's département, when known.

        Returns:
            True when one of these appears in the text.
        """
        own_digits = _NON_DIGITS_RE.sub("", facts.phone or "")[-_PHONE_DIGITS_COMPARED:]
        if len(own_digits) == _PHONE_DIGITS_COMPARED and own_digits in _NON_DIGITS_RE.sub("", text):
            return True
        text_key = f" {' '.join(_ADDRESS_SEPARATORS_RE.split(fold(text)))} "
        towns = {town for town in (facts.city, facts.searched_city) if town}
        if any(f" {' '.join(_ADDRESS_SEPARATORS_RE.split(fold(town))).strip()} " in text_key for town in towns):
            return True
        return department is not None and any(
            FrenchDepartments.of_postal_code(code) == department for code in _POSTAL_CODE_RE.findall(text)
        )

    @classmethod
    def names_another_place(cls, text: str, facts: CandidateFacts) -> str | None:
        """
        The place a page names that is not the business's, when the page does not name the business's own.

        In an overseas department, another of its communes: « Garage Flash Auto Carrosserie | Le Marin Martinique »
        is not the page of Flash Car, in Ducos. Elsewhere, a postal code of another département than the one of
        the business's address.

        Args:
            text: The page's words (a result's title and snippet).
            facts: The business: its address, town and searched town.

        Returns:
            The commune or the postal code named, or None when the page names no other place, or the business's too.
        """
        overseas = facts.searched_department or FrenchOverseas.of_address(facts.address)
        if overseas is not None:
            own_commune = next(
                (
                    commune
                    for place in (facts.address, facts.city, facts.searched_city)
                    if (commune := overseas.commune_in(place))
                ),
                None,
            )
            named_commune = overseas.commune_in(text)
            is_another_commune = own_commune is not None and named_commune not in (None, own_commune)
            return named_commune if is_another_commune and not cls._names(text, own_commune or "") else None
        address_postal_code = next(iter(_POSTAL_CODE_RE.findall(facts.address or "")), None)
        department = FrenchDepartments.of_postal_code(address_postal_code)
        if department is None:
            return None
        named_departments = {code: FrenchDepartments.of_postal_code(code) for code in _POSTAL_CODE_RE.findall(text)}
        if department in named_departments.values():
            return None
        return next((code for code, named in named_departments.items() if named is not None), None)

    @staticmethod
    def _names(text: str, place: str) -> bool:
        """Whether a text names a place, whatever its accents, case and hyphens."""
        words = f" {' '.join(_ADDRESS_SEPARATORS_RE.split(fold(text)))} "
        place_words = " ".join(word for word in _ADDRESS_SEPARATORS_RE.split(fold(place)) if word)
        return bool(place_words) and f" {place_words} " in words

    @staticmethod
    async def department_of(facts: CandidateFacts) -> str | None:
        """
        The French département the business is placed in: its address's postal code, else its town's.

        Args:
            facts: The business.

        Returns:
            The département code, or None outside France or when neither tells it.
        """
        if facts.country != "FR":
            return None
        postal_code = next(iter(_POSTAL_CODE_RE.findall(facts.address or "")), None)
        return FrenchDepartments.of_postal_code(postal_code) or await FrenchDepartments.of_town(facts.town)

    @classmethod
    def place_named_in_address(cls, address_part: str, department: str) -> str | None:
        """
        The place an address part names when it is not the business's département.

        A postal code, a département number written alone (« rg.elec.89 »), a region, its abbreviation or a
        neighbouring country (« lejardindeden.occitanie », « flashelecidf », « elecbzh »,
        « jselectricitebelux ») count; a number of one digit, or of four (a year), says nothing. An abbreviation
        ending a first name counts only alone (« ara.elec », never « clara »), and a region of two names counts
        as the one holding the business (« languedocroussillon » for the Hérault, though Roussillon is the
        Pyrénées-Orientales).

        Args:
            address_part: The words before an email's « @ », or the name in a Facebook page's address.
            department: The business's département.

        Returns:
            The number or the word naming another place, or None when the address names none or the business's own.
        """
        folded = fold(unquote(address_part))
        for run in _DIGIT_RUN_RE.findall(folded):
            run_department = (
                FrenchDepartments.of_postal_code(run)
                if len(run) == 5
                else run
                if run in _MAINLAND_DEPARTMENTS or run in _OVERSEAS_DEPARTMENTS
                else None
            )
            if run_department is not None and run_department != department:
                return run
        segments = [segment for segment in _ADDRESS_SEPARATORS_RE.split(re.sub(r"\d+", " ", folded)) if segment]
        named_words = [word for word in _DEPARTMENTS_BY_PLACE_WORD if cls._names_place_word(word, segments)]
        if any(department in _DEPARTMENTS_BY_PLACE_WORD[word] for word in named_words):
            return None
        return max(named_words, key=len, default=None)

    @staticmethod
    def _names_place_word(word: str, segments: list[str]) -> bool:
        """Whether an address's words name a place word: a short one alone or ending a word, a long one anywhere."""
        if word in _PLACE_WORDS_ENDING_FIRST_NAMES:
            return word in segments
        if len(word) <= _SHORT_PLACE_WORD_MAX_CHARS:
            return any(segment == word or segment.endswith(word) for segment in segments)
        return word in "".join(segments)

    @classmethod
    async def note_contact_elsewhere(cls, facts: CandidateFacts) -> None:
        """
        Note the place another than the business's that its email, or the Facebook page giving it, names.

        The words before the « @ », the name in the address of the Facebook page the email was read on and the name
        of the business's Facebook page are read; the first other place found is noted once.

        Args:
            facts: The candidate, completed in place.
        """
        if facts.email is None or any(line.get("fact") == "contact_elsewhere" for line in facts.evidence):
            return
        department = await cls.department_of(facts)
        if department is None:
            return
        email_line = next(
            (
                line
                for line in reversed(facts.evidence)
                if line.get("fact") == "email" and line.get("value") == facts.email
            ),
            {},
        )
        readings = [
            (_EMAIL_SOURCE, facts.email, facts.email.rpartition("@")[0]),
            (_EMAIL_PAGE_SOURCE, email_line.get("url") or "", cls.facebook_page_name(email_line.get("url"))),
            *((_FACEBOOK_PAGE_SOURCE, url, cls.facebook_page_name(url)) for url in cls.facebook_addresses_of(facts)),
        ]
        for source, shown, address_part in readings:
            place = cls.place_named_in_address(address_part, department) if address_part else None
            if place is not None:
                facts.add_evidence("contact_elsewhere", place, source=source, url=shown if "://" in shown else None)
                return

    @staticmethod
    def facebook_addresses_of(facts: CandidateFacts) -> list[str]:
        """The addresses the business's Facebook page was found under, its name written in them when Google gave it."""
        found_under = [line.get("url") or "" for line in facts.evidence if line.get("fact") == "facebook"]
        return [url for url in (facts.facebook_url or "", *found_under) if url]

    @staticmethod
    def facebook_page_name(url: str | None) -> str:
        """The page's own name in a Facebook address (« Exemple84700 »), empty for any other address."""
        parsed = urlparse(url or "")
        if "facebook.com" not in (parsed.hostname or ""):
            return ""
        segments = [segment for segment in parsed.path.split("/") if segment]
        if not segments:
            return ""
        return segments[1] if len(segments) > 1 and segments[0] in _FACEBOOK_PAGE_PREFIXES else segments[0]
