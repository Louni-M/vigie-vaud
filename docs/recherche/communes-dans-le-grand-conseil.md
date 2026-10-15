# Où et combien de fois les Objets du Grand Conseil nomment-ils une commune ?

Recherche du ticket [#47](https://github.com/Louni-M/vigie-vaud/issues/47), enfant de la carte
[#43](https://github.com/Louni-M/vigie-vaud/issues/43) (J1 Conseils). Mesures faites le 15 octobre 2026. Ce document
rapporte des faits et des chiffres ; la règle de Rattachement des Objets se décide dans le ticket #50.

## Réponse courte

- **Où** : l'API OpenParlData ne donne pour chaque Objet qu'un **titre** (`title`) et un titre long (`title_long` =
  type + auteur·es + titre). Le corps de texte n'existe dans l'API que par les **documents** liés (`/v1/docs`,
  champ `text` extrait des PDF), et seulement pour **16 %** des Objets récents (240 sur 1 470), surtout des
  décrets et des réponses du Conseil d'État. Le « Texte déposé » des interpellations, postulats, motions et
  questions est sur la page vd.ch de l'Objet (`url_external`), pas dans l'API ; `/v1/texts` ne contient que
  7 textes vaudois en tout.
- **Combien, par le titre** : sur 1 470 Objets (15 octobre 2024 – 6 octobre 2026), **84 titres (5,7 %)** contiennent
  au moins un nom de la liste ; après vérification à la main, **73 Objets (5,0 %)** nomment vraiment au moins une
  commune. Ces 73 Objets en citent presque toujours une seule (63 Objets), parfois 2 (7) ou 3 (3).
  50 communes différentes ; Lausanne en tête (16 Objets), puis Renens (5).
- **Combien, par les documents de l'API** : sur les 240 Objets qui en ont, 216 (90 %) contiennent un nom, mais
  91 seulement à cause de formules (« en séance du Conseil d'État, à Lausanne », « Université de Lausanne »,
  « Article premier »…). Hors formules : 125 Objets (52 %), dont 38 citent 6 communes ou plus.
- **Combien, par la page vd.ch** (hors API, 300 Objets tirés au hasard) : le « Texte déposé » (215 pages) nomme
  une commune dans 45 cas (21 %), dont 41 que le titre ne nomme pas ; la transcription du débat (184 pages) dans
  49 cas (27 %), souvent parce qu'un·e élu·e déclare ses intérêts (« syndique de la commune de Bussigny »). Sur
  ces 300 Objets, le titre en rattache 12, le titre ou la page 78.
- **Précision de l'appariement naïf** (liste des 300 communes + anciennes communes et anciens noms, voir annexe) :
  **83 %** des mentions justes dans les titres (94 sur 113, 2 cas limites, 17 faux positifs) ; **88 %** dans un
  échantillon de 100 mentions des documents, une fois les formules retirées (environ 80 % en les comptant) ;
  **88 %** aussi dans un échantillon de 100 mentions des pages vd.ch.
- **Faux positifs, dans l'ordre** : mentions qui ne désignent pas la commune (district homonyme, rivière ou plaine
  de l'Orbe, Université de Lausanne, rue ou route, nom d'entreprise de transport) ; formules répétées des
  documents (« en séance du Conseil d'État, à Lausanne », lieu de signature des rapports de commission) ; noms
  qui sont aussi des mots courants (Premier, Mur, Provence). S'y ajoutent, dans les débats, des mentions justes
  mais hors sujet (l'élu·e qui déclare sa commune). Les noms ambigus de l'ADR 0009 (Belmont, Mont-sur-…,
  Corcelles…) ne produisent **aucun** faux positif sous leur nom complet ; leurs formes courtes (« Cheseaux »,
  « Chavannes », « Belmont ») ne sont simplement pas reconnues. Les anciennes communes et anciens noms sont rares
  dans les titres (1 mention, « Yverdon ») et presque toujours justes dans les documents (sauf « Mur »).

## Source et échantillon

- API : `https://api.openparldata.ch/v1/` (CC BY 4.0, « Source: OpenParlData.ch »), Grand Conseil vaudois
  `body_key=VD` (body 272). Les filtres de champ passent en paramètre de requête (`body_key=VD`,
  `parent_type=affair`) ; `sort_by=-begin_date`, `fields=…`, `limit` jusqu'à 1 000 (spécification :
  `https://api.openparldata.ch/openapi.json`).
- `GET /v1/affairs/?body_key=VD` : **8 338 Objets** (2008 à 2026). Échantillon : les **1 470 Objets** dont
  `begin_date` est entre le 15 octobre 2024 et le 6 octobre 2026 (dernier Objet présent le jour de la mesure).
- Types dans l'échantillon : Interpellation 334, Question orale 288, Simple question 229, Motion 154,
  Décret/Loi 143, Postulat 132, Recours de compétence 54, Rapport 34, Résolution 28, Détermination 21,
  Pétition 18, autres 39.

## Où se trouve le nom

| Endroit | Ce qu'on y trouve | Couverture dans l'échantillon |
| --- | --- | --- |
| `title` (API) | le titre de l'Objet | 1 470 / 1 470 |
| `title_long` (API) | « Type Auteur·e et consorts au nom de … - titre. » | 1 470 / 1 470 ; n'ajoute au titre que des noms de district : sur les 8 338 Objets, 7 noms trouvés dans la partie auteur·es, dont 5 districts ou arrondissements (« députés du district de Morges »…) et 2 bouts de titre mal découpés ; aucun nom d'élu·e pris pour une commune |
| `/v1/affairs/{id}/texts` | texte déposé | 7 textes pour tout VD : inutilisable |
| `/v1/docs` (`parent_type=affair`, champ `text`) | texte extrait des PDF de `sieldocs.vd.ch` (EMPD, réponses du Conseil d'État) et quelques pages vd.ch | 1 073 documents pour 683 Objets, mais 588 sont des vidéos (sonomix) et 167 des liens (presse…) : **297 documents textuels pour 240 Objets (16 %)** : Décret/Loi 95, Simple question 65, Interpellation 59, Consultation 8, Postulat 7, autres 6 |
| page vd.ch (`url_external`) | « Texte déposé » en HTML (interpellations, questions, motions, postulats…), liens vers des documents `sieldocs.vd.ch` (rapports de commission…) | hors API ; voir plus bas |

Aucun champ géographique (commune, district) n'existe sur les Objets.

## Dans les titres

Appariement sur les 1 470 titres, puis lecture de chacune des 113 mentions (et des 3 mentions des titres longs).

- **84 Objets** (5,7 %) avec au moins un nom trouvé ; 113 mentions ; distribution brute du nombre de communes
  distinctes par Objet : 1 → 71, 2 → 9, 3 → 4 ; au plus 5 mentions dans un même titre (25_LEG_18, Moudon).
- Après vérification : **73 Objets (5,0 %)** avec au moins une commune juste ; 101 paires (Objet, commune) dont
  84 justes, 2 limites, 15 fausses ; 11 Objets n'ont **que** des faux positifs.
- Communes justes par Objet : 1 → 63, 2 → 7, 3 → 3.
- Communes les plus citées (Objets, après vérification) : Lausanne 16, Renens 5, Ecublens 3, Leysin 3, Nyon 3,
  Orbe 3, Moudon 3, puis Vallorbe, Lucens, Chavornay, Chavannes-près-Renens, Le Chenit, Yverdon-les-Bains,
  Crissier (2 chacune). 50 communes différentes en deux ans.
- Par type d'Objet (titres avec au moins un nom trouvé) : Décret/Loi 33 / 143 (23 %), Pétition 4 / 18 (22 %),
  Interpellation 20 / 334 (6 %), Simple question 11 / 229 (5 %), Question orale 9 / 288 (3 %), Postulat 3 / 132
  (2 %), Motion 2 / 154 (1 %), Recours de compétence 1 / 54, Rapport 1 / 34, aucun pour les 99 autres.
  Les EMPD situent leur objet (« … à Orbe », « sur le territoire des communes de … ») ; les décrets de fusion
  nomment toutes les communes concernées.

### Faux positifs des titres (17 mentions sur 113)

| Catégorie | Mentions | Exemples |
| --- | --- | --- |
| District homonyme | 4 | « district de Nyon » (26_INT_123, 25_LEG_105), « district de Lausanne », « district de Morges » |
| Rivière ou plaine homonyme | 4 | « L'Orbe supérieure », « L'Orbe, ses gorges », « plaine de l'Orbe » (×2, EPO) |
| Institution | 3 | « Université de Lausanne » (×3 ; l'UNIL est à Chavannes-près-Renens et Ecublens) |
| Rue ou route | 4 | « vers Provence 4 à Lausanne » (avenue de Provence), « Route de Saint-Cergue », « RC 601 Lausanne - Berne », « RC 626 Oron - Moudon » |
| Mot courant | 1 | « Premier mandat de 6 ans » (Premier) |
| Figure de style | 1 | « Morges va-t-elle devenir le nouveau Lausanne ? » |
| Limite (non compté faux) | 2 | « Ligne CFF Lausanne - Payerne » |

Aucun faux positif des titres ne vient des noms ambigus de l'ADR 0009, ni d'une ancienne commune ou d'un ancien
nom (la seule mention de ce type, « Gymnase d'Yverdon », est juste). Les 3 mentions du titre long hors titre sont
toutes des districts ou arrondissements (« au nom des députés du district de Morges »).

### Ce que les titres nomment sans que la liste le reconnaisse

- Formes courtes ou abrégées : « jonction Chavannes » (×2), « galerie de Cheseaux », « Villars-Ste-Croix ».
- Localités et lieux-dits qui ne sont pas des communes : La Sallaz, Malley, Dorigny (6 Objets n'ont pas d'autre
  nom), Clarens, Le Sentier, Les Mosses, Blécherette, Bourdonnette, Croix-du-Péage, Bochuz, Marchairuz.
- Régions : 25 titres nomment une région (Ouest lausannois, Riviera, Chablais, Broye, Nord vaudois, Vallée de
  Joux, Gros-de-Vaud, agglomération…), dont **19 sans aucun nom de commune**.

## Dans les documents de l'API

Appariement sur le texte des 297 documents textuels (240 Objets).

- Brut : 216 Objets sur 240 (90 %) avec au moins un nom, 3 393 mentions, jusqu'à 228 mentions pour un seul Objet.
- **Formules** repérées à la lecture des contextes (316 mentions, toutes fausses) : signature « en séance du
  Conseil d'État, à Lausanne, le … » (130), « Université de Lausanne » (64), adresse postale « 1014 Lausanne » (32),
  « district de … » (31), « Article premier » (30, écrit « Article Premier »), « rue / route / avenue de … » (29).
  91 Objets ne sont rattachés que par ces formules.
- **Hors formules : 125 Objets sur 240 (52 %)**. Communes distinctes par Objet : 1 → 47, 2 → 15, 3 à 5 → 25,
  6 à 19 → 32, 20 et plus → 6 (listes : décret de fusion de la Vallée de Joux qui énumère les communes du district
  du Jura-Nord vaudois, tableaux de routes cantonales, liste des STEP…).
- Communes les plus citées hors formules (Objets) : Lausanne 76, Yverdon-les-Bains 25, Nyon 22, Morges 21,
  Renens 19, Aigle 17, Payerne 16, Echallens 12, Moudon 12, Orbe 12.
- Apport par rapport au titre, sur ces 240 Objets : le titre en rattache 31, le corps hors formules 125, l'union
  126 ; **95 Objets ne sont rattachés que par le corps** (Décret/Loi 36, Interpellation 27, Simple question 18,
  Consultation 8, autres 6).

### Précision sur 100 mentions tirées au hasard (hors formules)

88 justes, 12 fausses :

| Catégorie | Mentions | Exemples |
| --- | --- | --- |
| District ou région homonyme | 4 | « Districts de Nyon et Morges », « Districts Ouest Lausanne, Lausanne, … », « RDU région Nyon », « Plaine de l'Orbe » |
| Nom d'entreprise de transport | 2 | « Chemin de fer Lausanne - Echallens - Bercher » (LEB) |
| Institution hors de la commune | 1 | « Haute école d'art et de design de Lausanne (ECAL) », à Renens |
| Mot courant | 2 | « Premier semestre », « Mur Blanc » |
| Homonyme hors de la commune | 1 | « La Chaux de Ste-Croix » (lieu-dit, pas La Chaux (Cossonay)) |
| Nom de famille | 1 | « Aymée de Villarzel » |
| Lieu de signature | 1 | « Lausanne, le 4 octobre 2022 (Signé) Kilian Duggan » |

9 des 100 mentions justes sont dans des énumérations (liste des communes d'un district) : elles désignent bien
la commune, mais ne disent pas que l'Objet la concerne.

### Noms à risque relevés dans tous les documents

- **Premier** : 42 mentions, toutes fausses sauf 2 dans la liste des communes du district (« Article Premier »,
  « Premier semestre »).
- **Mur** (ancienne commune, Vully-les-Lacs) : 7 mentions, toutes fausses (« Mur poids en béton armé », « Mur de
  soutènement », « Mur Blanc »).
- **Provence** : 21 mentions, 19 fausses (avenue de Provence et Gymnase de Provence, à Lausanne).
- **Fey** : 3 fausses sur 4 (avenue et collège du Fey, à Moudon).
- **Bercher** et **Sainte-Croix** dans des raisons sociales (LEB, TRAVYS) ; **La Chaux** pour La Chaux de
  Sainte-Croix (2) ; **Ecublens (FR)** et **Cugy** côté fribourgeois (1 chacun) : homonymes d'autres cantons.
- Justes malgré le risque : Bassins, Apples, Roche, Mex, Assens, Lully, Noville, Vich, Mies, Saint-Sulpice,
  Le Lieu, Villeneuve.

### Anciennes communes et anciens noms

Dans les documents (hors formules) : 107 mentions d'anciennes communes et 88 d'anciens noms. « Yverdon » (84) est
la forme courte usuelle d'Yverdon-les-Bains ; Cully, Grandvaux, Palézieux, Thierrens, Denezy, Carrouge, Sugnens,
Apples, Châtillens… désignent des localités qui existent toujours, et la liste les mène à la bonne commune
actuelle. Seul **Mur** (7) donne des faux positifs. « Blonay » (17) apparaît aussi quand le PDF coupe
« Blonay - Saint- Légier » : la commune reste juste.

### Ce que les documents nomment sans que la liste le reconnaisse

Formes courtes ou abrégées non comptées : Cheseaux 71, Villars-Ste-Croix 20, St-Sulpice 6, Saint-Légier 5,
Romanel 5, Ste-Croix 4, Chavannes 4, St-Cergue 3, St-Barthélemy 2, Belmont 2, St-Prex 1. L'extraction de certains
PDF espace les lettres (« Re ne ns , Pully, Prangins , Che se aux-Nore az »), ce qui les rend invisibles.

## Sur la page vd.ch de l'Objet (hors API)

300 Objets tirés au hasard dans l'échantillon (graine 47 ; Interpellation 62, Question orale 54, Simple
question 51, Motion 37, Décret/Loi 34, Postulat 21, Recours de compétence 12, autres 29), page `url_external`
téléchargée et réduite à son texte.

- Une page compte, dans l'ordre : l'en-tête (numéro, type, auteur·es, titre, séance), le **Texte déposé**, la
  conclusion, la liste des **Documents** (liens `sieldocs.vd.ch`), les **Transcriptions** du débat.
- Le Texte déposé est présent sur 215 pages : toutes les questions orales, simples questions, motions,
  postulats, résolutions et déterminations, 43 interpellations sur 62 (pour les 19 autres, `url_external` mène
  au point de la réponse du Conseil d'État, par exemple 25_INT_11 vers 25_REP_27) ; jamais pour les décrets,
  recours de compétence, rapports, grâces et pétitions. La transcription est présente sur 184 pages.
- Page entière (après l'en-tête) : 80 Objets sur 300 avec un nom ; formules (Université de Lausanne 14, district
  10, rue 3) ; hors formules 75. Le titre en rattache 12, la page hors formules 75, l'union 78 : **66 Objets ne
  sont rattachés que par la page**.
- **Texte déposé seul** : 45 Objets sur 215 (21 %), en retirant Premier, Université de Lausanne et districts ;
  communes distinctes par Objet : 1 → 30, 2 → 6, 3 → 3, 4 → 1, 5 → 3, 6 et plus → 2 ; Lausanne 20, Morges 4,
  Renens 4, Nyon 3, Yverdon-les-Bains 3. 41 de ces 45 Objets n'ont pas de commune dans le titre.
- **Transcription seule** : 49 Objets sur 184 (27 %) ; Lausanne 22, Bussigny 4, Yverdon-les-Bains 4, Aigle 4.

Précision sur 100 mentions tirées au hasard (page entière, hors formules) : **88 justes, 12 fausses** —
« Premier débat », « Premier vice-président » (5) ; « loi sur l'université de Lausanne », « École polytechnique
fédérale de Lausanne » (2) ; « Transports de la région Morges Bière Cossonay » (2) ; « plaine de l'Orbe » (1) ;
« Région de Nyon » (1) ; « la Vaud ID-santé », lu comme Le Vaud (1). Parmi les 88 justes, **10 désignent bien
la commune mais pas le sujet de l'Objet** : déclarations d'intérêts et présentations d'élu·es dans le débat
(« je suis syndique de la commune de Bussigny », « municipal à Aigle », « le député UDC de Villeneuve »).

### Les documents liés depuis la page

Sur 50 autres pages tirées au hasard (graine 4747), 27 lient au moins un document `sieldocs.vd.ch` (58 en tout),
dont **40 absents de l'API** (pour 27 Objets) : le Texte déposé en PDF (doublon de la page), les **rapports de
commission** (majorité et minorité) et quelques réponses du Conseil d'État. Lecture de 15 de ces PDF
(`pdftotext`) :

- les rapports de commission ajoutent leurs propres formules : lieu de signature du rapporteur ou de la
  rapporteuse (« Epesses, le 24 novembre 2024 », « Mathod, le 22 avril 2026 »), lieu de séance (« salle du
  Bicentenaire, place du Château 6 à Lausanne ») ;
- l'article contracté fait lire « aux Chaux », « l'alpage des Chaux » (lieu-dit de Gryon) comme La Chaux
  (Cossonay) ;
- les Textes déposés en PDF reprennent le texte de la page et ses communes ;
- les réponses du Conseil d'État en PDF ont les mêmes formules que celles de l'API (« en séance du Conseil
  d'État, à Lausanne », « Université de Lausanne »).

## Méthode et limites

- Appariement : script de l'annexe, sans liste d'exclusions, pour mesurer le comportement brut. Il ignore la
  casse de l'article mais pas celle du nom, plie accents et ligatures, et exige une frontière de mot sans trait
  d'union (« Lausanne » n'est pas trouvé dans « Le Mont-sur-Lausanne »).
- Vérification : toutes les mentions des titres et des titres longs lues une à une ; pour les documents de l'API
  et pour les pages vd.ch, un tirage aléatoire de 100 mentions chacun (graine 47) après retrait des formules,
  plus la lecture de toutes les mentions des noms à risque dans les documents. Une mention est « juste » si elle
  désigne le territoire de la commune (lieu, autorité communale, établissement situé dans la commune), même quand
  l'Objet n'en parle qu'en passant.
- Le rappel n'est pas mesuré de façon systématique : les formes courtes, localités et régions relevées ci-dessus
  en donnent l'ordre de grandeur.
- Échantillon : deux ans d'une seule législature ; les documents de l'API couvrent surtout les décrets et les
  réponses du Conseil d'État.

## Annexe : script d'appariement

Les autres scripts (téléchargement, comptes, vérification) n'ont servi qu'une fois ; ils suivent les requêtes
décrites plus haut.

```python
"""Appariement naïf des noms de communes vaudoises dans un texte (recherche #47).

Volontairement simple : c'est l'outil de mesure, pas la règle de rattachement (ticket #50).
- liste : les 300 Communes de web/static/communes.json, plus leurs Anciennes communes et anciens noms ;
- le suffixe OFS entre parenthèses est retiré (« Renens (VD) » -> « Renens ») ;
- comparaison sans accents ni ligatures (« Échallens » = « Echallens », « Château-d'Œx » = « Château-d'Oex »),
  mais sensible à la casse (« Premier » ≠ « premier ») ;
- un nom ne doit être ni précédé ni suivi d'une lettre ou d'un trait d'union
  (« Lausanne » ne se trouve pas dans « Le Mont-sur-Lausanne ») ;
- les noms à article (« Le Mont-sur-Lausanne », « L'Isle ») sont reconnus avec l'article ou sa contraction
  (le/la/les/l'/du/des/au/aux, casse libre) ; sans article seulement si le reste contient un trait d'union ;
- chevauchements : la plus longue mention l'emporte.
"""
import json
import re
import unicodedata

ARTICLES = ("Le ", "La ", "Les ", "L'")


def plier(s: str) -> str:
    """Sans accents ni ligatures, apostrophes, tirets et espaces normalisés."""
    out = []
    for ch in s:
        if ch in "’‘ʼ`´":
            out.append("'")
        elif ch in "–—‑‐−":
            out.append("-")
        elif ch in "\u00a0\u202f\u2009":
            out.append(" ")
        elif ch == "œ":
            out.append("oe")
        elif ch == "Œ":
            out.append("Oe")
        else:
            d = unicodedata.normalize("NFD", ch)
            base = "".join(c for c in d if not unicodedata.combining(c))
            out.append(base[:1] if base else ch)
    return "".join(out)


def _forme(nom: str) -> str:
    nom = re.sub(r"\s*\([^)]*\)$", "", nom)
    return plier(nom)


def charger(path):
    communes = json.load(open(path, encoding="utf-8"))
    entrees = []
    for c in communes:
        entrees.append({"nom": c["nom"], "type": "Commune", "commune": c["nom"]})
        for a in c["anciens"]:
            entrees.append({"nom": a["nom"], "type": a["type"], "commune": c["nom"]})
    for e in entrees:
        f = _forme(e["nom"])
        art = next((a for a in ARTICLES if f.startswith(a)), None)
        core = f[len(art):] if art else f
        core_re = re.escape(core).replace(r"\ \-\ ", r"\s*-\s*").replace(r"\ ", r"\s+")
        if art:
            pre = r"(?:(?:\b[Ll]e|\b[Ll]a|\b[Ll]es|\b[Dd]u|\b[Dd]es|\b[Aa]u|\b[Aa]ux)\s+|\b[Ll]')"
            if "-" in core:
                pre = f"(?:{pre})?"
            pat = pre + core_re
        else:
            pat = core_re
        e["forme"] = f
        e["re"] = re.compile(r"(?<![\w-])" + pat + r"(?![\w-])")
    return entrees


def apparier(texte: str, entrees):
    """Renvoie [(début, fin, entrée)] ; les positions portent sur plier(texte)."""
    t2 = plier(texte)
    trouves = []
    for e in entrees:
        for m in e["re"].finditer(t2):
            trouves.append((m.start(), m.end(), e))
    trouves.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    garde = []
    fin = -1
    for s, f, e in trouves:
        if s >= fin:
            garde.append((s, f, e))
            fin = f
    return garde
```
