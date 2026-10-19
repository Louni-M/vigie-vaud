#!/usr/bin/env bash
# Vérifie qu'aucune donnée CAMAC ni DGMR n'est dans le site construit (norme DCG 8401 : pas de rediffusion).
# Les dossiers et les restrictions de circulation sont chargés en direct par le navigateur ; l'ancienne version
# écrivait les dossiers dans web/build/data.
# Utilisé par la CI des PR (ci.yml) et par la publication (publier.yml).
set -euo pipefail

build="${1:-web/build}"
if [ ! -d "$build" ]; then
	echo "$build introuvable : construire le site d'abord" >&2
	exit 1
fi
if [ -e "$build/data" ]; then
	echo "$build/data ne doit pas exister : aucune donnée CAMAC ni DGMR ne doit être publiée (norme DCG 8401)" >&2
	exit 1
fi
echo "Aucune donnée CAMAC ni DGMR dans $build"
