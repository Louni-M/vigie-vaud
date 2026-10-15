"""Schéma commun de Vigie Vaud (ADR 0013) : le seul endroit où il s'écrit.

Ces modèles Pydantic décrivent `sources.json` (déclaration des sources, écrite à la main) et les fichiers du
dépôt de données, qui portent tous l'enveloppe `version` + `genere`. Le cron valide ce qu'il lit et écrit en
construisant ces modèles.

On en tire le JSON Schema, versionné dans `schema/` à la racine du dépôt, puis les types TypeScript du site
(`web/src/lib/schema.ts`). Après toute modification, régénérer les deux avec `pnpm --dir web schema` ; la CI
échoue s'ils ne sont pas à jour.

Réglages repris de l'essai de #3, pour des types TypeScript aussi propres qu'écrits à la main :
- pas de titre par champ (sinon `json-schema-to-typescript` crée un alias par champ) ;
- énumérations nommées par `TypeAliasType` (un seul type TypeScript, réutilisé partout) ;
- `extra="forbid"` (sinon chaque interface admet des clés inconnues).

Usage : `uv run python schema.py` écrit les JSON Schema dans `schema/`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)
from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import TypeAliasType

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_SCHEMA = RACINE / "schema"


class Modele(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Types communs ---------------------------------------------------------------------------------------------

Lien = TypeAliasType("Lien", Annotated[str, StringConstraints(pattern=r"^https?://\S+$")])
NumeroOfs = TypeAliasType("NumeroOfs", Annotated[int, Field(ge=1, le=9999)])


def _en_utc(d: datetime) -> datetime:
    if d.utcoffset() != timedelta(0):
        raise ValueError("l'heure doit être en UTC (suffixe Z)")
    return d


Horodatage = TypeAliasType("Horodatage", Annotated[AwareDatetime, AfterValidator(_en_utc)])


class Enveloppe(Modele):
    """Enveloppe de chaque fichier du dépôt de données."""

    version: Annotated[int, Field(ge=1)] = Field(
        description="Version majeure du format : seul un changement incompatible l'augmente. "
        "Le site refuse une version qu'il ne connaît pas."
    )
    genere: Horodatage = Field(description="Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).")


# --- sources.json ----------------------------------------------------------------------------------------------

IdSource = TypeAliasType("IdSource", Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")])
VoieAcces = TypeAliasType("VoieAcces", Literal["direct", "cron", "worker", "preparee"])
SorteFraicheur = TypeAliasType("SorteFraicheur", Literal["donnee", "requete", "millesime"])
ModeCouverture = TypeAliasType("ModeCouverture", Literal["api", "scrape"])


class Attribution(Modele):
    texte: str = Field(min_length=1, description="Texte affiché, par ex. « © swisstopo ».")
    lien: Lien
    licence: str = Field(min_length=1)


class CouvertureDeclaree(Modele):
    communes: Literal["canton"] | Annotated[list[NumeroOfs], Field(min_length=1)] = Field(
        description="« canton » (les 300 communes) ou la liste des n° OFS des communes couvertes."
    )
    mode: ModeCouverture


class Sonde(Modele):
    """Requête de vérification envoyée par le cron, sans conserver de données.

    Une seule requête GET par passage, sans nouvel essai. La réponse doit être un objet JSON dont `features` liste
    les enregistrements (JSON ArcGIS ou GeoJSON) ; elle doit donc rester légère (un enregistrement suffit).
    """

    url: Lien
    delai: Annotated[int, Field(ge=1, le=60)] = Field(description="Délai de réponse en secondes.")
    champs: list[str] = Field(
        default=[],
        description="Champs que doit porter chaque enregistrement renvoyé, lus dans `attributes` (JSON ArcGIS) "
        "ou `properties` (GeoJSON).",
    )
    jamais_vide: bool = Field(default=False, description="Une réponse sans enregistrement compte comme un échec.")


class Source(Modele):
    id: IdSource = Field(description="Identifiant stable, clé de la source dans l'état des sources.")
    nom: str = Field(min_length=1)
    nom_court: str = Field(min_length=1, description="Nom affiché dans le badge de fraîcheur (« · CAMAC »).")
    attribution: Attribution
    voie_acces: VoieAcces
    fraicheur: SorteFraicheur
    couverture: CouvertureDeclaree
    sonde: Sonde | None = Field(default=None, description="Sans sonde, la source n'est pas surveillée.")


class FichierSources(Modele):
    """`sources.json` : chaque source y est déclarée une seule fois, pour le site et pour le cron."""

    schema_: str | None = Field(default=None, alias="$schema")
    sources: list[Source]

    @model_validator(mode="after")
    def _ids_uniques(self) -> FichierSources:
        vus: set[str] = set()
        for s in self.sources:
            if s.id in vus:
                raise ValueError(f"identifiant de source en double : {s.id}")
            vus.add(s.id)
        return self


def lire_sources(chemin: Path) -> FichierSources:
    return FichierSources.model_validate_json(chemin.read_bytes())


# --- État des sources (etat-sources.json, dépôt de données) ----------------------------------------------------

EtatSonde = TypeAliasType("EtatSonde", Literal["disponible", "en_panne"])


class EtatSource(Modele):
    """Ce que les sondes ont mesuré pour une source, dans un état binaire (sans « dégradée »).

    Aucun numéro d'issue n'y figure.
    """

    etat: EtatSonde
    depuis: Horodatage | None = Field(
        description="En panne : heure de la première sonde en échec. Disponible : heure du retour, ou de la première "
        "sonde réussie ; `null` tant qu'aucune sonde n'a réussi."
    )
    derniere_sonde: Horodatage
    dernier_succes: Horodatage | None = Field(description="`null` tant qu'aucune sonde n'a réussi.")
    echecs_consecutifs: Annotated[int, Field(ge=0)] = Field(description="La source passe en panne à 2.")
    motif: str | None = Field(description="Cause courte du dernier échec (« HTTP 503 », « délai dépassé »…).")


class EtatSources(Enveloppe):
    """`etat-sources.json` : l'état de chaque source sondée, indexé par identifiant de source."""

    version: Literal[1] = Field(description="Version 1. Le cron repart de zéro devant une autre version.")
    sources: dict[IdSource, EtatSource] = Field(description="Seules les sources qui ont un bloc `sonde` y figurent.")


# --- Génération du JSON Schema ---------------------------------------------------------------------------------

# Un JSON Schema par document : `schema/<nom>.schema.json`.
DOCUMENTS: dict[str, type[BaseModel]] = {
    "sources": FichierSources,
    "enveloppe": Enveloppe,
    "etat-sources": EtatSources,
}


class _SansTitresDeChamps(GenerateJsonSchema):
    def field_title_should_be_set(self, schema) -> bool:  # noqa: ANN001
        return False


def json_schema(modele: type[BaseModel]) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **modele.model_json_schema(schema_generator=_SansTitresDeChamps),
    }


def ecrire_schemas(dossier: Path = DOSSIER_SCHEMA) -> list[Path]:
    dossier.mkdir(parents=True, exist_ok=True)
    ecrits = []
    for nom, modele in DOCUMENTS.items():
        chemin = dossier / f"{nom}.schema.json"
        chemin.write_text(json.dumps(json_schema(modele), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ecrits.append(chemin)
    return ecrits


if __name__ == "__main__":
    for chemin in ecrire_schemas():
        print(chemin.relative_to(RACINE))
