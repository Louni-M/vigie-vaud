/*
 * PROTOTYPE jetable (ticket #7 « Carte, panneau des couches et fiche commune ») : état en mémoire
 * partagé par les trois variantes. Rien ici n'est destiné à `main`.
 */
import { getActive, getCommunes } from '#lib/data.js';
import { STATUTS_EN_COURS } from '#lib/etat.js';
import type { Commune, Dossier, Statut } from '#lib/types.js';

export type Onglet = 'permis' | 'conseil' | 'presse' | 'meteo';

/** Une source et sa sorte de fraîcheur (décision du ticket #5). */
export interface SourceProto {
	nom: string;
	sorte: 'donnee' | 'requete' | 'millesime';
	/** `donnee` / `requete` : date ; `millesime` : année. */
	quand: Date | number;
}

export const GRAND_CONSEIL: [number, number] = [6.6357, 46.5229];

/** Position provisoire d'un hôtel de ville : centre de l'emprise (la vraie règle est le ticket #12). */
export const hdv = (c: Commune): [number, number] => [(c.bbox[0] + c.bbox[2]) / 2, (c.bbox[1] + c.bbox[3]) / 2];

type Ouvert = { commune: Commune | null; dossier: Dossier | null; gc: boolean };

export class Proto {
	communes: Commune[] = $state.raw([]);
	actifs: Dossier[] = $state.raw([]);
	consulte: Date | null = $state(null);

	/** Couche Permis activée (Hôtels de ville est permanente). */
	permis = $state(true);
	statuts: Statut[] = $state([...STATUTS_EN_COURS]);
	nature = $state('');

	commune: Commune | null = $state(null);
	dossier: Dossier | null = $state(null);
	/** Fiche du Grand Conseil ouverte (marqueur du Parlement). */
	gc = $state(false);
	onglet: Onglet = $state('permis');
	/** Montre aussi les onglets des couches à venir (J1–J5), pour juger la disposition. */
	futures = $state(false);

	/** Pile simulée du bouton retour du navigateur. */
	pile: Ouvert[] = [];

	/** Horloge, pour que les badges vieillissent sous les yeux. */
	maintenant = $state(new Date());

	constructor() {
		getCommunes(fetch).then((c) => (this.communes = c));
		getActive(fetch).then((ds) => {
			this.actifs = ds;
			this.consulte = new Date();
		});
		setInterval(() => (this.maintenant = new Date()), 15_000);
	}

	get onglets(): { id: Onglet; nom: string }[] {
		const o: { id: Onglet; nom: string }[] = [{ id: 'permis', nom: 'Permis' }];
		if (this.futures)
			o.unshift({ id: 'conseil', nom: 'Conseil' }),
				o.push({ id: 'presse', nom: 'Presse' }, { id: 'meteo', nom: 'Météo' });
		return o;
	}

	get sources(): Record<string, SourceProto> {
		const il = (min: number) => new Date(this.maintenant.getTime() - min * 60_000);
		return {
			permis: { nom: 'CAMAC', sorte: 'requete', quand: this.consulte ?? this.maintenant },
			hdv: { nom: 'swisstopo', sorte: 'millesime', quand: 2026 },
			conseil: { nom: 'OpenParlData', sorte: 'donnee', quand: il(190) },
			presse: { nom: '24 heures', sorte: 'donnee', quand: il(38) },
			meteo: { nom: 'MétéoSuisse', sorte: 'donnee', quand: il(9) }
		};
	}

	/** L'URL qu'aurait la page (ADR 0012 : commune dans le chemin, le reste en requête). */
	get url(): string {
		const q = new URLSearchParams();
		if (!this.permis) q.set('couches', 'hdv');
		if (this.dossier) q.set('d', String(this.dossier.id));
		const chemin = this.commune ? `/commune/${this.commune.slug}` : this.gc ? '/?gc' : '/';
		const s = q.toString().replaceAll('%2C', ',');
		return s ? `${chemin}${chemin.includes('?') ? '&' : '?'}${s}` : chemin;
	}

	private empiler() {
		this.pile.push({ commune: this.commune, dossier: this.dossier, gc: this.gc });
	}

	ouvrirCommune(c: Commune) {
		if (this.commune?.slug === c.slug && !this.dossier && !this.gc) return;
		this.empiler();
		this.commune = c;
		this.dossier = null;
		this.gc = false;
		if (!this.onglets.some((o) => o.id === this.onglet)) this.onglet = 'permis';
	}

	ouvrirDossier(d: Dossier) {
		if (this.dossier?.id === d.id) return;
		this.empiler();
		this.dossier = d;
		this.gc = false;
	}

	ouvrirGrandConseil() {
		this.empiler();
		this.gc = true;
		this.commune = null;
		this.dossier = null;
	}

	/** Bouton retour du navigateur (ou « ← Pully »). */
	retour() {
		const p = this.pile.pop();
		if (!p) return this.toutFermer();
		this.commune = p.commune;
		this.dossier = p.dossier;
		this.gc = p.gc;
	}

	/** Croix d'une fiche : retire le niveau du dessus. */
	fermer() {
		this.empiler();
		if (this.dossier) this.dossier = null;
		else this.commune = null;
		this.gc = false;
	}

	toutFermer() {
		this.empiler();
		this.commune = null;
		this.dossier = null;
		this.gc = false;
	}

	communeDe(d: Dossier) {
		return this.communes.find((c) => c.slug === d.slug) ?? null;
	}
}

/** Libellés de badge décidés au ticket #5. */
export function libelleBadge(s: SourceProto, maintenant: Date): string {
	if (s.sorte === 'millesime') return `édition ${s.quand} · ${s.nom}`;
	const min = Math.max(0, Math.round((maintenant.getTime() - (s.quand as Date).getTime()) / 60_000));
	const age = min < 1 ? 'à l’instant' : min < 60 ? `il y a ${min} min` : `il y a ${Math.round(min / 60)} h`;
	return `${s.sorte === 'requete' ? `consulté ${age === 'à l’instant' ? 'à l’instant' : age}` : age} · ${s.nom}`;
}
