/*
 * PROTOTYPE (ticket #45), à jeter : objets et séances FICTIFS, en attendant OpenParlData (#46). Les dates sont
 * relatives à aujourd'hui pour que le fil cantonal ait toujours des nouveautés.
 */

export type Conseil = 'Grand Conseil' | 'Conseil communal';

export interface ElementConseil {
	id: string;
	sorte: 'objet' | 'seance';
	/** Conseil communal : la commune du conseil ; Grand Conseil : `null`. */
	conseil: string | null;
	/** Type d'objet (« Motion »…) ; pour une séance, « Séance ». */
	type: string;
	titre: string;
	auteur?: string;
	statut?: string;
	/** Il y a combien de jours. */
	age: number;
	/** Communes rattachées (slugs) : celle du conseil, ou celles citées dans le texte d'un objet du Grand Conseil. */
	communes: string[];
	ordreDuJour?: string[];
}

const e = (x: ElementConseil) => x;

export const ELEMENTS: ElementConseil[] = [
	// Grand Conseil, objets rattachés par le nom d'une commune
	e({ id: 'gc-26-int-142', sorte: 'objet', conseil: null, type: 'Interpellation', titre: 'Fermeture du bureau de poste de Bussigny : quel accès aux services pour l’Ouest lausannois ?', auteur: 'M. Dupraz', statut: 'Déposée', age: 0, communes: ['bussigny'] }),
	e({ id: 'gc-26-mot-31', sorte: 'objet', conseil: null, type: 'Motion', titre: 'Pour une liaison cyclable continue entre Morges et Lausanne', auteur: 'Mme Rochat', statut: 'Renvoyée en commission', age: 1, communes: ['morges', 'lausanne'] }),
	e({ id: 'gc-26-que-88', sorte: 'objet', conseil: null, type: 'Question', titre: 'Le gymnase d’Aigle sera-t-il agrandi avant 2030 ?', auteur: 'M. Chablais', statut: 'Déposée', age: 2, communes: ['aigle'] }),
	e({ id: 'gc-26-pos-19', sorte: 'objet', conseil: null, type: 'Postulat', titre: 'Inondations de la Broye : un plan d’action pour Payerne et la plaine', auteur: 'Mme Pidoux', statut: 'Prise en considération', age: 4, communes: ['payerne'] }),
	e({ id: 'gc-26-int-139', sorte: 'objet', conseil: null, type: 'Interpellation', titre: 'Chantier de la gare de Renens : quelles mesures pour les commerçants ?', auteur: 'M. Gay', statut: 'Réponse du Conseil d’État', age: 6, communes: ['renens'] }),
	// Grand Conseil, sans rattachement (aucune commune citée)
	e({ id: 'gc-26-mot-30', sorte: 'objet', conseil: null, type: 'Motion', titre: 'Pour des repas scolaires bio et locaux dans tout le canton', auteur: 'Mme Ferrari', statut: 'Déposée', age: 0, communes: [] }),
	e({ id: 'gc-26-pre-12', sorte: 'objet', conseil: null, type: 'Préavis', titre: 'Exposé des motifs : budget 2027 de l’État de Vaud', auteur: 'Conseil d’État', statut: 'En commission', age: 3, communes: [] }),
	e({ id: 'gc-26-que-90', sorte: 'objet', conseil: null, type: 'Question', titre: 'Combien d’apprenti·e·s dans l’administration cantonale ?', auteur: 'M. Wyss', statut: 'Déposée', age: 5, communes: [] }),
	e({ id: 'gc-seance-1020', sorte: 'seance', conseil: null, type: 'Séance', titre: 'Séance du Grand Conseil', age: -5, communes: [], ordreDuJour: ['Budget 2027 : entrée en matière', 'Motion Rochat (liaison cyclable Morges–Lausanne)', 'Interpellations et questions'] }),
	e({ id: 'gc-seance-1013', sorte: 'seance', conseil: null, type: 'Séance', titre: 'Séance du Grand Conseil', age: 2, communes: [], ordreDuJour: ['Loi sur l’énergie : deuxième débat', 'Postulat Pidoux (Broye)'] }),
	// Conseils communaux
	e({ id: 'lau-26-mot-07', sorte: 'objet', conseil: 'lausanne', type: 'Motion', titre: 'Végétaliser les cours d’école d’ici 2030', auteur: 'Mme Bovet', statut: 'Déposée', age: 0, communes: ['lausanne'] }),
	e({ id: 'lau-26-pre-44', sorte: 'objet', conseil: 'lausanne', type: 'Préavis', titre: 'Crédit pour la rénovation du pont Chauderon', auteur: 'Municipalité', statut: 'En commission', age: 2, communes: ['lausanne'] }),
	e({ id: 'lau-26-int-21', sorte: 'objet', conseil: 'lausanne', type: 'Interpellation', titre: 'Horaires de la piscine de Mon-Repos cet hiver', auteur: 'M. Pittet', statut: 'Réponse de la Municipalité', age: 5, communes: ['lausanne'] }),
	e({ id: 'lau-seance-1021', sorte: 'seance', conseil: 'lausanne', type: 'Séance', titre: 'Séance du Conseil communal', age: -6, communes: ['lausanne'], ordreDuJour: ['Préavis 44 : pont Chauderon', 'Motion Bovet', 'Divers'] }),
	e({ id: 'lau-seance-1007', sorte: 'seance', conseil: 'lausanne', type: 'Séance', titre: 'Séance du Conseil communal', age: 8, communes: ['lausanne'], ordreDuJour: ['Comptes intermédiaires', 'Interpellation Pittet'] }),
	e({ id: 'pul-26-pos-03', sorte: 'objet', conseil: 'pully', type: 'Postulat', titre: 'Une zone 30 sur l’avenue de Lavaux', auteur: 'M. Chevalley', statut: 'Déposé', age: 1, communes: ['pully'] }),
	e({ id: 'pul-seance-1016', sorte: 'seance', conseil: 'pully', type: 'Séance', titre: 'Séance du Conseil communal', age: -1, communes: ['pully'], ordreDuJour: ['Postulat Chevalley', 'Budget 2027'] }),
	e({ id: 'ren-26-pre-09', sorte: 'objet', conseil: 'renens', type: 'Préavis', titre: 'Construction d’un collège au Censuy', auteur: 'Municipalité', statut: 'Adopté', age: 3, communes: ['renens'] }),
	e({ id: 'pri-26-int-05', sorte: 'objet', conseil: 'prilly', type: 'Interpellation', titre: 'Sécurité du passage sous-voies de Prilly-Malley', auteur: 'Mme Nicolet', statut: 'Déposée', age: 4, communes: ['prilly'] }),
	e({ id: 'mor-26-mot-02', sorte: 'objet', conseil: 'morges', type: 'Motion', titre: 'Des bancs à l’ombre sur les quais', auteur: 'M. Mermoud', statut: 'Déposée', age: 2, communes: ['morges'] }),
	e({ id: 'mor-seance-1009', sorte: 'seance', conseil: 'morges', type: 'Séance', titre: 'Séance du Conseil communal', age: 6, communes: ['morges'], ordreDuJour: ['Motion Mermoud', 'Plan d’affectation des Halles'] }),
	e({ id: 'vev-26-pre-15', sorte: 'objet', conseil: 'vevey', type: 'Préavis', titre: 'Réaménagement de la place du Marché', auteur: 'Municipalité', statut: 'En commission', age: 1, communes: ['vevey'] }),
	e({ id: 'mon-26-que-11', sorte: 'objet', conseil: 'montreux', type: 'Question', titre: 'Où en est le parking du Marché couvert ?', auteur: 'Mme Favre', statut: 'Déposée', age: 7, communes: ['montreux'] }),
	e({ id: 'nyo-26-mot-04', sorte: 'objet', conseil: 'nyon', type: 'Motion', titre: 'Un abonnement de bus à 1 franc pour les jeunes', auteur: 'M. Bühler', statut: 'Renvoyée à la Municipalité', age: 3, communes: ['nyon'] }),
	// Yverdon : séances seulement (#44)
	e({ id: 'yve-seance-1008', sorte: 'seance', conseil: 'yverdon-les-bains', type: 'Séance', titre: 'Séance du Conseil communal', age: 7, communes: ['yverdon-les-bains'], ordreDuJour: ['Budget 2027 : premier débat', 'Divers'] }),
	e({ id: 'yve-seance-1105', sorte: 'seance', conseil: 'yverdon-les-bains', type: 'Séance', titre: 'Séance du Conseil communal', age: -21, communes: ['yverdon-les-bains'], ordreDuJour: ['Budget 2027 : vote'] })
];

export const element = (id: string) => ELEMENTS.find((x) => x.id === id);

/** Date de l'élément (dépôt d'un objet, jour d'une séance), relative à aujourd'hui. */
export function dateDe(x: ElementConseil): Date {
	const d = new Date();
	d.setHours(12, 0, 0, 0);
	d.setDate(d.getDate() - x.age);
	return d;
}

export const nomConseil = (x: ElementConseil, nomCommune: (slug: string) => string) =>
	x.conseil === null ? 'Grand Conseil' : `Conseil communal de ${nomCommune(x.conseil)}`;
