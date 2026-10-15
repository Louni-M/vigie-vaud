/**
 * Nettoyage des descriptions et masquage des noms de particuliers, côté navigateur.
 * Portage fidèle de `clean_text` et `mask_names` du script de la version hébergée (étiquette `chantiers-hebergee`).
 *
 * Différences d'expressions régulières entre Python et JavaScript : `\w` et `\b` n'y reconnaissent que
 * l'ASCII. On les remplace par des classes Unicode explicites (`L`, `nonL`) et le drapeau `u`.
 */

const W = String.raw`[\p{L}\p{N}_]`;
/** Équivalent de `\b` devant un mot (le mot qui suit commence toujours par une lettre). */
const B = String.raw`(?<!${W})`;

const C1_RE = /[\x80-\x9f]/g;
const cp1252 = new TextDecoder('windows-1252');

/** Corrige les caractères Windows-1252 mal décodés (ex. \x92 → ’) et les espaces superflus. */
export function nettoyer(s: string | null | undefined): string {
	const corrige = (s ?? '').replace(C1_RE, (c) => {
		const r = cp1252.decode(new Uint8Array([c.charCodeAt(0)]));
		// Octets non définis en cp1252 : Python lève une erreur et les supprime.
		return r === c ? '' : r;
	});
	return [...corrige]
		.filter((ch) => ch >= ' ' || ch === '\t' || ch === '\n')
		.join('')
		.split(/[\s\x1c-\x1f\x85]+/u)
		.filter(Boolean)
		.join(' ');
}

export const MASQUE = '[particulier]';

const ENTITE_RE = new RegExp(
	B +
		String.raw`(?:S\.?A\.?|Sàrl|S\.à\.r\.l\.?|SARL|GmbH|AG|SNC|SCI|Ltd|Inc|` +
		String.raw`Swisscom|Sunrise|Salt|Orange|UPC|CFF|SBB|Migros|Coop|Banque|BCV|Raiffeisen|Poste|` +
		String.raw`Commune|Ville|Municipalit[ée]|[ÉE]tat|Canton|Conf[ée]d[ée]ration|Paroisse|[ÉE]glise|` +
		String.raw`Fondation|Association|Soci[ée]t[ée]|Coop[ée]rative|Communaut[ée]|PPE|Hoirie|Consortage|` +
		String.raw`Groupe|Holding|Immobili[eè]re?|Caisse|Assurances?|Fonds|Hôpital|H[ôo]pitaux|[ÉE]cole|Club|` +
		String.raw`Romande Energie|Services?|Infra|SI(?!${W})|Syndicat|Entreprise|Cave|Domaine|Hôtel|Restaurant)(?!${W})`,
	'iu'
);
const CIVILITE = String.raw`(?:M\.|MM\.|Mme|Mmes|Mlle|Monsieur|Madame|Messieurs|Mesdames)`;
const CIVILITE_SEULE = new RegExp(CIVILITE, 'u');
const COMPTE_RE = new RegExp(
	String.raw`(pour\s+(?:le\s+)?compte\s+(?:de\s+(?:la\s+|l[’'´]\s*|de\s+)?|d[’'´]\s*|des\s+|du\s+))` +
		String.raw`([^.,;:()/\n]+?)(?=\s*(?:[.,;:()/]|\savec\s|\set\s(?:de\s|d[’'´])|$))`,
	'giu'
);
const NOM = String.raw`[A-ZÀ-Ý](?:\.(?:-[A-ZÀ-Ý]\.)?|[\p{L}\p{N}_’'´-]*)`;
const CIVILITE_RE = new RegExp(
	String.raw`${B}${CIVILITE}(?:\s+(?:et|&)\s+${CIVILITE})*\s+${NOM}(?:\s+(?:et\s+|&\s+)?${NOM})*`,
	'gu'
);
const LIAISONS = new Set(['et', '&', 'de', 'du', 'des', 'da', 'dos', 'von', 'van', 'der', 'le', 'la']);

const majuscule = (c: string) => c !== c.toLowerCase() && c === c.toUpperCase();

/** Suite de 2 à 8 mots tous à majuscule initiale (hors liaisons), sans chiffre : « Occipinti Santo ». */
function ressembleAUnNom(segment: string): boolean {
	const mots = segment.trim().split(/\s+/u).filter(Boolean);
	const noms = mots.filter((m) => !LIAISONS.has(m.toLowerCase()));
	return noms.length >= 2 && noms.length <= 8 && !/\p{Nd}/u.test(segment) && noms.every((m) => majuscule(m[0]));
}

export function masquerNoms(s: string): string {
	// Formes juridiques avec points (« S.A. », « A.G. », « S.à r.l. ») : sinon le point coupe le segment.
	s = s.replace(new RegExp(String.raw`${B}S\.\s?A\.?(?!${W})`, 'gu'), 'SA');
	s = s.replace(new RegExp(String.raw`${B}A\.\s?G\.?(?!${W})`, 'gu'), 'AG');
	s = s.replace(new RegExp(String.raw`${B}S\.?\s?à\s?r\.?\s?l\.?(?!${W})`, 'giu'), 'Sàrl');
	// Civilités d'abord (« M. Dupont ») : le point de « M. » couperait sinon le segment « pour le compte de ».
	s = s.replace(CIVILITE_RE, MASQUE);
	return s.replace(COMPTE_RE, (_, debut: string, cible: string) => {
		const parties = cible.split(/(\s-\s)/u);
		for (let i = 0; i < parties.length; i += 2) {
			const p = parties[i];
			if (CIVILITE_SEULE.test(p) || (!ENTITE_RE.test(p) && ressembleAUnNom(p))) parties[i] = MASQUE;
		}
		return debut + parties.join('');
	});
}
