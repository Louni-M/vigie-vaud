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
    ],
)
def test_masquer(titre, attendu):
    assert masquer(titre, ELUS) == (titre if attendu is None else attendu)


# La même table que `web/src/lib/masquage.test.ts` (`masquerNoms`), cas pour cas : sans élu·e connu·e, le cron
# masque comme le site, les auteur·e·s de pétition sans civilité mis à part (une règle des conseils seulement). Un cas
# ajouté d'un côté s'ajoute de l'autre.
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


@pytest.mark.parametrize(("titre", "attendu"), CAS_DU_SITE)
def test_sans_elu_connu_le_cron_masque_comme_le_site(titre, attendu):
    assert masquer(titre) == (titre if attendu is None else attendu)
