// PROTOTYPE (ticket #45), à jeter : une couche Conseils factice, pour que le fil cantonal ait des objets et des
// séances à montrer et à ouvrir dans l'onglet Conseil. La vraie couche se spécifie sur la carte #43.
import type { Couche } from '#lib/registre/types.js';
import { element } from './donnees.js';

let communes: Promise<{ slug: string; hotel: [number, number] }[]> | null = null;
const lireCommunes = () => (communes ??= fetch('/communes.json').then((r) => r.json()));

export const coucheConseils: Couche<undefined> = {
	id: 'conseils',
	nom: 'Conseils',
	sources: ['openparldata-prototype'],
	permanente: false,
	activeParDefaut: true,
	icone: { signe: 'C', couleur: '#7a3e9d' },
	cleElement: 'o',
	async localiser(id) {
		const x = element(id);
		if (!x || !x.communes.length) return null;
		const c = (await lireCommunes()).find((c: { slug: string }) => c.slug === x.communes[0]);
		return c ? { commune: c.slug, position: c.hotel } : null;
	},
	introuvable: (id) => `Aucun objet ni séance ${id}`,
	titre: (id, commune) => `${element(id)?.titre ?? id} – ${commune} – Vigie Vaud`,
	composants: {
		Carte: () => import('./Carte.svelte'),
		Volet: () => import('./Volet.svelte'),
		Onglet: () => import('./Onglet.svelte'),
		Fiche: () => import('./Fiche.svelte')
	}
};
