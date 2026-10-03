"""The privacy section of a site's legal page, stating what its page really collects, loads and sends."""

from __future__ import annotations

from enums.privacy_regime import PrivacyRegime
from schemas.site_legal_notice import SiteLegalBlock, SiteLegalLine, SiteLegalSection
from services.country_profiles import CountryProfiles, SiteLegalFacts
from services.site_legal.hosting import SITE_HOSTING_PROVIDER
from services.site_legal.lines import SiteLegalLines
from services.site_legal.sources import DEMO_PUBLISHER_COUNTRY_CODE, SiteLegalSources

GOOGLE_PRIVACY_POLICY_URL = "https://policies.google.com/privacy"
PROSPECT_DATA_RETENTION = "au plus trois ans après le dernier contact"
POSTHOG_EVENTS_RETENTION = "un an"
POSTHOG_RECORDINGS_RETENTION = "trente jours"


class PrivacyNoticeBuilder:
    """Builds the « Politique de confidentialité » section of a site (« Protection des données » in Switzerland).

    A delivered site is the business's: the business is in charge of the data, the page measures no
    audience, and the regime of the business's country words the rights. A demo is its publisher's:
    the publisher is in charge, measures the visits and reads the message left on the demo, under the
    GDPR. Both list the third parties the template's page really loads (host, fonts, images, map,
    plate lookup), as the template module declares them.
    """

    @classmethod
    def build(cls, sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalSection:
        """
        Build the privacy section of one site.

        Args:
            sources: The facts of the site.
            lines: The line writer of the site's country.

        Returns:
            The section, with every block that has at least one line.
        """
        facts = sources.country.site_legal
        if sources.is_demo:
            regime_facts = CountryProfiles.get(DEMO_PUBLISHER_COUNTRY_CODE).site_legal
            blocks = [
                cls._demo_controller_block(sources, lines),
                cls._demo_measurement_block(sources, lines),
                cls._demo_message_block(sources, lines),
                cls._demo_form_block(sources, lines),
            ]
        else:
            regime_facts = facts
            blocks = [
                cls._controller_block(sources, lines),
                cls._contact_block(sources, lines),
                cls._audience_block(sources, lines),
            ]
        blocks += [
            cls._services_block(sources, lines),
            cls._transfers_block(lines, regime_facts.privacy_regime),
            cls._rights_block(sources, lines, regime_facts),
        ]
        return SiteLegalSection(
            anchor=SiteLegalLines.anchor(facts.privacy_notice_title),
            title=facts.privacy_notice_title,
            blocks=[block for block in blocks if block.lines],
        )

    @staticmethod
    def _controller_block(sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """Who is in charge of a delivered site's data: the business (in Québec, its highest authority)."""
        business = sources.business
        if sources.country.site_legal.privacy_regime is PrivacyRegime.QUEBEC_PRIVATE_SECTOR:
            heading = "Responsable de la protection des renseignements personnels"
            role = lines.value("Fonction", "personne ayant la plus haute autorité au sein de l'entreprise")
        else:
            heading = "Responsable du traitement"
            role = []
        return SiteLegalBlock(
            heading=lines.localize(heading),
            kind="identity",
            lines=[
                *lines.plain(business.name),
                *role,
                *lines.plain(business.address),
                *lines.phone(business.phone, sources.country.code),
                *lines.email(business.email),
            ],
        )

    @staticmethod
    def _contact_block(sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """What happens to what a visitor sends a delivered site's business, through its form or directly."""
        business = sources.business.name
        regime = sources.country.site_legal.privacy_regime
        statements: list[SiteLegalLine] = []
        if sources.visitor_data.has_contact_form:
            heading = "Formulaire de contact"
            statements.append(
                lines.sentence(
                    "Le formulaire de ce site n'envoie rien à un serveur : il ouvre votre messagerie avec un e-mail "
                    "prérempli, adressé à {business}. Rien ne part tant que vous n'envoyez pas cet e-mail vous-même.",
                    business=business,
                )
            )
            statements.append(
                lines.sentence(
                    "Les informations que vous y écrivez (par exemple votre nom, votre téléphone, votre adresse "
                    "e-mail et votre demande) servent uniquement à vous répondre."
                )
            )
        else:
            heading = "Vos messages"
            statements.append(
                lines.sentence(
                    "Ce site n'a pas de formulaire. Si vous écrivez à {business} ou l'appelez, les informations que "
                    "vous donnez servent uniquement à vous répondre.",
                    business=business,
                )
            )
        statements.append(
            lines.sentence(
                "Rien n'est obligatoire, mais sans moyen de vous recontacter, {business} ne pourra pas vous répondre.",
                business=business,
            )
        )
        if regime is PrivacyRegime.GDPR:
            statements.append(
                lines.sentence(
                    "Base légale : les mesures précontractuelles prises à votre demande (article 6, paragraphe 1, "
                    "point b, du RGPD)."
                )
            )
        if regime is PrivacyRegime.QUEBEC_PRIVATE_SECTOR:
            statements.append(
                lines.sentence(
                    "En envoyant votre message, vous consentez à ce que {business} utilise ces renseignements pour "
                    "vous répondre. Vous pouvez retirer ce consentement à tout moment.",
                    business=business,
                )
            )
        statements.append(
            lines.sentence("Destinataire : uniquement {business}, dans sa messagerie.", business=business)
        )
        statements.append(
            lines.sentence(
                "Durée de conservation : le temps de traiter votre demande, puis {retention}.",
                retention=PROSPECT_DATA_RETENTION,
            )
        )
        return SiteLegalBlock(heading=lines.localize(heading), lines=statements)

    @classmethod
    def _audience_block(cls, sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """A delivered site measures no audience and sets no cookie; an embedded Google map may set Google's."""
        statements = [lines.sentence("Ce site ne mesure pas son audience et ne dépose aucun cookie.")]
        if sources.visitor_data.has_google_map:
            statements += cls._google_map_statements(lines)
        return SiteLegalBlock(heading=lines.localize("Mesure d'audience et cookies"), lines=statements)

    @staticmethod
    def _google_map_statements(lines: SiteLegalLines) -> list[SiteLegalLine]:
        """What loading the embedded Google map sends to Google, and how a visitor refuses its cookies."""
        return [
            lines.sentence(
                "La carte affichée provient de Google Maps : en la chargeant, votre navigateur se connecte aux "
                "serveurs de Google, qui reçoit votre adresse IP et peut déposer ses propres cookies. Vous pouvez "
                "refuser ces cookies dans les réglages de votre navigateur."
            ),
            lines.sentence("Politique de confidentialité de Google", href=GOOGLE_PRIVACY_POLICY_URL),
        ]

    @staticmethod
    def _demo_controller_block(sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """Who is in charge of a demo's data: its publisher."""
        publisher = sources.publisher
        heading = lines.localize("Responsable du traitement pendant la démonstration")
        if publisher is None:
            return SiteLegalBlock(heading=heading, kind="identity", lines=[])
        return SiteLegalBlock(
            heading=heading,
            kind="identity",
            lines=[
                *lines.plain(publisher.company_name),
                *lines.plain(publisher.person_name),
                *lines.plain(publisher.postal_address),
                *lines.email(publisher.email),
            ],
        )

    @staticmethod
    def _demo_measurement_block(sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """The visit measurement a demo runs (PostHog) and the live alerts its publisher receives."""
        business = sources.business.name
        publisher = sources.publisher_label
        return SiteLegalBlock(
            heading=lines.localize("Mesure des visites de la démonstration"),
            lines=[
                lines.sentence(
                    "Cette démonstration a été préparée pour {business}. Pour savoir si elle l'intéresse, {publisher} "
                    "mesure les visites avec l'outil PostHog, dont les données sont hébergées dans l'Union "
                    "européenne (Francfort).",
                    business=business,
                    publisher=publisher,
                ),
                lines.sentence(
                    "Sont enregistrés : les pages vues, les parties du site affichées, les clics, le défilement, le "
                    "temps passé et un enregistrement de la navigation dans lequel tous les champs de saisie sont "
                    "masqués."
                ),
                lines.sentence(
                    "Aucun cookie n'est déposé : l'identifiant de la visite reste dans la mémoire de l'onglet et "
                    "disparaît à sa fermeture. Les visites sont rattachées à cette démonstration."
                ),
                lines.sentence(
                    "Certaines actions (ouverture de la démonstration, clic sur le téléphone ou l'adresse e-mail, "
                    "temps passé) sont signalées en direct à {publisher}.",
                    publisher=publisher,
                ),
                lines.sentence(
                    "Base légale : l'intérêt légitime, {publisher} cherchant à savoir si sa proposition intéresse "
                    "{business} (article 6, paragraphe 1, point f, du RGPD). Vous pouvez vous y opposer en lui "
                    "écrivant.",
                    business=business,
                    publisher=publisher,
                ),
                lines.sentence(
                    "Durée de conservation : chez PostHog, {events} pour les mesures et {recordings} pour les "
                    "enregistrements de navigation ; le suivi de la proposition, le temps de la prospection et "
                    "{retention}.",
                    events=POSTHOG_EVENTS_RETENTION,
                    recordings=POSTHOG_RECORDINGS_RETENTION,
                    retention=PROSPECT_DATA_RETENTION,
                ),
            ],
        )

    @staticmethod
    def _demo_message_block(sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """The message a visitor writes in the demo's « Ce site vous plaît ? » panel, even when unsent."""
        return SiteLegalBlock(
            heading=lines.localize("Message laissé sur la démonstration"),
            lines=[
                lines.sentence(
                    "Le message écrit dans le panneau « Ce site vous plaît ? » est transmis à {publisher}, y compris "
                    "s'il est refermé sans être envoyé, pour qu'il puisse vous répondre. Il est conservé le temps "
                    "de la prospection, et {retention}.",
                    publisher=sources.publisher_label,
                    retention=PROSPECT_DATA_RETENTION,
                )
            ],
        )

    @staticmethod
    def _demo_form_block(sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """A demo's form works as on the final site: it opens the visitor's mail app towards the business."""
        if not sources.visitor_data.has_contact_form:
            return SiteLegalBlock(heading=lines.localize("Formulaire de contact"), lines=[])
        return SiteLegalBlock(
            heading=lines.localize("Formulaire de contact"),
            lines=[
                lines.sentence(
                    "Le formulaire de la démonstration n'envoie rien à un serveur : il ouvre votre messagerie avec un "
                    "e-mail prérempli, adressé à {business}. {publisher} ne reçoit pas ces e-mails.",
                    business=sources.business.name,
                    publisher=sources.publisher_label,
                )
            ],
        )

    @classmethod
    def _services_block(cls, sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """The third parties the page loads, each receiving the visitor's IP address like any web server."""
        visitor_data = sources.visitor_data
        statements = [
            lines.sentence(
                "Hébergement : {host} ({host_country}). Comme pour toute page web, l'hébergeur reçoit l'adresse IP "
                "de votre appareil et la page demandée, pour vous l'envoyer.",
                host=SITE_HOSTING_PROVIDER.name,
                host_country=SITE_HOSTING_PROVIDER.country_name,
            )
        ]
        if visitor_data.has_google_fonts:
            statements.append(
                lines.sentence(
                    "Polices de caractères : elles sont chargées depuis Google Fonts, qui reçoit l'adresse IP de "
                    "votre appareil."
                )
            )
        statements.append(
            lines.sentence(
                "Images : elles sont chargées depuis les serveurs de Cloudflare, de Storyblok ou d'Unsplash, qui "
                "reçoivent l'adresse IP de votre appareil."
            )
        )
        if visitor_data.has_google_map and sources.is_demo:
            statements += cls._google_map_statements(lines)
        if visitor_data.has_vehicle_plate_lookup:
            statements.append(
                lines.sentence(
                    "Recherche par plaque d'immatriculation : si vous lancez l'identification du véhicule, la plaque "
                    "saisie est envoyée au service Auto Ways, qui renvoie la marque et le modèle."
                )
            )
        return SiteLegalBlock(heading=lines.localize("Services techniques utilisés par le site"), lines=statements)

    @staticmethod
    def _transfers_block(lines: SiteLegalLines, regime: PrivacyRegime) -> SiteLegalBlock:
        """Where the technical data goes outside the regime's territory, and on what ground."""
        if regime is PrivacyRegime.QUEBEC_PRIVATE_SECTOR:
            return SiteLegalBlock(
                heading=lines.localize("Communication à l'extérieur du Québec"),
                lines=[
                    lines.sentence(
                        "Ces renseignements techniques (adresse IP, page consultée) peuvent être traités à "
                        "l'extérieur du Québec, notamment aux États-Unis, par les prestataires cités ci-dessus."
                    )
                ],
            )
        if regime is PrivacyRegime.SWISS_FADP:
            return SiteLegalBlock(
                heading=lines.localize("Communication à l'étranger"),
                lines=[
                    lines.sentence(
                        "Certains de ces prestataires, dont Vercel, Google et Cloudflare, traitent ces données aux "
                        "États-Unis. Ils sont certifiés selon le Swiss-US Data Privacy Framework, que le Conseil "
                        "fédéral reconnaît comme garantissant un niveau de protection adéquat."
                    )
                ],
            )
        return SiteLegalBlock(
            heading=lines.localize("Transferts hors de l'Union européenne"),
            lines=[
                lines.sentence(
                    "Certains de ces prestataires, dont Vercel, Google et Cloudflare, traitent ces données aux "
                    "États-Unis. Ils sont certifiés selon le Data Privacy Framework UE-États-Unis, reconnu par la "
                    "Commission européenne comme garantissant un niveau de protection adéquat."
                )
            ],
        )

    @staticmethod
    def _rights_block(sources: SiteLegalSources, lines: SiteLegalLines, regime_facts: SiteLegalFacts) -> SiteLegalBlock:
        """The visitor's rights under the regime, the contact to exercise them and the authority to turn to."""
        controller = sources.publisher_label if sources.is_demo else sources.business.name
        authority = SiteLegalLine(text=regime_facts.privacy_authority_name, href=regime_facts.privacy_authority_url)
        if regime_facts.privacy_regime is PrivacyRegime.QUEBEC_PRIVATE_SECTOR:
            rights = [
                lines.sentence(
                    "Vous pouvez demander à accéder aux renseignements personnels qui vous concernent, à les faire "
                    "rectifier ou à en obtenir une copie dans un format technologique structuré et couramment "
                    "utilisé, et retirer votre consentement, en écrivant au responsable de la protection des "
                    "renseignements personnels (coordonnées ci-dessus). Il vous répond par écrit au plus tard "
                    "30 jours après avoir reçu votre demande."
                ),
                lines.sentence("Vous pouvez aussi porter plainte auprès de l'organisme de surveillance :"),
            ]
        elif regime_facts.privacy_regime is PrivacyRegime.SWISS_FADP:
            rights = [
                lines.sentence(
                    "Vous pouvez demander à {controller} si des données vous concernant sont traitées et en obtenir "
                    "une copie, les faire rectifier ou effacer, ou vous opposer à leur traitement, en lui écrivant "
                    "(coordonnées ci-dessus).",
                    controller=controller,
                ),
                lines.sentence("Vous pouvez aussi vous adresser à l'autorité fédérale de surveillance :"),
            ]
        else:
            rights = [
                lines.sentence(
                    "Vous pouvez demander à {controller} d'accéder à vos données, de les rectifier ou de les effacer, "
                    "d'en limiter le traitement, de vous y opposer ou d'en recevoir une copie, en lui écrivant "
                    "(coordonnées ci-dessus).",
                    controller=controller,
                ),
                lines.sentence(
                    "Si vous estimez que vos droits ne sont pas respectés, vous pouvez introduire une réclamation "
                    "auprès de l'autorité de protection des données :"
                ),
            ]
        return SiteLegalBlock(heading=lines.localize("Vos droits"), lines=[*rights, authority])
