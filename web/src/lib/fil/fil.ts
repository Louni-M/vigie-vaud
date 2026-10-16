import type { Commune, Zone } from '#lib/types.js';
import type { EntreeFil, TypeFil } from '#lib/registre/types.js';

/**
 * Le fil cantonal, calculé : il ne connaît aucune couche par son nom. Il reçoit, dans l'ordre du rail, ce que
 * chaque couche apporte au fil (`Couche.fil`) et rend ce que le composant n'a plus qu'à afficher.
 */

/** Une couche qui alimente le fil, et où en sont ses entrées. */
export interface SourceFil {
	couche: string;
	nom: string;
	types: TypeFil[];
	etat: { entrees: EntreeFil[] } | 'chargement' | 'panne';
	/** L'aide de « Sans commune » que déclare la couche (`Fil.sansCommune`). */
	sansCommune?: string;
}

/** Choix de la personne dans le fil : ni dans l'adresse, ni retenus d'une visite à l'autre. */
export interface ReglagesFil {
	/** Puces éteintes (`cleType`). */
	masques: string[];
	portee: 'zone' | 'canton';
}

export interface ContexteFil {
	/** AAAA-MM-JJ, jour local. */
	aujourdhui: string;
	/** Zone du fil (voir `zoneDuFil`), `null` tant que la carte n'a rien affiché. */
	zone: Zone | null;
	communes: readonly Pick<Commune, 'slug' | 'hotel' | 'nom'>[];
}

/** Une entrée prête à afficher : avec sa couche et sa pastille. */
export interface LigneFil extends EntreeFil {
	couche: string;
	/** Unique dans le fil. */
	cle: string;
	signe: string;
	couleur: string;
	/** Nom du type (« Nouveaux dossiers »). */
	nomType: string;
	/**
	 * Noms de ses communes, dans leur ordre, quand `qui` n'en nomme aucune (« Grand Conseil → Morges, Lausanne ») ;
	 * vide sinon (« Conseil communal de Lausanne », « Lutry »).
	 */
	nommees: string[];
}

/** Clé d'une puce : les types sont déclarés par couche, deux couches peuvent avoir le même. */
export const cleType = (couche: string, type: string) => `${couche}:${type}`;

/** Une puce du fil : un type déclaré par une couche, allumé ou éteint. */
export interface PuceFil extends TypeFil {
	cle: string;
	active: boolean;
}

export interface VueFil {
	/** Couches dont les entrées n'ont pas pu être lues, dans l'ordre du rail : une ligne chacune, en tête. */
	pannes: { couche: string; nom: string }[];
	/** Les entrées d'une couche au moins sont encore attendues. */
	chargement: boolean;
	/** Dans l'ordre du rail, puis des types déclarés. */
	puces: PuceFil[];
	/** Entrées sans commune, quelle que soit la zone, dans le même ordre que le reste du fil. */
	sansCommune: LigneFil[];
	/**
	 * L'aide de la section « Sans commune », celles des couches qui en déclarent une, dans l'ordre du rail ; `null`
	 * si aucune n'en déclare : la section n'est pas affichée. Sinon elle l'est toujours, même vide.
	 */
	aideSansCommune: string | null;
	/** Daté du futur, le plus proche d'abord, quelle que soit la fenêtre. */
	avenir: LigneFil[];
	/** Les jours de la fenêtre, le plus récent d'abord. */
	jours: { date: string; entrees: LigneFil[] }[];
	/** Entrées d'« À venir » et des jours (« 12 dans la zone visible »). */
	compteur: number;
}

/**
 * Zone du fil après un déplacement de la carte, distincte de la zone de la carte : celle du dernier déplacement
 * fait par la personne (`parLaPersonne` : glisser, zoomer, recherche). Les vols et cadrages lancés par le registre
 * pour ouvrir un élément ou une fiche ne la changent pas : la liste ne se vide pas quand la carte vole vers ce
 * qu'on vient d'ouvrir. À l'arrivée (`avant` nul), c'est la zone initiale.
 */
export const zoneDuFil = (avant: Zone | null, apres: Zone, parLaPersonne: boolean): Zone =>
	avant === null || parLaPersonne ? apres : avant;

/** Jours du fil, aujourd'hui non compris : la fenêtre est fixée par le fil, pas par les couches. */
export const JOURS_FIL = 14;

const JOUR_A_LAUSANNE = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Zurich' });
/** Le jour d'un instant à Lausanne, AAAA-MM-JJ. */
export const jourDe = (d: Date) => JOUR_A_LAUSANNE.format(d);

/** Premier jour du fil (AAAA-MM-JJ), passé aux couches en `depuis`. */
export function depuisFil(aujourdhui: string): string {
	const d = new Date(`${aujourdhui}T00:00:00Z`);
	d.setUTCDate(d.getUTCDate() - JOURS_FIL);
	return d.toISOString().slice(0, 10);
}

export function calculerFil(sources: readonly SourceFil[], reglages: ReglagesFil, ctx: ContexteFil): VueFil {
	const depuis = depuisFil(ctx.aujourdhui);
	const noms = new Map(ctx.communes.map((c) => [c.slug, c.nom]));
	const nommees = (e: EntreeFil) => {
		const n = e.communes.flatMap((c) => noms.get(c) ?? []);
		return n.some((nom) => e.qui.includes(nom)) ? [] : n;
	};
	// Dans l'ordre du rail, puis des types déclarés : le tri par date, stable, garde cet ordre dans un jour.
	const lignes: LigneFil[] = [];
	const puces: PuceFil[] = [];
	for (const s of sources)
		for (const t of s.types) {
			const cle = cleType(s.couche, t.id);
			const active = !reglages.masques.includes(cle);
			puces.push({ ...t, cle, active });
			if (!active || typeof s.etat !== 'object') continue;
			for (const e of s.etat.entrees)
				if (e.type === t.id && e.date >= depuis)
					lignes.push({
						...e,
						couche: s.couche,
						cle: `${s.couche}:${e.element}`,
						signe: t.signe,
						couleur: t.couleur,
						nomType: t.nom,
						nommees: nommees(e)
					});
		}
	const { zone } = ctx;
	const hotels = new Map(ctx.communes.map((c) => [c.slug, c.hotel]));
	const dans = (p: [number, number] | undefined) =>
		!!p && !!zone && p[0] >= zone[0] && p[0] <= zone[2] && p[1] >= zone[1] && p[1] <= zone[3];
	// Avant le premier affichage de la carte, la zone est celle du canton : tout y est.
	const dansZone = (l: LigneFil) =>
		reglages.portee === 'canton' ||
		!zone ||
		(l.position ? dans(l.position) : l.communes.some((c) => dans(hotels.get(c))));

	// À venir d'abord, le plus proche en tête ; puis le plus récent d'abord.
	const avenir = (l: LigneFil) => l.date > ctx.aujourdhui;
	lignes.sort(
		(a, b) =>
			Number(avenir(b)) - Number(avenir(a)) || (avenir(a) ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date))
	);
	const sansCommune = lignes.filter((l) => l.communes.length === 0);
	const gardees = lignes.filter((l) => l.communes.length > 0 && dansZone(l));

	const jours: VueFil['jours'] = [];
	for (const l of gardees) {
		if (avenir(l)) continue;
		const dernier = jours.at(-1);
		if (dernier?.date === l.date) dernier.entrees.push(l);
		else jours.push({ date: l.date, entrees: [l] });
	}
	return {
		pannes: sources.filter((s) => s.etat === 'panne').map(({ couche, nom }) => ({ couche, nom })),
		chargement: sources.some((s) => s.etat === 'chargement'),
		puces,
		sansCommune,
		aideSansCommune: sources.flatMap((s) => s.sansCommune ?? []).join(' · ') || null,
		avenir: gardees.filter(avenir),
		jours,
		compteur: gardees.length
	};
}
