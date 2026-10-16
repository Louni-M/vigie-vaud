"""Un faux OpenParlData écrit à la main, sur le modèle du `Monde` des faux services de J0.

Un `Monde` décrit en quelques lignes les Objets (*affairs*) et les Séances (*meetings*) que renverrait l'API, avec
leurs relations ; `transport()` les sert à `httpx` sans réseau, à la forme des réponses réelles (libellés imbriqués
`{"fr": …}`, enveloppe de pagination `meta`), ainsi que les documents des Objets (*docs*). Le faux honore ce que
l'import utilise : `body_key`, `group_id`, `id` (liste séparée par des virgules), `from_updated_at` (au jour près),
`offset` et `limit`, ce dernier plafonné à `taille_page` pour forcer la pagination. Chaque requête est notée avec l'heure de l'horloge factice.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import httpx

API = "https://api.openparldata.ch/v1"


@dataclass
class HorlogeFactice:
    """Heure fixée, qui n'avance que par `attendre` (ou à la main)."""

    heure: datetime

    def __call__(self) -> datetime:
        return self.heure

    def attendre(self, secondes: float) -> None:
        self.heure += timedelta(seconds=secondes)


@dataclass
class Contributeur:
    nom: str
    parti: str | None = None
    role: str | None = "Auteur"
    type: str = "person"
    prenom: str | None = None  # `firstname`, s'il diffère du début de `nom`
    nom_de_famille: str | None = None  # `lastname`


@dataclass
class Etape:
    date: str | None  # « 2026-10-06 »
    titre_fr: str | None = None  # `title.fr`, souvent absent
    harmonise_fr: str = "Déposé"  # `title_harmonized.fr`


@dataclass
class Document:
    nom: str | None
    url: str
    date: str | None = None
    categorie: str | None = None
    texte: str | None = None  # `text`, extrait du PDF par OpenParlData
    mis_a_jour: str | None = None  # `updated_at` ; par défaut, celui de son Objet


@dataclass
class Affaire:
    id: int
    body_key: str
    number: str
    title: str
    type_name: str = "Interpellation"
    state_name: str | None = None
    begin_date: str | None = "2026-10-06"
    updated_at: str = "2026-10-07"
    url: str | None = None
    contributeurs: list[Contributeur] = field(default_factory=list)
    etapes: list[Etape] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)

    def brut(self) -> dict:
        return {
            "id": self.id,
            "body_key": self.body_key,
            "number": self.number,
            "title": {"fr": self.title},
            "title_long": {"fr": f"{self.type_name} - {self.title}"},
            "type_name": {"fr": self.type_name},
            "state_name": {"fr": self.state_name} if self.state_name else {},
            "begin_date": f"{self.begin_date}T00:00:00" if self.begin_date else None,
            "url_external": {"fr": self.url} if self.url else {},
            "updated_at": f"{self.updated_at}T05:12:00",
            "contributors": _relation(
                {
                    "type": c.type,
                    "fullname": c.nom,
                    "firstname": c.prenom or c.nom.split()[0] if c.type == "person" else None,
                    "lastname": c.nom_de_famille or " ".join(c.nom.split()[1:]) if c.type == "person" else None,
                    "party": {"fr": c.parti} if c.parti else {},
                    "role": {"fr": c.role} if c.role else {},
                    "position": i,
                }
                for i, c in enumerate(self.contributeurs, start=1)
            ),
            "events": _relation(
                {
                    "date": f"{e.date}T00:00:00" if e.date else None,
                    "position": i,
                    "title": {"fr": e.titre_fr} if e.titre_fr else {"de": "Eingereicht"},
                    "title_harmonized": {"de": "Eingereicht", "fr": e.harmonise_fr},
                }
                for i, e in enumerate(self.etapes, start=1)
            ),
            "docs": _relation(
                {
                    "name": d.nom,
                    "url": d.url,
                    "date": f"{d.date}T00:00:00" if d.date else None,
                    "category": {"fr": d.categorie} if d.categorie else {},
                    "text": d.texte,
                }
                for d in self.documents
            ),
        }

    def docs(self) -> list[Doc]:
        return [
            Doc(self.id * 100 + i, self.body_key, self.id, d.mis_a_jour or self.updated_at)
            for i, d in enumerate(self.documents)
        ]


@dataclass
class Doc:
    """Un document tel que `/v1/docs/` le liste, rattaché à son Objet par `affair_id`."""

    id: int
    body_key: str
    affair_id: int
    updated_at: str

    def brut(self) -> dict:
        return {"id": self.id, "affair_id": self.affair_id, "updated_at": f"{self.updated_at}T04:10:58"}


@dataclass
class Point:
    numero: int
    titre: str
    affaire_numero: str | None = None
    affaire_id: int | None = None
    resultat: str | None = None
    categorie: str | None = None


@dataclass
class Reunion:
    id: int
    body_key: str
    name: str
    begin_date: str  # « 2026-10-06T00:00:00 »
    group_id: int = 1
    updated_at: str = "2026-10-07"
    url: str | None = None
    points: list[Point] = field(default_factory=list)

    def brut(self) -> dict:
        return {
            "id": self.id,
            "body_key": self.body_key,
            "name": {"fr": self.name},
            "type": "meeting",
            "group_id": self.group_id,
            "begin_date": self.begin_date,
            "url_external": {"fr": self.url} if self.url else {},
            "updated_at": f"{self.updated_at}T05:12:00",
            "agendas": _relation(
                {
                    "item_number": p.numero,
                    "item_number_display": str(p.numero),
                    "item_title": p.titre,
                    "item_affair_number": p.affaire_numero,
                    "item_affair_id": p.affaire_id,
                    "item_result": p.resultat,
                    "item_category": p.categorie,
                }
                for p in self.points
            ),
        }


def _relation(elements) -> dict:
    data = list(elements)
    return {"data": data, "meta": {"total_records": len(data), "has_more": False}}


@dataclass
class Monde:
    horloge: Callable[[], datetime] = field(default=lambda: datetime(2026, 10, 16, 7, 5, tzinfo=UTC))
    affaires: list[Affaire] = field(default_factory=list)
    reunions: list[Reunion] = field(default_factory=list)
    taille_page: int = 2
    en_panne: set[str] = field(default_factory=set)  # body_key qui répondent 503
    requetes: list[tuple[datetime, httpx.Request]] = field(default_factory=list)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._repondre)

    def requetes_vers(self, entite: str) -> list[httpx.Request]:
        return [r for _, r in self.requetes if r.url.path == f"/v1/{entite}/"]

    def _repondre(self, requete: httpx.Request) -> httpx.Response:
        self.requetes.append((self.horloge(), requete))
        p = requete.url.params
        if p.get("body_key") in self.en_panne:
            return httpx.Response(503)
        if requete.url.path == "/v1/affairs/":
            elements = self.affaires
            if "id" in p:
                ids = {int(i) for i in p["id"].split(",")}
                elements = [e for e in elements if e.id in ids]
        elif requete.url.path == "/v1/docs/":
            elements = [d for a in self.affaires for d in a.docs()]
        elif requete.url.path == "/v1/meetings/":
            elements = [r for r in self.reunions if "group_id" not in p or r.group_id == int(p["group_id"])]
        else:
            return httpx.Response(404)
        elements = [e for e in elements if e.body_key == p.get("body_key")]
        if "from_updated_at" in p:
            depuis = date.fromisoformat(p["from_updated_at"])
            elements = [e for e in elements if date.fromisoformat(e.updated_at) >= depuis]
        elements.sort(key=lambda e: e.id)
        offset = int(p.get("offset", 0))
        limit = min(int(p.get("limit", 500)), self.taille_page)
        page = elements[offset : offset + limit]
        return httpx.Response(
            200,
            json={
                "meta": {
                    "offset": offset,
                    "limit": limit,
                    "total_records": len(elements),
                    "has_more": offset + limit < len(elements),
                },
                "data": [e.brut() for e in page],
            },
        )
