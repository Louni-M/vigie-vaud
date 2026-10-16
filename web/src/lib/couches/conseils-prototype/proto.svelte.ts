/*
 * PROTOTYPE (ticket #51), à jeter : la variante choisie et l'état propre au prototype, en mémoire seulement.
 *
 * A « Fiche du Grand Conseil » : la couche n'ajoute que le marqueur du Grand Conseil ; il ouvre sa propre fiche, en
 *   colonne à droite (adresse /grand-conseil), où s'ouvrent aussi ses objets et séances sans commune.
 * B « Activité sur la carte » : une pastille par commune avec le nombre d'objets récents ; le marqueur du Grand
 *   Conseil ouvre le fil cantonal filtré sur le Grand Conseil.
 * C « Agenda des séances » : les communes au conseil couvert sont cerclées, avec la date de leur prochaine ou
 *   dernière séance ; le volet est un agenda, et le marqueur du Grand Conseil l'ouvre sur le Grand Conseil.
 */
export const VARIANTES = [
	{ id: 'A', nom: 'Fiche du Grand Conseil' },
	{ id: 'B', nom: 'Activité sur la carte' },
	{ id: 'C', nom: 'Agenda des séances' }
] as const;
export type Variante = (typeof VARIANTES)[number]['id'];

function initiale(): Variante {
	if (typeof location === 'undefined') return 'A';
	const v = new URLSearchParams(location.search).get('conseils');
	return VARIANTES.some((x) => x.id === v) ? (v as Variante) : 'A';
}

export const proto = $state({
	variante: initiale(),
	/** A : la fiche du Grand Conseil est ouverte (dans la vraie couche : l'adresse /grand-conseil). */
	gc: false,
	/** A : élément ouvert dans la fiche du Grand Conseil (`/grand-conseil?o=…`). */
	gcElement: null as string | null,
	/** B : le fil n'affiche que ce conseil (« Grand Conseil »). */
	filQui: null as string | null,
	/** C : le volet Conseils est ouvert sur ce conseil (clé OpenParlData, « VD » : le Grand Conseil ; absent : tous). */
	agendaConseil: undefined as string | undefined,
	/** Téléphone : grisage de la Couverture des Conseils demandé par « Voir sur la carte ». */
	grisageMobile: false,
	/** Téléphone : vue que la couche demande d'afficher (« fil », « couches »). */
	vue: null as string | null,
	/** Onglet que la fiche commune doit montrer à sa prochaine ouverture. */
	onglet: null as string | null
});

export function ouvrirGrandConseil(element: string | null = null) {
	proto.gc = true;
	proto.gcElement = element;
}
export function fermerGrandConseil() {
	proto.gc = false;
	proto.gcElement = null;
}
