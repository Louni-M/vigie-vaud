// Couverture de la visite en cours, pour la carte, la fiche commune et la page Couverture : déduite de sources.json, du registre et de
// l'état des sources. Celui-ci est chargé au premier besoin, dans le navigateur, et relu après un échec
// (`creerEtatSource`) ; avant (et à la pré-génération), il vaut « inconnu », ce qui ne change ni le mode ni le grisage.
import { deduireCouverture, type Couverture } from './couverture.js';
import { creerEtatSource } from './etat-source.svelte.js';
import { chargerEtatSources } from './etat-sources.js';
import { COUCHES } from './registre/couches.js';
import { PLATEFORMES, SOURCES } from './sources.js';

/** L'état des sources et l'heure de sa lecture : au-delà de 8 h après le dernier passage du cron, il est périmé. */
const lecture = creerEtatSource(async () => ({ etat: await chargerEtatSources(fetch), lu: new Date() }));
/** L'heure de référence avant la première lecture réussie. */
const ouverture = new Date();

/**
 * La Couverture, qui suit l'état des sources une fois chargé. `communes` ne sert qu'à ce qui les énumère
 * (`grisees`, le nombre de communes couvertes) : `couvre`, `mode` et `etat` n'en ont pas besoin.
 */
export function couvertureCourante(communes: readonly { bfs: number }[] = []): Couverture {
	const l = lecture.valeur();
	return deduireCouverture({
		sources: SOURCES,
		etat: l?.etat ?? null,
		couches: COUCHES,
		communes,
		plateformes: PLATEFORMES,
		maintenant: l?.lu ?? ouverture
	});
}

/**
 * Vrai une fois le premier chargement de l'état des sources terminé, même en échec : la Couverture le dit alors
 * « inconnu » jusqu'à ce qu'un nouvel essai réussisse. Avant, elle le croit « inconnu » faute de mieux.
 */
export function couvertureChargee(): boolean {
	return lecture.chargee();
}
