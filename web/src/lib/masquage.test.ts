import { describe, expect, it } from 'vitest';
import { masquerNoms } from './masquage.js';

// La même table que `CAS_DU_SITE` de `pipeline/tests/test_masquage.py`, cas pour cas : le cron masque les titres des
// conseils comme le site masque les descriptions des permis. Un cas ajouté d'un côté s'ajoute de l'autre.
// `null` : le titre ne change pas.
const CAS: [string, string | null][] = [
	['Construction d’une villa pour le compte de Dupont Jean', 'Construction d’une villa pour le compte de [particulier]'],
	['Recours pour le compte de Swisscom SA', null],
	['Transformation pour le compte de Immobilière Rive S.A.', 'Transformation pour le compte de Immobilière Rive SA'],
	[
		'Pétition de M. Paul Exemple et consorts (312 signatures) : « Pour un parc à chiens »',
		'Pétition de [particulier] et consorts (312 signatures) : « Pour un parc à chiens »'
	],
	['Pétition de Mme et M. Exemple pour un trottoir', 'Pétition de [particulier] pour un trottoir'],
	['Pétition de Madame Exemple', 'Pétition de [particulier]'],
	['Postulat de M. Loris SOCCHI : « Nos beaux murs gris»', 'Postulat de [particulier] : « Nos beaux murs gris»'],
	['Postulat de MM. Jean Dupont et Loris Socchi : « Des bancs »', 'Postulat de [particulier] : « Des bancs »'],
	['Interpellation de Mme Anne-Laure Métraux : « Quel avenir ? »', 'Interpellation de [particulier] : « Quel avenir ? »'],
	['Villa pour le compte de M. J.-P. Martin', 'Villa pour le compte de [particulier]'],
	['Agrandissement pour le compte de Commune de Lutry', null],
	['Abri pour le compte de la Fondation Les Oliviers', null],
	['Rénovation pour le compte de l’Hoirie Favre', null],
	['Pose d’un velux pour compte d’Ébéniste Rochat S.à r.l.', 'Pose d’un velux pour compte d’Ébéniste Rochat Sàrl'],
	['Garage pour le compte de Rossi Marco - Bianchi Anna', 'Garage pour le compte de [particulier] - [particulier]'],
	['Garage pour le compte de Rossi Marco, architecte', 'Garage pour le compte de [particulier], architecte'],
	['Couvert pour le compte de Dupont Jean avec garage', 'Couvert pour le compte de [particulier] avec garage'],
	['Recours pour le compte des Époux Rochat', 'Recours pour le compte des [particulier]'],
	['Simple question Laurence Cretegny et consorts - Galère La Liberté', null],
	['Covid 2020 six ans pour revenir en arrière', null]
];

describe('masquerNoms, même table que le cron', () => {
	it.each(CAS)('%s', (titre, attendu) => {
		expect(masquerNoms(titre)).toBe(attendu ?? titre);
	});
});
