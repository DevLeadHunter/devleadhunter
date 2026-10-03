"""Which follow-up steps a campaign may carry, by channel."""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from enums.sms_template_category import SmsTemplateCategory
from models.campaign import Campaign
from schemas.campaign import CampaignFollowUpCreate
from services.campaign_queue_service import CampaignQueueService
from services.email_variables import LOYALTY_CARD_DEMO_MISSING_REFUSAL
from services.sms.templates import DEFAULT_FIRST_CONTACT_KEY, find_sms_template
from services.sms_auto_campaign_service import SMS_AUTO_RELANCE_KIND
from services.sms_variables import SmsVariables


class CampaignFollowUpRules:
    """Check a campaign's follow-up steps before they are saved.

    An email campaign's steps name email templates. An SMS campaign's sequence is one first contact
    and one relance (see ``SmsProspectingRules``), so it carries one step at most: a relance of the
    SMS library that sells the same offer as its first SMS and never recalls an email the prospect
    did not receive. The J+30 relance campaign is already a relance and carries none.
    """

    MAXIMUM_SMS_STEPS: ClassVar[int] = 1

    @classmethod
    def refusal(
        cls, campaign: Campaign, steps: Sequence[CampaignFollowUpCreate], *, first_contact_key: str | None
    ) -> str | None:
        """
        Why these follow-up steps cannot be saved on the campaign, or ``None`` when they can.

        Args:
            campaign: The campaign the steps belong to.
            steps: The whole sequence about to replace the campaign's.
            first_contact_key: The SMS template the campaign's first SMS renders (SMS campaigns).

        Returns:
            The reason shown to the user, or ``None``.
        """
        if campaign.system_kind == SMS_AUTO_RELANCE_KIND:
            return "La campagne J+30 est déjà une relance : elle n'en envoie pas d'autre." if steps else None
        if campaign.channel != "sms":
            if any(step.template_id is None for step in steps):
                return "Choisissez un modèle d'email pour chaque relance."
            return None
        if any(step.sms_template_key is None for step in steps):
            return "Choisissez un modèle SMS pour la relance."
        if len(steps) > cls.MAXIMUM_SMS_STEPS:
            return "Une campagne SMS envoie un premier SMS puis une seule relance."
        first_contact_module: str = CampaignQueueService.sms_template_module(
            find_sms_template(first_contact_key or DEFAULT_FIRST_CONTACT_KEY)
        )
        for step in steps:
            template = find_sms_template(step.sms_template_key or "")
            if template is None or template.category is not SmsTemplateCategory.FOLLOW_UP:
                return "Modèle inconnu : la relance utilise un modèle de relance de la bibliothèque SMS."
            if template.recalls_an_email:
                return f"Le modèle « {template.name} » rappelle votre email : il ne peut pas suivre un premier SMS."
            if template.uses(SmsVariables.CARD_LINK):
                return LOYALTY_CARD_DEMO_MISSING_REFUSAL
            if CampaignQueueService.sms_template_module(template) != first_contact_module:
                return f"Le modèle « {template.name} » ne présente pas la même offre que le premier SMS."
        return None
