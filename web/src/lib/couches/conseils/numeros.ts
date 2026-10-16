// Reconnaissance d'un numéro d'Objet tapé dans la recherche, par sa seule forme : aucune donnée n'est lue, le
// fichier d'archive ne l'est qu'à l'ouverture (`localiser`). Chaque conseil a sa forme et ses préfixes, relevés
// dans OpenParlData (tous les numéros du Grand Conseil et de Lausanne, octobre 2026) : un préfixe inconnu n'est
// pas un numéro, et « 25 rue 12 » reste une adresse.
import type { Source } from '#lib/schema.js';
import { SOURCES } from '#lib/sources.js';
import { sourceDuConseil } from './cles.js';

/** La forme des numéros d'un conseil, telle qu'OpenParlData les donne. */
export interface FormeNumero {
	/** Clé du conseil dans le dépôt de données. */
	conseil: string;
	/** Ce que le résultat dit du conseil : « Grand Conseil », « Lausanne ». */
	nom: string;
	/**
	 * `annee-prefixe` : `26_INT_140` (Grand Conseil, numéro sans zéro de tête) ;
	 * `prefixe-annee` : `INT26/056` (Lausanne, numéro sur 3 chiffres).
	 */
	ordre: 'annee-prefixe' | 'prefixe-annee';
	prefixes: readonly string[];
	/**
	 * Année (sur 2 chiffres) depuis laquelle tous les numéros suivent la forme canonique. Avant, le Grand Conseil
	 * écrit tantôt `07_INT_004`, tantôt `8_LEG_124` : le numéro est gardé tel qu'il est tapé.
	 */
	reguliereDepuis?: number;
}

export const FORMES_NUMEROS: readonly FormeNumero[] = [
	{
		conseil: 'vd',
		nom: 'Grand Conseil',
		ordre: 'annee-prefixe',
		prefixes: ['INT', 'HQU', 'QUE', 'MOT', 'POS', 'LEG', 'RAP', 'PAR', 'PET', 'RES', 'INI', 'DET', 'GRA', 'REP'],
		reguliereDepuis: 21
	},
	{
		conseil: '5586',
		nom: 'Lausanne',
		ordre: 'prefixe-annee',
		// Postulat, interpellation, préavis, question écrite, pétition, divers (COMC, PD), compte d'attente, projet
		// de règlement, motion.
		prefixes: ['POS', 'INT', 'PREA', 'Q', 'PE', 'COMC', 'CA', 'PR', 'MOT', 'PD']
	}
];

/** Un numéro reconnu : la clé de l'Objet et ce qu'affiche la recherche. */
export interface NumeroReconnu {
	cle: string;
	/** À la forme canonique du conseil : `26_INT_140`, `INT26/056`. */
	numero: string;
	/** Nom du conseil pour la recherche : « Grand Conseil », « Lausanne ». */
	nom: string;
}

/** La clé d'un Objet, comme `cle_objet` du cron : la barre oblique devient `-`, un espace `_`. */
export const cleObjet = (conseil: string, numero: string) =>
	`${conseil}/${numero.trim().replace(/\s+/g, '_').replace(/\//g, '-')}`;

const sansZeros = (chiffres: string) => String(Number(chiffres));
const sur = (n: number, chiffres: string) => sansZeros(chiffres).padStart(n, '0');

/** Le numéro à la forme canonique de ce conseil, ou `null` si les morceaux tapés n'en ont pas la forme. */
function canonique(forme: FormeNumero, morceaux: string[]): string | null {
	if (forme.ordre === 'annee-prefixe') {
		const [annee, prefixe, numero] = morceaux;
		if (morceaux.length !== 3 || !/^\d{1,2}$/.test(annee) || !/^\d{1,4}$/.test(numero)) return null;
		if (!forme.prefixes.includes(prefixe) || Number(numero) === 0) return null;
		const reguliere = Number(annee) >= (forme.reguliereDepuis ?? 0);
		return reguliere ? `${sur(2, annee)}_${prefixe}_${sansZeros(numero)}` : `${annee}_${prefixe}_${numero}`;
	}
	let [prefixe, annee, numero] = morceaux;
	// `int26056` : l'année et le numéro collés, l'année sur 2 chiffres.
	if (morceaux.length === 2 && /^\d{3,5}$/.test(annee)) [annee, numero] = [annee.slice(0, 2), annee.slice(2)];
	else if (morceaux.length !== 3) return null;
	if (!forme.prefixes.includes(prefixe) || !/^\d{1,2}$/.test(annee) || !/^\d{1,4}$/.test(numero)) return null;
	if (Number(numero) === 0 || Number(numero) > 999) return null;
	return `${prefixe}${sur(2, annee)}/${sur(3, numero)}`;
}

/**
 * Les Objets dont la saisie a la forme du numéro, un par conseil qui donne des Objets dans `sources.json`. Tolère
 * les espaces, tirets, barres, points et soulignés, la casse et les zéros de tête (`26 int 140`, `26-INT-140`,
 * `int 26/56`).
 */
export function reconnaitreNumero(saisie: string, sources: readonly Source[] = SOURCES): NumeroReconnu[] {
	const texte = saisie.trim().toUpperCase();
	if (!/^[A-Z0-9][A-Z0-9\s_\-/.]*$/.test(texte)) return [];
	const morceaux = texte.match(/[A-Z]+|\d+/g) ?? [];
	return FORMES_NUMEROS.flatMap((forme) => {
		if (!sourceDuConseil(forme.conseil, sources)?.conseil?.donne.includes('objets')) return [];
		const numero = canonique(forme, morceaux);
		return numero ? [{ cle: cleObjet(forme.conseil, numero), numero, nom: forme.nom }] : [];
	});
}
