// Couverture de la visite en cours, pour la carte et la fiche commune : déduite de sources.json, du registre et de
// l'état des sources. Celui-ci est chargé une seule fois, au premier besoin, dans le navigateur ; avant (et à la
// pré-génération), il vaut « inconnu », ce qui ne change ni le mode ni le grisage.
import { browser } from '$app/env';
import { deduireCouverture, type Couverture } from './couverture.js';
import { chargerEtatSources } from './etat-sources.js';
import { COUCHES } from './registre/couches.js';
import type { EtatSources } from './schema.js';
import { SOURCES } from './sources.js';

let etat = $state.raw<EtatSources | null>(null);
/** Heure de lecture de l'état : au-delà de 2 h après le dernier passage du cron, il est périmé. */
let lu = $state.raw(new Date());
let demande = false;

/**
 * La Couverture, qui suit l'état des sources une fois chargé. `communes` ne sert qu'à ce qui les énumère
 * (`grisees`, le nombre de communes couvertes) : `couvre`, `mode` et `etat` n'en ont pas besoin.
 */
export function couvertureCourante(communes: readonly { bfs: number }[] = []): Couverture {
	if (browser && !demande) {
		demande = true;
		chargerEtatSources(fetch).then((e) => {
			lu = new Date();
			etat = e;
		});
	}
	return deduireCouverture({ sources: SOURCES, etat, couches: COUCHES, communes, maintenant: lu });
}
