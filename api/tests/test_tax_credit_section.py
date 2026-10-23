"""
The « crédit d'impôt » section of a « services à la personne » provider is stored as a site override:
it survives regenerations, needs a heading to exist, and adds its FAQ entry once.
"""

from services.templates.site_content import apply_section_overrides, clean_tax_credit


def _override() -> dict:
    return {
        "heading": "  Votre entretien de jardin   à moitié prix ",
        "lead": "La moitié de la facture vous revient.",
        "points": ["50 % remboursés", "", None, "Attestation fournie"],
        "note": "Plafond de 5 000 € par an.",
        "faqQuestion": "Puis-je bénéficier du crédit d'impôt de 50 % ?",
        "faqAnswer": "Oui, sur l'entretien courant du jardin.",
    }


def test_the_section_needs_a_heading() -> None:
    assert clean_tax_credit({"lead": "Sans titre", "points": ["x"]}) == {}
    assert clean_tax_credit("not a section") == {}


def test_the_section_is_cleaned_line_by_line() -> None:
    cleaned = clean_tax_credit(_override())

    assert cleaned["heading"] == "Votre entretien de jardin à moitié prix"
    assert cleaned["points"] == ["50 % remboursés", "Attestation fournie"]
    assert cleaned["faqQuestion"] == "Puis-je bénéficier du crédit d'impôt de 50 % ?"


def test_a_faq_entry_without_its_answer_is_dropped() -> None:
    cleaned = clean_tax_credit({**_override(), "faqAnswer": ""})

    assert "faqQuestion" not in cleaned and "faqAnswer" not in cleaned


def test_the_override_fills_the_section_and_adds_its_faq_entry_once() -> None:
    content = {"faq": [{"question": "Le devis est-il gratuit ?", "answer": "Oui."}]}

    result = apply_section_overrides(content, {"taxCredit": _override()})

    assert result["taxCreditHeading"] == "Votre entretien de jardin à moitié prix"
    assert result["taxCreditPoints"] == ["50 % remboursés", "Attestation fournie"]
    assert [item["question"] for item in result["faq"]] == [
        "Le devis est-il gratuit ?",
        "Puis-je bénéficier du crédit d'impôt de 50 % ?",
    ]

    again = apply_section_overrides(result, {"taxCredit": _override()})
    assert len(again["faq"]) == 2


def test_a_faq_already_covering_the_credit_keeps_its_own_wording() -> None:
    content = {"faq": [{"question": "Et le crédit d'impôt ?", "answer": "On s'en occupe."}]}

    result = apply_section_overrides(content, {"taxCredit": _override()})

    assert result["faq"] == [{"question": "Et le crédit d'impôt ?", "answer": "On s'en occupe."}]


def test_no_override_leaves_the_content_untouched() -> None:
    content = {"faq": []}

    result = apply_section_overrides(content, {"heroBadge": "Paysagiste"})

    assert "taxCreditHeading" not in result
