"""
Decision-maker name resolution — finds the PERSON behind a prospect (first/last
name of the owner/manager) so cold emails can open with a real, trusted
greeting instead of the company name.

Public surface:
  - ``decision_maker_resolver`` : the multi-strategy cascade (registre gouv,
    Pappers, mentions légales, réponses du propriétaire, LLM aggregate).
  - ``build_greeting`` : the salutation rules (see greeting.py).

Golden rule everywhere: a WRONG name is worse than NO name — below the
confidence threshold we fall back to a plain « Bonjour ».
"""
from services.decision_maker.greeting import build_greeting
from services.decision_maker.resolver import decision_maker_resolver

__all__ = ["build_greeting", "decision_maker_resolver"]
