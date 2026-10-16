// PROTOTYPE (tickets #45 et #51), à jeter : la couche Conseils, sur les données réelles d'OpenParlData lues
// directement (voir donnees.svelte.ts), en trois variantes (proto.svelte.ts). La vraie couche passe par le cron.
import type { Couche } from '#lib/registre/types.js';
import type { Commune } from '#lib/types.js';
import { charger, element } from './donnees.svelte.js';

let communes: Promise<Commune[]> | null = null;
const lireCommunes = () => (communes ??= fetch('/communes.json').then((r) => r.json()));

export const coucheConseils: Couche<undefined> = {
	id: 'conseils',
	nom: 'Conseils',
	sources: ['openparldata-prototype'],
	permanente: false,
	activeParDefaut: true,
	icone: { signe: 'C', couleur: '#0b7285' },
	cleElement: 'o',
	async localiser(id) {
		const cs = await lireCommunes();
		await charger(cs);
		const x = element(id);
		if (!x || !x.communes.length) return null;
		// PROTOTYPE : un objet du Grand Conseil qui nomme plusieurs communes s'ouvre dans la fiche où l'on est, si
		// elle en fait partie ; sinon dans celle de la première nommée (#45).
		const ici = location.pathname.match(/^\/commune\/([^/]+)/)?.[1];
		const c = cs.find((c: Commune) => c.slug === (ici && x.communes.includes(ici) ? ici : x.communes[0]));
		return c ? { commune: c.slug, position: c.hotel } : null;
	},
	introuvable: (id) => `Aucun objet ni séance ${id}`,
	titre: (id, commune) => `${element(id)?.titre ?? id} – ${commune} – Vigie Vaud`,
	composants: {
		Carte: () => import('./Carte.svelte'),
		Volet: () => import('./Volet.svelte'),
		Onglet: () => import('./Onglet.svelte'),
		Fiche: () => import('./Fiche.svelte'),
		Apercu: () => import('./Apercu.svelte')
	}
};
