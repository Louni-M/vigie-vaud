"""`rattacher(texte, origine)` (ADR 0016), par une table de cas : une ligne par règle, et les faux positifs relevés
par la recherche #47 (`communes-dans-le-grand-conseil`) devenus des cas. Les communes sont celles de
`web/static/communes.json` ; on les compare par leur nom, traduit en n° OFS par ce même fichier."""

import json

import pytest

from rattachement import rattacher
from schema import RACINE

OFS = {}
for _c in json.loads((RACINE / "web/static/communes.json").read_text(encoding="utf-8")):
    OFS[_c["nom"]] = _c["bfs"]


def _noms(texte, origine="titre"):
    par_ofs = {ofs: nom for nom, ofs in OFS.items()}
    trouvees = rattacher(texte, origine)
    assert {c.origine for c in trouvees} <= {origine}
    return [par_ofs[c.ofs] for c in trouvees]


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        # Un nom de commune, tel quel ou sans ses accents.
        ("Sécurité à la Cathédrale de Lausanne", ["Lausanne"]),
        ("Gymnase d'Echallens", ["Echallens"]),
        ("Le nouveau gymnase d’Échallens", ["Echallens"]),
        # Le titre garde l'ordre d'apparition.
        ("Fusion des communes de Mathod et Suscévaz, puis de Lucens et Mathod", ["Mathod", "Suscévaz", "Lucens"]),
        # Un nom n'est pas trouvé dans un autre, ni accolé à un trait d'union.
        ("Couverture photovoltaïque du Centre Blécherette, le Mont-sur-Lausanne", ["Le Mont-sur-Lausanne"]),
        ("Ligne Lausanne-Echallens", []),
        # Les noms à article : avec l'article, ou sa contraction selon le genre.
        ("La fusion de L’Abbaye, Le Chenit et Le Lieu", ["L'Abbaye", "Le Chenit", "Le Lieu"]),
        ("Le couvent du Lieu", ["Le Lieu"]),
        ("Le monastère de l'Abbaye", ["L'Abbaye"]),
        ("Gravière des Bulles, à La Chaux", ["La Chaux (Cossonay)"]),
        ("L'alpage des Chaux, aux Chaux", []),
        ("Un abonnement à la Vaud ID-santé", []),
        ("Sans son article : Chenit", []),
        # Une ancienne commune ou un ancien nom mène à la commune actuelle, une seule fois.
        ("Port du turban au Gymnase d'Yverdon", ["Yverdon-les-Bains"]),
        ("Les caves de Cully et d'Epesses, puis Bourg-en-Lavaux", ["Bourg-en-Lavaux"]),
        ("Le giratoire de Bussigny-près-Lausanne", ["Bussigny"]),
        # Aucun nom n'est banni, sauf l'ancienne commune Mur.
        ("Mur de soutènement et Mur Blanc", []),
        ("Mur poids en béton armé, à Constantine", ["Vully-les-Lacs"]),
        # « St- » et « Ste- » se lisent « Saint- » et « Sainte- ».
        ("Prolongement du tramway de Renens à Villars-Ste-Croix", ["Renens (VD)", "Villars-Sainte-Croix"]),
        ("St-Prex, Ste-Croix et St-Sulpice", ["Saint-Prex", "Sainte-Croix", "Saint-Sulpice (VD)"]),
        # Un nom coupé en fin de ligne par l'extraction d'un PDF est recollé.
        ("Molondin, Montagny-près- Yverdon, Romainmôtier- Envy", ["Molondin", "Montagny-près-Yverdon",
                                                                 "Romainmôtier-Envy"]),
        ("Le nord- est de Lausanne - Morges", ["Lausanne", "Morges"]),
        # Une courte liste de formes usuelles, sans ambiguïté.
        ("La galerie de Cheseaux", ["Cheseaux-sur-Lausanne"]),
        ("Le Conseil communal de Saint-Légier", ["Blonay - Saint-Légier"]),
        # Les formes courtes ambiguës ne sont jamais reconnues.
        ("Jonction Chavannes, Belmont, Corcelles, Romanel et Mont", []),
        # Formules retirées avant l'appariement.
        ("Ainsi adopté, en séance du Conseil d'État, à Lausanne, le 4 octobre 2022.", []),
        ("Château cantonal, 1014 Lausanne", []),
        ("Lausanne, le 4 octobre 2022 (Signé)", []),
        ("Epesses, le 24 novembre 2024. La rapportrice", []),
        ("Article Premier - Principe", []),
        ("Séance de commission, salle du Bicentenaire, place du Château 6 à Lausanne", []),
        # District, région, agglomération : le territoire homonyme n'est pas la commune, ni ceux qu'on lui accole.
        ("Quel est l’impact des gravières du district de Morges ?", []),
        ("Justice de paix du district de Nyon sis rue Jules-Gachet 5 à Nyon", ["Nyon"]),
        ("Districts de Nyon et Morges", []),
        ("Districts Ouest Lausanne, Lausanne, Lavaux-Oron", []),
        ("RDU région Nyon", []),
        ("La région de Nyon", []),
        ("Le plan des mesures OPair de l'agglomération Lausanne - Morges", []),
        # Plaine, rivière : la commune n'a pas d'article, le cours d'eau en a un.
        ("Établissements de la plaine de l’Orbe (EPO)", []),
        ("L'Orbe, ses gorges et... ses déchets?", []),
        ("Contrôle de la qualité de l'eau de L'Orbe supérieure", []),
        ("Le pénitencier de Bochuz et ateliers aux EPO, Orbe", ["Orbe"]),
        ("Le collège du Fey et l'avenue du Fey, à Moudon", ["Moudon"]),
        # Rues, routes et adresses.
        ("Justice de Paix des Côtes-de-Montbenon 8 à Lausanne vers Provence 4 à Lausanne", ["Lausanne"]),
        ("Le Gymnase de Provence, avenue de Provence", []),
        ("Pétition Aménagement du tronçon de la Route de Saint-Cergue", []),
        ("Bien-fonds sis à la Route des Flumeaux 50, commune de Prilly", ["Prilly"]),
        ("Place de la Gare à Lausanne: le canton adhère-t-il au projet ?", ["Lausanne"]),
        ("Jonction entre la RC 601 Lausanne – Berne et la RC 626 Oron – Moudon, sur la commune de Moudon", ["Moudon"]),
        ("La rampe de Lausanne et le chemin du Devin", []),
        # Institutions qui portent le nom d'une commune sans y être.
        ("Licenciement à l’Université de Lausanne", []),
        ("Modifiant la loi sur l'université de Lausanne", []),
        ("L'École polytechnique fédérale de Lausanne", []),
        ("La Haute école d'art et de design de Lausanne (ECAL)", []),
        # Mais un établissement situé dans la commune la nomme bien.
        ("Cartes de vœux du Gymnase de Nyon", ["Nyon"]),
        ("Racisme structurel au sein de la Police de Lausanne", ["Lausanne"]),
        # Raisons sociales et lignes.
        ("Chemin de fer Lausanne - Echallens - Bercher (LEB)", []),
        ("Transports de la région Morges Bière Cossonay (MBC)", []),
        ("Transports Vallée de Joux - Yverdon-les-Bains - Sainte-Croix (TRAVYS)", []),
        # Mots courants.
        ("Cour des comptes – Premier mandat de 6 ans", []),
        ("Au Premier semestre, Premier débat et Premier vice-président", []),
        ("Les communes de La Praz, Premier, Provence et Rances", ["La Praz", "Premier", "Provence", "Rances"]),
        ("Agressions, deal, Morges va-t-elle devenir le nouveau Lausanne ?", ["Morges"]),
        # Homonymes d'un autre canton, et lieux-dits.
        ("Ecublens (FR) et Cugy FR", []),
        ("Le lieu-dit La Chaux de Ste-Croix", ["Sainte-Croix"]),
    ],
)
def test_rattacher(texte, attendu):
    assert _noms(texte) == attendu


def test_un_document_donne_ses_communes_de_la_plus_a_la_moins_mentionnee_avec_leur_origine():
    texte = "La STEP de Tolochenaz reçoit les eaux de Nyon et de Morges ; Nyon et Morges paient, Morges exploite."

    assert [(c.ofs, c.origine) for c in rattacher(texte, "document")] == [
        (OFS["Morges"], "document"),
        (OFS["Nyon"], "document"),
        (OFS["Tolochenaz"], "document"),
    ]
    assert _noms(texte, "titre") == ["Tolochenaz", "Nyon", "Morges"]
