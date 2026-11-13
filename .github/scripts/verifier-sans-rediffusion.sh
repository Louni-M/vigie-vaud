#!/usr/bin/env bash
# Vérifie qu'aucune donnée CAMAC ni DGMR n'est dans le site construit (norme DCG 8401 : pas de rediffusion).
# Les dossiers et les restrictions de circulation sont chargés en direct par le navigateur ; l'ancienne version
# écrivait les dossiers dans web/build/data.
# Utilisé par la CI des PR (ci.yml) et par la publication (publier.yml). Testé par web/scripts/verifier-sans-rediffusion.test.ts.
#
# Au-delà de build/data, tout fichier du site construit est cherché, où qu'il soit, pour un champ caractéristique
# d'une des deux sources employé comme clé (suivi de « : »), sous toutes ses formes : JSON ou GeoJSON brut, JSON
# échappé dans une chaîne ou un attribut HTML, objet littéral d'un fichier JS. Le nom seul ne suffit pas : le code
# du site cite ces champs pour interroger le canton (outFields, `e.NO_CAMAC`, `NO_CAMAC IN (…)`).
# Limites : un export CSV (en-tête « NO_CAMAC,NO_FAO,… ») ressemble au code, et des données déjà converties au
# format du site (Dossier, Restriction) ne portent plus ces champs.
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

# Champs propres à chaque source (sonde de sources.json), « SOURCE=champ|champ » ; les noms génériques (OBJECTID,
# NOM, TYPE, URL, ETAT…) sont exclus.
marqueurs=(
	'CAMAC=NO_CAMAC|NO_FAO|DATE_ENQUETE|DECISION_COMMUNALE|DATE_DECISION'
	'DGMR=RHRC|WEEK_END|HEURE_DEBUT|HEURE_FIN'
)
# Guillemet éventuel autour du champ : ", ', `, \" (JSON dans une chaîne) ou &quot; (JSON dans un attribut HTML).
guillemet='(\\?["'"'"'`]|&quot;)?'

export LC_ALL=C
trouve=0
for marqueur in "${marqueurs[@]}"; do
	source="${marqueur%%=*}"
	# Ni précédé d'un point ni d'un caractère d'identifiant : `e.NO_CAMAC` (y compris `a?e.NO_CAMAC:b`) est du code.
	motif="(^|[^.[:alnum:]_\$])${guillemet}(${marqueur#*=})${guillemet}[[:space:]]*:"
	fichiers=$(grep -rlE -- "$motif" "$build") && statut=0 || statut=$?
	case $statut in
	0)
		while IFS= read -r f; do
			echo "$f contient un champ $source ($(grep -oE -- "$motif" "$f" | head -1)) : aucune donnée $source ne doit être publiée (norme DCG 8401)" >&2
		done <<<"$fichiers"
		trouve=1
		;;
	1) ;;
	*)
		echo "Recherche des champs $source impossible dans $build" >&2
		exit 2
		;;
	esac
done
if [ "$trouve" -ne 0 ]; then
	exit 1
fi
echo "Aucune donnée CAMAC ni DGMR dans $build"
