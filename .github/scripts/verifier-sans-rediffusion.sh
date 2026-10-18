#!/usr/bin/env bash
# Vérifie qu'aucune donnée CAMAC n'est dans le site construit (DCG 8401 : pas de rediffusion).
# Les dossiers sont chargés en direct par le navigateur ; l'ancienne version les écrivait dans web/build/data.
# Utilisé par la CI des PR (ci.yml) et par la publication (publier.yml).
set -euo pipefail

build="${1:-web/build}"
if [ ! -d "$build" ]; then
	echo "$build introuvable : construire le site d'abord" >&2
	exit 1
fi
if [ -e "$build/data" ]; then
	echo "$build/data ne doit pas exister : aucune donnée CAMAC ne doit être publiée" >&2
	exit 1
fi
echo "Aucune donnée CAMAC dans $build"
