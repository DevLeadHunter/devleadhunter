"""Services read from the business's own words: lists are kept, prose and sales lines are not."""

from services.service_list_reader import ServiceListReader


def test_an_emoji_list_keeps_the_services_and_drops_the_sales_lines() -> None:
    """A Facebook intro written as an emoji list: quote, phone, networks and guarantee lines are not services."""
    intro = (
        "🌳 Abattage • Elagage • Dessouchage\n🌿 Aménagement paysager\n✂️ Taille de haies & cèdres\n"
        "✔️ Installation avec garantie 2 ans\n📩 Soumission rapide (819)555-0199\n🛜 Facebook,instagram & tiktok"
    )

    services = ServiceListReader.services_in(intro, business_name="Exemple Paysages", city="Trois-Rivières")

    assert services == ["Abattage", "Elagage", "Dessouchage", "Aménagement paysager", "Taille de haies & cèdres"]


def test_a_shouted_comma_list_after_a_title_comes_out_in_plain_case() -> None:
    """« GARAGE DE MÉCANIQUE . AIR CLIMATISÉ, FREIN, … » : the title sentence is not a service, the list is."""
    intro = (
        "GARAGE DE MÉCANIQUE AUTOMOBILE . AIR CLIMATISÉ, FREIN,SILENCIEUX, DIRECTION/SUSPENSION, INJECTION/ ÉLECTRICITÉ"
    )

    services = ServiceListReader.services_in(intro, business_name="Garage Exemple", city="Victoriaville")

    assert services == ["Air climatisé", "Frein", "Silencieux", "Direction/suspension", "Injection/électricité"]


def test_a_list_sentence_inside_prose_is_found_and_the_prose_is_not() -> None:
    """Only the sentence that lists the work is read; « Plus de 25 ans d'expérience » is not a service."""
    description = (
        "Paysagiste de formation. Plus de 25 ans d'expérience. Exemple Paysagiste est une petite entreprise basée "
        "à Sion. Dallage, pavage , taille des arbres, mur de pierre, clôture de jardin etc. DEVIS GRATUIT"
    )

    services = ServiceListReader.services_in(description, business_name="Exemple Paysagiste", city="Sion")

    assert services == ["Dallage", "Pavage", "Taille des arbres", "Mur de pierre", "Clôture de jardin"]


def test_the_business_name_in_its_own_list_is_not_a_service() -> None:
    """« Garage Automobiles X, Réparations toutes marques, … » lists three services after the name."""
    intro = "Garage Automobiles Exemple, Réparations toutes marques, auto-location, électricité ..."

    services = ServiceListReader.services_in(intro, business_name="Garage Exemple", city="Payerne")

    assert services == ["Réparations toutes marques", "Auto-location", "Électricité"]


def test_a_company_prefix_is_dropped_from_the_first_service() -> None:
    """« Entreprise de plomberie, chauffage, sanitaire » lists three trades."""
    assert ServiceListReader.services_in("Entreprise de plomberie, chauffage, sanitaire") == [
        "Plomberie",
        "Chauffage",
        "Sanitaire",
    ]


def test_prose_a_truncated_intro_and_a_list_of_towns_give_no_services() -> None:
    """Sentences with commas, a cut intro and a list of places are not service lists."""
    texts = [
        "Nous intervenons à Dijon, Chenôve, Talant et environs pour tous vos travaux.",
        "L'entreprise Exemple, situé à Dijon 21000, vous propose des services d'exploitation de forê...",
        "Dijon • Chenôve • Talant • Quetigny",
    ]

    assert [ServiceListReader.services_in(text, city="Dijon") for text in texts] == [[], [], []]
