"""Build the list of given names the decision-maker search knows (services/decision_maker/given_names.tsv).

Two open data files count the first names given at birth:

- INSEE « Fichier des prénoms », births in France 1900-2024 (Licence Ouverte):
  https://www.insee.fr/fr/statistiques/8595130
- Retraite Québec « Banque de prénoms », births in Québec 1980-2025 (CC-BY 4.0):
  https://www.donneesquebec.ca/recherche/dataset/banque-de-prenoms-garcons and banque-de-prenoms-filles

A name is kept when enough people bear it, since rare spellings collide with common words, with the
sex nearly all of them have (« M », « F »), else « X ». The French file decides the sex of the names it
knows: the Québec girls' file repeats some boys' rows (« MAXIME », « JONATHAN ») and only adds names.

Each name is also marked common or rare: a rare given name is often a last name (« Marty », « Roy »),
so only a common one may tell where a last name stops. It also carries the spelling most of its bearers have
in France (« Stéphane » for « stephane »), since a registry writes names without their accents; the Québec
file has no accents at all. The two files count too few people of the Swiss
German, Albanian, Portuguese, Italian or Spanish communities: their common names come from
COMMON_FOREIGN_NAMES, and the ones the files lack altogether from SUPPLEMENTARY_NAMES.

Usage::

    python scripts/build_given_names.py
"""

from __future__ import annotations

import csv
import io
import os
import sys
import zipfile
from collections import Counter, defaultdict

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.decision_maker.normalize import fold

INSEE_URL: str = "https://www.insee.fr/fr/statistiques/fichier/8595130/prenoms-2025-nat_csv.zip"
QUEBEC_URLS: dict[str, str] = {
    "M": (
        "https://www.donneesquebec.ca/recherche/dataset/93d640ec-d059-4768-b7ed-388604b278aa/resource/"
        "039539f5-af55-4d8f-9010-ca718e45c2a5/download/grande_listeg_csv.csv"
    ),
    "F": (
        "https://www.donneesquebec.ca/recherche/dataset/13db2583-427a-4e5f-b679-8532d3df571f/resource/"
        "bf77b504-54b9-4db8-be53-b92156175c12/download/grande_listef_csv.csv"
    ),
}
OUTPUT_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "decision_maker", "given_names.tsv"
)
MIN_FRENCH_BIRTHS: int = 200
MIN_QUEBEC_BIRTHS: int = 50
COMMON_FRENCH_BIRTHS: int = 2000
COMMON_QUEBEC_BIRTHS: int = 500
SEX_MAJORITY: float = 0.9
SUPPLEMENTARY_NAMES: dict[str, str] = {
    "adelino": "M",
    "agron": "M",
    "arben": "M",
    "ardian": "M",
    "arsim": "M",
    "avni": "M",
    "beat": "M",
    "bekim": "M",
    "besnik": "M",
    "blerim": "M",
    "bujar": "M",
    "burim": "M",
    "custodio": "M",
    "dardan": "M",
    "driton": "M",
    "faton": "M",
    "fatmir": "M",
    "fitim": "M",
    "gezim": "M",
    "ilir": "M",
    "isuf": "M",
    "jurg": "M",
    "kushtrim": "M",
    "labinot": "M",
    "lirim": "M",
    "mentor": "M",
    "reto": "M",
    "ruedi": "M",
    "simao": "M",
    "tiberio": "M",
    "ueli": "M",
    "urs": "M",
    "valon": "M",
    "visar": "M",
    "arta": "F",
    "besa": "F",
    "drita": "F",
    "filipa": "F",
    "graca": "F",
    "lurdes": "F",
    "mimoza": "F",
    "regula": "F",
    "rute": "F",
    "teuta": "F",
    "verena": "F",
    "vjosa": "F",
}
COMMON_FOREIGN_NAMES: frozenset[str] = frozenset(
    {
        "abilio",
        "agostinho",
        "alvaro",
        "americo",
        "armando",
        "artur",
        "augusto",
        "beatriz",
        "bernardo",
        "carlo",
        "catarina",
        "diogo",
        "domenico",
        "domingos",
        "eduardo",
        "fabrizio",
        "fritz",
        "goncalo",
        "heinz",
        "helder",
        "henrique",
        "ignacio",
        "ivo",
        "jaime",
        "javier",
        "joaquin",
        "kemal",
        "kurt",
        "marcos",
        "margarida",
        "markus",
        "marta",
        "maurizio",
        "nuno",
        "orlando",
        "osman",
        "pietro",
        "pilar",
        "ramon",
        "raquel",
        "raul",
        "renato",
        "riccardo",
        "rodrigo",
        "rogerio",
        "rolf",
        "rui",
        "silvio",
        "stefano",
        "susana",
        "teresa",
        "umberto",
        "ursula",
        "valter",
        "vasco",
        "vera",
        "vitor",
        "vittorio",
        "werner",
    }
)


def french_births(spellings: dict[str, Counter[str]]) -> dict[str, list[int]]:
    """Births per name and sex in France since 1900, from the INSEE national file; each spelling counted in *spellings*."""
    births: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    archive = zipfile.ZipFile(io.BytesIO(httpx.get(INSEE_URL, timeout=120, follow_redirects=True).content))
    with archive.open(archive.namelist()[0]) as handle:
        for row in csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8"), delimiter=";"):
            if row["prenom"].startswith("_") or not row["valeur"].isdigit():
                continue
            births[fold(row["prenom"])][int(row["sexe"]) - 1] += int(row["valeur"])
            spellings[fold(row["prenom"])][row["prenom"].title()] += int(row["valeur"])
    return births


def quebec_births() -> dict[str, list[int]]:
    """Births per name and sex in Québec since 1980, from the two Retraite Québec files (« <5 » counts as nothing)."""
    births: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for sex, url in QUEBEC_URLS.items():
        text = httpx.get(url, timeout=120, follow_redirects=True).content.decode("utf-8-sig")
        for row in csv.reader(io.StringIO(text)):
            if not row or row[0] == "PRENOMS":
                continue
            count = sum(int(cell) for cell in row[1:] if cell.isdigit())
            births[fold(row[0])][0 if sex == "M" else 1] += count
    return births


def usual_spelling(name: str, spellings: dict[str, Counter[str]]) -> str:
    """The spelling most bearers of a name have in France (« Stéphane »), else the name in title case."""
    return spellings[name].most_common(1)[0][0] if spellings.get(name) else name.title()


def sex_of(male_births: int, female_births: int) -> str:
    """« M » or « F » when nearly all bearers have that sex, else « X »."""
    total = male_births + female_births
    if male_births >= SEX_MAJORITY * total:
        return "M"
    if female_births >= SEX_MAJORITY * total:
        return "F"
    return "X"


def main() -> None:
    """Download both files and write the merged list, one « name<TAB>sex<TAB>common<TAB>spelling » line per name."""
    lines: dict[str, tuple[str, bool]] = {}
    spellings: dict[str, Counter[str]] = defaultdict(Counter)
    sources = (
        (french_births(spellings), MIN_FRENCH_BIRTHS, COMMON_FRENCH_BIRTHS),
        (quebec_births(), MIN_QUEBEC_BIRTHS, COMMON_QUEBEC_BIRTHS),
    )
    for births, floor, common_floor in sources:
        for name, (male, female) in births.items():
            if male + female < floor or not name.replace("-", "").isalpha():
                continue
            sex, is_common = lines.get(name, (sex_of(male, female), False))
            is_community_name = name in COMMON_FOREIGN_NAMES or name in SUPPLEMENTARY_NAMES
            lines[name] = (sex, is_common or male + female >= common_floor or is_community_name)
    for name, sex in SUPPLEMENTARY_NAMES.items():
        lines.setdefault(name, (sex, True))
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.writelines(
            f"{name}\t{sex}\t{int(is_common)}\t{usual_spelling(name, spellings)}\n"
            for name, (sex, is_common) in sorted(lines.items())
        )
    print(f"{len(lines)} given names written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
