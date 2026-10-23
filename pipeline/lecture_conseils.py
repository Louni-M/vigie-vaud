"""Fichiers de lecture des conseils (ADR 0017) : ce que le site lit pour lister, reconstruit en entier depuis
l'archive à chaque import par `lecture`, fonction pure et déterministe.

- `conseils/index.json` : par conseil, de quoi remplir le volet et les compteurs, et le nombre d'Objets du Grand
  Conseil rattachés à chaque commune ;
- `conseils/fil.json` : les Objets et les Séances des 21 derniers jours et toutes les Séances à venir ;
- `conseils/<conseil>/objets-<année>.json` : les Objets en lignes légères, par date de dépôt décroissante ;
- `conseils/<conseil>/seances.json` : toutes les Séances du conseil en lignes légères ;
- `conseils/communes/<ofs>.json` (« Au Grand Conseil ») : les Objets rattachés à la commune, par date de dernière
  étape décroissante, seulement s'il y en a au moins un.

Un Objet est daté par son dépôt, sinon par sa première étape datée ; sans aucune date, il n'est dans aucun fichier
de lecture (son fichier d'archive reste ouvrable). Les jours se comptent à l'heure de Suisse.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from schema import (
    Auteur,
    ConseilIndexe,
    EntreeFil,
    Enveloppe,
    FichierSources,
    FilConseils,
    IndexConseils,
    LigneObjet,
    LigneSeance,
    ListeObjets,
    ListeSeances,
    Objet,
    RattachementsCommune,
    Seance,
    Source,
    nom_du_conseil,
)

Archive = Mapping[str, Objet | Seance]

SUISSE = ZoneInfo("Europe/Zurich")
FENETRE_FIL = timedelta(days=21)  # le fil du site en montre 14 : la marge couvre des imports manqués
FENETRE_RECENTS = timedelta(days=14)
# Où sont les fichiers de lecture dans le dépôt (motifs de `Path.glob`) : `lecture` produit tout ce qui doit y être,
# le reste est périmé. Les fichiers d'archive (`conseils/<conseil>/objets/`, `…/seances/`) n'y sont pas.
MOTIFS_LECTURE = (
    "conseils/index.json",
    "conseils/fil.json",
    "conseils/communes/*.json",
    "conseils/*/objets-*.json",
    "conseils/*/seances.json",
)


def lecture(archive: Archive, sources: FichierSources, genere: datetime) -> dict[str, Enveloppe]:
    """Les fichiers de lecture des conseils déclarés dans `sources`, par chemin, au passage de l'heure `genere`, et ceux
    de l'archive d'une commune scrapée passée non couverte (`_conseils_lus`)."""
    aujourdhui = genere.astimezone(SUISSE).date()
    depuis = aujourdhui - FENETRE_FIL
    documents: dict[str, Enveloppe] = {}
    fil: list[EntreeFil] = []
    index: list[ConseilIndexe] = []
    dates: list[tuple[str, Objet]] = []  # les Objets datés de tous les conseils
    for source, conseil, commune in _conseils_lus(sources, archive):
        objets = _par_date([(c, e) for c, e in archive.items() if isinstance(e, Objet) and _de(c, conseil)])
        seances = sorted(
            ((c, e) for c, e in archive.items() if isinstance(e, Seance) and _de(c, conseil)),
            key=lambda cs: (cs[1].date, cs[0]),
            reverse=True,
        )
        dates += objets

        par_annee: dict[int, list[tuple[str, Objet]]] = defaultdict(list)
        for cle, objet in objets:
            par_annee[date_de_reference(objet).year].append((cle, objet))
        for annee, liste in par_annee.items():
            documents[f"conseils/{conseil}/objets-{annee}.json"] = ListeObjets(
                version=1, genere=genere, conseil=conseil, annee=annee, objets=[ligne_objet(c, o) for c, o in liste]
            )
        documents[f"conseils/{conseil}/seances.json"] = ListeSeances(
            version=1,
            genere=genere,
            conseil=conseil,
            seances=[ligne_seance(c, s) for c, s in seances],
        )

        fil += [_entree_objet(conseil, c, o, commune) for c, o in objets if date_de_reference(o) >= depuis]
        fil += [_entree_seance(conseil, c, s, commune) for c, s in seances if _jour(s) >= depuis]
        index.append(_conseil_indexe(source, conseil, commune, par_annee, seances, aujourdhui))

    fil.sort(key=lambda e: e.cle)
    fil.sort(key=lambda e: e.date, reverse=True)
    documents["conseils/fil.json"] = FilConseils(version=1, genere=genere, entrees=fil)

    rattaches = _rattaches(dates)
    for ofs, liste in rattaches.items():
        documents[f"conseils/communes/{ofs}.json"] = RattachementsCommune(
            version=1, genere=genere, commune=ofs, objets=[ligne_objet(c, o) for c, o in liste]
        )
    documents["conseils/index.json"] = IndexConseils(
        version=1,
        genere=genere,
        conseils=index,
        communes={str(ofs): len(liste) for ofs, liste in sorted(rattaches.items())},
    )
    return documents


def _conseils_lus(sources: FichierSources, archive: Archive) -> list[tuple[Source, str, int | None]]:
    """Les conseils dont les fichiers de lecture sont reconstruits, dans l'ordre de `sources.json`, chacun avec sa clé
    et sa commune : celui de chaque source à bloc `conseil`, et l'archive d'une commune scrapée passée non couverte
    (une commune qui a demandé l'arrêt du robot, un nouveau site pas encore lu…), sous son n° OFS : ce qui a déjà été
    importé reste en ligne, sans import ni sonde (récit 33 de la spec de J3)."""
    lus = []
    for source in sources.sources:
        if source.conseil is not None:
            lus.append((source, source.conseil.cle, source.conseil.commune))
            continue
        couverture = source.couverture
        if source.site is None or couverture is None or couverture.mode != "non_couvert":
            continue
        for ofs in couverture.communes if couverture.communes != "canton" else []:
            if any(_de(cle, str(ofs)) for cle in archive):
                lus.append((source, str(ofs), ofs))
    return lus


def date_de_reference(objet: Objet) -> date | None:
    """Le jour de dépôt de l'Objet, sinon celui de sa première étape datée ; `None` s'il n'a aucune date."""
    return objet.depose or (objet.etapes[0].date if objet.etapes else None)


def ligne_objet(cle: str, objet: Objet) -> LigneObjet:
    return LigneObjet(
        cle=cle,
        numero=objet.numero,
        type=objet.type,
        depose=objet.depose,
        titre=objet.titre,
        auteurs=[Auteur(nom=c.nom, parti=c.parti) for c in objet.contributeurs[:2]],
        nombre_auteurs=len(objet.contributeurs),
        statut=objet.statut,
        derniere_etape=_derniere_etape(objet),
        communes=list(objet.communes),
    )


def ligne_seance(cle: str, seance: Seance) -> LigneSeance:
    """Une Séance en ligne légère ; une Séance sans points y garde ses documents, que sa ligne montre à leur place."""
    return LigneSeance(
        cle=cle,
        date=seance.date,
        points=len(seance.ordre_du_jour),
        documents=[] if seance.ordre_du_jour else seance.documents,
    )


def _de(cle: str, conseil: str) -> bool:
    return cle.startswith(conseil + "/")


def _jour(seance: Seance) -> date:
    return date.fromisoformat(seance.date[:10])


def _derniere_etape(objet: Objet) -> date | None:
    return objet.etapes[-1].date if objet.etapes else None


def _par_date(objets: list[tuple[str, Objet]]) -> list[tuple[str, Objet]]:
    """Les Objets datés, du plus récent au plus ancien (puis par clé, pour un ordre stable)."""
    dates = [(c, o) for c, o in objets if date_de_reference(o) is not None]
    return sorted(dates, key=lambda co: (date_de_reference(co[1]), co[0]), reverse=True)


def _rattaches(objets: list[tuple[str, Objet]]) -> dict[int, list[tuple[str, Objet]]]:
    """Par n° OFS, les Objets rattachés à la commune, par date de dernière étape décroissante."""
    par_commune: dict[int, list[tuple[str, Objet]]] = defaultdict(list)
    for cle, objet in objets:
        for ofs in dict.fromkeys(c.ofs for c in objet.communes):
            par_commune[ofs].append((cle, objet))
    for liste in par_commune.values():
        liste.sort(key=lambda co: (_derniere_etape(co[1]) or date_de_reference(co[1]), co[0]), reverse=True)
    return par_commune


def _conseil_indexe(
    source: Source,
    cle: str,
    commune: int | None,
    par_annee: Mapping[int, list[tuple[str, Objet]]],
    seances: list[tuple[str, Seance]],
    aujourdhui: date,
) -> ConseilIndexe:
    """Le conseil dans l'index. Une commune non couverte n'a plus de niveau déclaré : elle donne ce que son archive
    a, ses Objets s'il y en a, ses Séances."""
    if source.conseil is not None:
        donne = source.conseil.donne
    else:
        donne = (["objets"] if par_annee else []) + ["seances"]
    recents = [(c, o) for liste in par_annee.values() for c, o in liste]
    recents = _par_date([(c, o) for c, o in recents if date_de_reference(o) >= aujourdhui - FENETRE_RECENTS])
    a_venir = [c for c, s in seances if _jour(s) >= aujourdhui]
    passees = [c for c, s in seances if _jour(s) < aujourdhui]
    return ConseilIndexe(
        cle=cle,
        source=source.id,
        nom=nom_du_conseil(source.nom),
        commune=commune,
        donne=donne,
        objets=sum(len(liste) for liste in par_annee.values()),
        objets_par_annee={str(annee): len(liste) for annee, liste in sorted(par_annee.items())},
        recents=[ligne_objet(c, o) for c, o in recents],
        seances=len(seances),
        prochaine_seance=a_venir[-1] if a_venir else None,
        derniere_seance=passees[0] if passees else None,
    )


def _entree_objet(conseil: str, cle: str, objet: Objet, commune: int | None) -> EntreeFil:
    return EntreeFil(
        cle=cle,
        conseil=conseil,
        sorte="objet",
        type=objet.type,
        date=date_de_reference(objet).isoformat(),
        titre=objet.titre,
        communes=[commune] if commune is not None else [c.ofs for c in objet.communes],
        points=None,
    )


def _entree_seance(conseil: str, cle: str, seance: Seance, commune: int | None) -> EntreeFil:
    return EntreeFil(
        cle=cle,
        conseil=conseil,
        sorte="seance",
        type=None,
        date=seance.date,
        titre=seance.nom,
        communes=[commune] if commune is not None else [],
        points=len(seance.ordre_du_jour),
    )
