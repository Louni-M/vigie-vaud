"""`masquer(titre, élu·e·s connu·e·s)`, la version du cron du masquage du site (`web/src/lib/masquage.ts`), par une
table de cas (spec de J1, « Décisions de test », point 3)."""

import pytest

from masquage import masquer

ELUS = frozenset({"Loris Socchi", "Jean Dupont", "Anne-Laure Métraux"})


@pytest.mark.parametrize(
    ("titre", "attendu"),
    [
        # Un particulier dans un titre de pétition est masqué.
        (
            "Pétition de M. Paul Exemple et consorts (312 signatures) : « Pour un parc à chiens »",
            "Pétition de [particulier] et consorts (312 signatures) : « Pour un parc à chiens »",
        ),
        ("Pétition de Mme et M. Exemple pour un trottoir", "Pétition de [particulier] pour un trottoir"),
        # Comme sur le site : « pour le compte de » un particulier, mais pas d'une entreprise.
        ("Recours pour le compte de Dupuis Marie", "Recours pour le compte de [particulier]"),
        ("Recours pour le compte de Swisscom SA", "Recours pour le compte de Swisscom SA"),
        # Un·e élu·e connu·e est épargné·e, quelle que soit la casse ou l'accentuation de la source.
        ("Postulat de M. Loris SOCCHI : « Nos beaux murs gris». (FIM)", None),
        ("Interpellation de Mme Anne-Laure METRAUX : « Quel avenir ? »", None),
        ("Postulat de MM. Jean Dupont et Loris Socchi : « Des bancs »", None),
        # Un élu et un particulier ensemble : seul le particulier est masqué.
        (
            "Pétition de MM. Jean Dupont et Paul Exemple : « Des bancs »",
            "Pétition de MM. Jean Dupont et [particulier] : « Des bancs »",
        ),
        # Un homonyme partiel n'est ni épargné à tort…
        ("Pétition de M. Pierre Dupont : « Des bancs »", "Pétition de [particulier] : « Des bancs »"),
        ("Pétition de M. Jean Dupontel : « Des bancs »", "Pétition de [particulier] : « Des bancs »"),
        ("Pétition de M. Dupont : « Des bancs »", "Pétition de [particulier] : « Des bancs »"),
        # … ni masqué à tort : sans civilité, un nom propre reste (c'est la règle du site).
        ("Simple question Laurence Cretegny et consorts - Galère La Liberté", None),
        ("Pour une place Jean Dupont à Ouchy", None),
        # Sauf l'auteur·e d'une pétition, que Lausanne nomme sans civilité, dans un ordre ou dans l'autre.
        (
            "Pétition de Exemple Paul et crts déposée le 2 octobre 2026 de : «Un stand sur la place»",
            "Pétition de [particulier] et crts déposée le 2 octobre 2026 de : «Un stand sur la place»",
        ),
        (
            "Pétition de Modèle Julie et crts : «Du bruit au parc»",
            "Pétition de [particulier] et crts : «Du bruit au parc»",
        ),
        (
            "Pétition au CC déposée le 12 mai 2024 de Julie Modèle et crts : «Pour un bus le dimanche»",
            "Pétition au CC déposée le 12 mai 2024 de [particulier] et crts : «Pour un bus le dimanche»",
        ),
        (
            "Dépôt - Pétition déposée le 1er février 2021 de Noël Exemple et Anne Modèle Témoin : «Modérer»",
            "Dépôt - Pétition déposée le 1er février 2021 de [particulier] : «Modérer»",
        ),
        ("Pétition déposée le 9 novembre 2023 de Paul et Luc Exemple : « Un stade »", "Pétition déposée le 9 novembre 2023 de [particulier] : « Un stade »"),
        (
            "Pétition de Exemple Paul et Modèle Julie et crts : « La ligne M2 »",
            "Pétition de [particulier] et crts : « La ligne M2 »",
        ),
        (
            "Communication - réponse à la pétition déposée le 16 novembre 2021 de Julie Témoin et consorts : « Rue »",
            "Communication - réponse à la pétition déposée le 16 novembre 2021 de [particulier] et consorts : « Rue »",
        ),
        ("Pétition de Marc et Lucie Modèle, relative à un conseiller d'État.", "Pétition de [particulier], relative à un conseiller d'État."),
        ("Pétition de P. E. - pour la restitution de mon permis.", "Pétition de [particulier] - pour la restitution de mon permis."),
        ("Pétition de Paul de Montexemple : « Un banc »", "Pétition de [particulier] : « Un banc »"),
        ("Pétition de Paul d'Exemplaire et consorts", "Pétition de [particulier] et consorts"),
        ("Pétition de Témoin Luc", "Pétition de [particulier]"),
        # Un·e élu·e pétitionnaire reste, à côté d'un particulier masqué ; avec sa civilité, on n'y touche plus.
        ("Pétition de Jean Dupont et Paul Exemple : « Des bancs »", "Pétition de Jean Dupont et [particulier] : « Des bancs »"),
        ("Pétition de M. Jean Dupont : « Des bancs »", None),
        # Une entité ou un collectif reste nommé·e.
        ("Pétition au CC déposée le 16 janvier 2024 de Société de Développement du Sud-Ouest : « Un parc »", None),
        ("Pétition déposée le 14 juin 2024 de Habitants de Cour-Contigny : « Un parc »", None),
        ("Pétition de l'Association Lac-Harpe : « Un parc »", None),
        ("Pétition déposée le 8 mars 2022 de Collectif Aubépines : « Un parc »", None),
        # Ce qui suit « Pétition de » sans être un nom ne bouge pas.
        ("Pétition de soutien à une famille.", None),
        ("Pétition déposée le 8 mars 2022 de Montelly vit ! : « Non à l'APEMS »", None),
        # Les titres sans nom ne bougent pas.
        ("Covid 2020 six ans pour revenir en arrière", None),
        # Les coordonnées qui suivent un particulier masqué sont masquées avec lui : adresse et téléphone.
        (
            "Pétition déposée le 27 août 2024 de Exemple Paul - Chemin des Lilas 46 - 1004 Lausanne - 079 000 00 00 : "
            "«Pétition au CC de Exemple Paul - Respect de la vie des animaux»",
            "Pétition déposée le 27 août 2024 de [particulier] - [coordonnées] : «Pétition au CC de [particulier] - "
            "Respect de la vie des animaux»",
        ),
        (
            "Pétition au CC déposée le 29 août 2023 de Mme Paule Exemple - Chemin des Lilas 9 - 1007 Lausanne : "
            "«Comité \"Non au transit vélos\" (par Mme Exemple Paule et crts) - Une zone de rencontre»",
            "Pétition au CC déposée le 29 août 2023 de [particulier] - [coordonnées] : "
            "«Comité \"Non au transit vélos\" (par [particulier] et crts) - Une zone de rencontre»",
        ),
        ("Pétition de Témoin Luc, av. de la Gare 4b, 1003 Lausanne", "Pétition de [particulier], [coordonnées]"),
        ("Pétition de Témoin Luc - 1004 Lausanne : « Un banc »", "Pétition de [particulier] - [coordonnées] : « Un banc »"),
        ("Recours pour le compte de Dupuis Marie, rue du Port 3", "Recours pour le compte de [particulier], [coordonnées]"),
        # Un téléphone ou un courriel est masqué partout, quelle qu'en soit la forme.
        ("Renseignements au 021 000 00 00", "Renseignements au [coordonnées]"),
        ("Pétition de M. Exemple (+41 79 000 00 00)", "Pétition de [particulier] ([coordonnées])"),
        ("Contact : 0041 21 000 00 00 ou 079/000.00.00", "Contact : [coordonnées] ou [coordonnées]"),
        ("Pétition de Témoin Luc - luc.temoin@exemple.ch : « Un banc »", "Pétition de [particulier] - [coordonnées] : « Un banc »"),
        # L'adresse d'une entité, ou d'un immeuble sujet de l'Objet, reste ; un nombre n'est pas un téléphone.
        (
            "Pétition déposée le 24 mai 2022 de Centre socioculturel de Bellevaux - Chemin d'Entre-Bois 10 - 1018 "
            "Lausanne : «Pour la rénovation du terrain de foot»",
            None,
        ),
        ("Préavis N° 2023/44 - Chemin de la Colline 6-8 - Vente du bien-fonds n° 7'536", None),
        ("Interpellation urgente de M. Paul Exemple : «Rue de Genève 85 : adresse fictive»", "Interpellation urgente de [particulier] : «Rue de Genève 85 : adresse fictive»"),
        ("Pétition Pour des aménagements de la route du Village, 1295 Mies", None),
        ("Les Dailles - Epalinges, biens-fonds nos 272 - 344 - 366, vente de terrains", None),
        # Les titres de documents : une URL (le Grand Conseil en met en titre) ou un nom de fichier restent ; un nom de
        # fichier qui commence comme un titre de pétition est masqué comme lui.
        ("https://www.exemple.ch/fr/regions/vaud/12345678-un-article-de-presse.html", None),
        ("17_17_mai_reponse_interpellation_exemple_casino.pdf v1.0", None),
        ("Pétition de Exemple Paul et crts - Route des Lilas 30kmh.pdf", "Pétition de [particulier] et crts - Route des Lilas 30kmh.pdf"),
    ],
)
def test_masquer(titre, attendu):
    assert masquer(titre, ELUS) == (titre if attendu is None else attendu)


# La même table que `web/src/lib/masquage.test.ts` (`masquerNoms`), cas pour cas : sans élu·e connu·e, le cron
# masque comme le site, sauf là où une règle des conseils seulement s'en écarte (`ECARTS_DU_CRON`) : les auteur·e·s de
# pétition et les noms après un déclencheur, masqué·e·s sans civilité. Un cas ajouté d'un côté s'ajoute de l'autre.
CAS_DU_SITE = [
    ("Construction d’une villa pour le compte de Dupont Jean", "Construction d’une villa pour le compte de [particulier]"),
    ("Recours pour le compte de Swisscom SA", None),
    ("Transformation pour le compte de Immobilière Rive S.A.", "Transformation pour le compte de Immobilière Rive SA"),
    (
        "Pétition de M. Paul Exemple et consorts (312 signatures) : « Pour un parc à chiens »",
        "Pétition de [particulier] et consorts (312 signatures) : « Pour un parc à chiens »",
    ),
    ("Pétition de Mme et M. Exemple pour un trottoir", "Pétition de [particulier] pour un trottoir"),
    ("Pétition de Madame Exemple", "Pétition de [particulier]"),
    ("Postulat de M. Loris SOCCHI : « Nos beaux murs gris»", "Postulat de [particulier] : « Nos beaux murs gris»"),
    ("Postulat de MM. Jean Dupont et Loris Socchi : « Des bancs »", "Postulat de [particulier] : « Des bancs »"),
    ("Interpellation de Mme Anne-Laure Métraux : « Quel avenir ? »", "Interpellation de [particulier] : « Quel avenir ? »"),
    ("Villa pour le compte de M. J.-P. Martin", "Villa pour le compte de [particulier]"),
    ("Agrandissement pour le compte de Commune de Lutry", None),
    ("Abri pour le compte de la Fondation Les Oliviers", None),
    ("Rénovation pour le compte de l’Hoirie Favre", None),
    ("Pose d’un velux pour compte d’Ébéniste Rochat S.à r.l.", "Pose d’un velux pour compte d’Ébéniste Rochat Sàrl"),
    ("Garage pour le compte de Rossi Marco - Bianchi Anna", "Garage pour le compte de [particulier] - [particulier]"),
    ("Garage pour le compte de Rossi Marco, architecte", "Garage pour le compte de [particulier], architecte"),
    ("Couvert pour le compte de Dupont Jean avec garage", "Couvert pour le compte de [particulier] avec garage"),
    ("Recours pour le compte des Époux Rochat", "Recours pour le compte des [particulier]"),
    ("Simple question Laurence Cretegny et consorts - Galère La Liberté", None),
    ("Covid 2020 six ans pour revenir en arrière", None),
]


# Après « hoirie », un nom est masqué dans les titres des conseils ; le site, qui ne masque que les permis, y voit une
# entité.
ECARTS_DU_CRON = {"Rénovation pour le compte de l’Hoirie Favre": "Rénovation pour le compte de l’Hoirie [particulier]"}


@pytest.mark.parametrize(("titre", "attendu"), CAS_DU_SITE)
def test_sans_elu_connu_le_cron_masque_comme_le_site(titre, attendu):
    attendu = ECARTS_DU_CRON.get(titre, attendu)
    assert masquer(titre) == (titre if attendu is None else attendu)


# Les pétitionnaires que la source connaît (prénom, nom), masqué·e·s dans les textes de leur pétition sous toutes les
# formes que Lausanne leur donne : nom de fichier en snake_case, sans civilité ni « Pétition de », nom seul.
PETITIONNAIRES = [("Paul", "Exemple"), ("Zoé", "Modèle"), ("Ariane", "Exemple-Témoin"), ("Léa", "Do")]


@pytest.mark.parametrize(
    ("titre", "attendu"),
    [
        ("2025_08_rp_petition_paul_exemple_parc_a_chiens.pdf v1.0", "2025_08_rp_petition_[particulier]_parc_a_chiens.pdf v1.0"),
        ("39_24_nov_cc_rep_petition_exemple_parc.pdf v1.0", "39_24_nov_cc_rep_petition_[particulier]_parc.pdf v1.0"),
        ("COPET_rapport pétition Exemple.pdf", "COPET_rapport pétition [particulier].pdf"),
        ("Pétition Exemple Paul_toilettes du parc", "Pétition [particulier]_toilettes du parc"),
        (
            "Pétition du Collectif des Lilas par Exemple Paul et crts - Un parc",
            "Pétition du Collectif des Lilas par [particulier] et crts - Un parc",
        ),
        (
            "Réponse à la pétition de l'Association des Lilas (Paul Exemple)",
            "Réponse à la pétition de l'Association des Lilas ([particulier])",
        ),
        ("Pétition Exemple Paul et Exemple Marc - Un banc", "Pétition [particulier] et [particulier] Marc - Un banc"),
        # À la casse et aux accents près, nom composé compris.
        ("Pétition MODELE Zoé - Un banc", "Pétition [particulier] - Un banc"),
        ("30_11_sept_petition_zoe_modele_banc.pdf v1.0", "30_11_sept_petition_[particulier]_banc.pdf v1.0"),
        ("Pétition Exemple Témoin Ariane - Un banc", "Pétition [particulier] - Un banc"),
        ("petition_exemple_temoin_banc.pdf", "petition_[particulier]_banc.pdf"),
        # Ses coordonnées le suivent.
        ("Pétition Exemple Paul - Chemin des Lilas 2 - 1000 Lausanne", "Pétition [particulier] - [coordonnées]"),
        # Un mot qui contient le nom n'est pas le nom ; un nom de deux lettres n'est masqué qu'avec le prénom.
        ("Rapport sur l'exemplaire du plan", None),
        ("Pétition Do Léa - Un banc", "Pétition [particulier] - Un banc"),
        ("do_re_mi.pdf", None),
    ],
)
def test_les_petitionnaires_connus_sont_masques_sous_toutes_leurs_formes(titre, attendu):
    assert masquer(titre, ELUS, PETITIONNAIRES) == (titre if attendu is None else attendu)


def test_un_petitionnaire_elu_connu_reste_et_son_nom_de_famille_seul_aussi():
    # Jean Dupont est un élu connu : il reste. Marc Dupont n'en est pas un : il est masqué avec son prénom, mais
    # « Dupont » seul peut être l'élu (« postulat_dupont ») et reste.
    petitionnaires = [("Jean", "Dupont"), ("Marc", "Dupont")]
    assert masquer("petition_jean_dupont_bancs.pdf", ELUS, petitionnaires) == "petition_jean_dupont_bancs.pdf"
    assert (
        masquer("rp_petition_marc_dupont_postulat_dupont.pdf", ELUS, petitionnaires)
        == "rp_petition_[particulier]_postulat_dupont.pdf"
    )


# Un nom partiel après une civilité (ADR 0007, pour tous les conseils, pas pour le site) : il reste quand un·e élu·e
# connu·e porte ce nom de famille, avec la même initiale s'il y en a une, et qu'un contexte d'élu·e le précède ; sinon,
# il est masqué (dans un village, un opposant porte souvent le nom d'un·e élu·e).
@pytest.mark.parametrize(
    ("titre", "attendu"),
    [
        # Contexte d'élu·e et homonyme connu·e, sans initiale : le nom reste.
        ("Préavis 12/2026 - Réfection du collège (Rapp. M. Socchi)", None),
        ("Interpellation urgente de Mme Métraux : « Quel avenir pour la grande salle ? »", None),
        ("Réponse de la Municipalité à la motion de M. Dupont", None),
        ("Simple question de M. SOCCHI sur les horaires du bus", None),
        ("Rapport du rapporteur, M. Dupont, sur le budget 2027", None),
        ("Démission de la conseillère communale Mme Métraux", None),
        ("Postulat 2026/04 de M. Dupont : « Des bancs »", None),
        ("Réfection du chemin du Stand, M. Dupont et consorts", None),
        # Avec l'initiale de l'élu·e : le nom reste ; avec une autre initiale, c'est quelqu'un d'autre.
        ("Interpellation de M. J. Dupont : « Le parking »", None),
        ("Préavis 13/2026 - Budget (Rapp. Mme A.-L. Métraux)", None),
        ("Préavis 13/2026 - Budget (Rapp. Mme A. Métraux)", None),
        ("Interpellation de M. P. Dupont : « Le parking »", "Interpellation de [particulier] : « Le parking »"),
        ("Préavis 13/2026 - Budget (Rapp. Mme L.-A. Métraux)", "Préavis 13/2026 - Budget (Rapp. [particulier])"),
        # Contexte d'élu·e sans homonyme connu·e : masqué.
        ("Préavis 14/2026 - Éclairage public (Rapp. M. Exemple)", "Préavis 14/2026 - Éclairage public (Rapp. [particulier])"),
        ("Interpellation de M. C. Modèle : « Le parking »", "Interpellation de [particulier] : « Le parking »"),
        # Homonyme connu·e sans contexte d'élu·e : masqué, c'est peut-être un opposant du village.
        ("Opposition de M. Dupont au plan de quartier", "Opposition de [particulier] au plan de quartier"),
        ("Vente de la parcelle 412 à M. J. Socchi", "Vente de la parcelle 412 à [particulier]"),
        ("Pétition de M. Dupont et consorts : « Des bancs »", "Pétition de [particulier] et consorts : « Des bancs »"),
        (
            "Postulat de M. Paul Exemple : « La lettre de M. Dupont »",
            "Postulat de [particulier] : « La lettre de [particulier] »",
        ),
        # Plusieurs noms partiels : seul l'inconnu est masqué.
        ("Postulat de MM. Dupont et Modèle : « Des bancs »", "Postulat de MM. Dupont et [particulier] : « Des bancs »"),
        # Un prénom n'est pas un nom de famille.
        ("Interpellation de M. Loris : « Le parking »", "Interpellation de [particulier] : « Le parking »"),
    ],
)
def test_un_nom_partiel_ne_reste_qu_avec_un_contexte_d_elu_et_un_homonyme_connu(titre, attendu):
    assert masquer(titre, ELUS) == (titre if attendu is None else attendu)


# Les déclencheurs sans civilité (ADR 0007, pour tous les conseils, pas pour le site) : après « succession de »,
# « hoirie », « feu », « legs de », « opposition de » ou « acquéreur », un nom est masqué comme après une civilité,
# sauf entité ou élu·e connu·e.
@pytest.mark.parametrize(
    ("titre", "attendu"),
    [
        # Succession de
        ("Préavis 15/2026 - Succession de Paul Exemple : acceptation", "Préavis 15/2026 - Succession de [particulier] : acceptation"),
        ("Acceptation de la succession d'Albert Modèle", "Acceptation de la succession d'[particulier]"),
        ("Succession de Swisscom SA : reprise du bail", None),
        ("Succession de Jean Dupont à la présidence du conseil", None),
        ("Succession de Mme Zoé Modèle : acceptation", "Succession de [particulier] : acceptation"),
        # Hoirie
        ("Hoirie Exemple - vente de la parcelle 88", "Hoirie [particulier] - vente de la parcelle 88"),
        ("Accord avec l'hoirie de feu Paul Exemple", "Accord avec l'hoirie de feu [particulier]"),
        ("Hoirie Rive Immobilière SA : vente de la parcelle 88", None),
        ("Rachat de la parcelle 88 à l'hoirie Loris Socchi", None),
        # Feu
        ("Don en mémoire de feu Paul Exemple", "Don en mémoire de feu [particulier]"),
        ("Fonds de feue Zoé Modèle pour les aînés", "Fonds de feue [particulier] pour les aînés"),
        ("Archives de feu Société de Musique L'Écho", None),
        ("Hommage à feu Jean Dupont, ancien syndic", None),
        ("Feu d'artifice du 1er Août et feux de signalisation", None),
        # Legs de
        ("Legs de Zoé Modèle à la Commune", "Legs de [particulier] à la Commune"),
        ("Acceptation du legs d'Exemple Paul", "Acceptation du legs d'[particulier]"),
        ("Legs de Fondation Exemple pour la bibliothèque", None),
        ("Legs de Loris Socchi à la bibliothèque", None),
        # Opposition de
        ("Levée de l'opposition de Exemple Paul et Modèle Zoé", "Levée de l'opposition de [particulier]"),
        ("Oppositions de Jean Dupont et Paul Exemple au plan", "Oppositions de Jean Dupont et [particulier] au plan"),
        (
            "Opposition de Paul Exemple, Chemin des Lilas 2, 1000 Exempleville",
            "Opposition de [particulier], [coordonnées]",
        ),
        ("Opposition de Pro Natura au plan de quartier", None),
        ("Opposition de Swisscom SA à l'antenne", None),
        ("Opposition de Anne-Laure Métraux au plan de quartier", None),
        # Acquéreur
        ("Vente de la parcelle 210, acquéreur Paul Exemple", "Vente de la parcelle 210, acquéreur [particulier]"),
        ("Vente de la parcelle 211 - acquéreurs : Paul et Zoé Exemple", "Vente de la parcelle 211 - acquéreurs : [particulier]"),
        ("Vente de la parcelle 212, acquéreuse Zoé Modèle", "Vente de la parcelle 212, acquéreuse [particulier]"),
        ("Vente de la parcelle 213, acquéreur Coopérative Les Lilas", None),
        ("Vente de la parcelle 214, acquéreur Jean Dupont", None),
    ],
)
def test_un_nom_sans_civilite_est_masque_apres_un_declencheur(titre, attendu):
    assert masquer(titre, ELUS) == (titre if attendu is None else attendu)
