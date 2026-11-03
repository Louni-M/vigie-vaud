// Les phrases du diagramme du masquage (#165), en morceaux : le texte qui reste, et les noms que le masquage remplace
// ou épargne. Les noms sont inventés. L'exemple des permis est vérifié contre `masquerNoms` (exemples.test.ts) :
// le diagramme montre ce que fait vraiment le site. Celui des conseils suit les règles du cron (ADR-0007).

export interface Morceau {
	texte: string;
	/** `masque` : un particulier, remplacé à l'animation ; `elu` : un·e élu·e connu·e, qui reste lisible. */
	role?: 'masque' | 'elu';
}

export const PERMIS: Morceau[] = [
	{ texte: 'Construction d’une piscine enterrée, pour le compte de ' },
	{ texte: 'M. Paul Exemple', role: 'masque' }
];

export const CONSEIL: Morceau[] = [
	{ texte: 'Interpellation de ' },
	{ texte: 'Mme Anne Modèle', role: 'elu' },
	{ texte: '\u00a0: quel avenir pour la parcelle de ' },
	{ texte: 'M. Paul Exemple', role: 'masque' },
	{ texte: '\u00a0?' }
];

/** La phrase telle que la source la publie. */
export const avant = (morceaux: Morceau[]): string => morceaux.map((m) => m.texte).join('');

/** La phrase telle que le site la publie. */
export const apres = (morceaux: Morceau[], masque: string): string =>
	morceaux.map((m) => (m.role === 'masque' ? masque : m.texte)).join('');
