import type { Statut } from './types';

export const STATUTS: Record<Statut, { label: string; court: string; couleur: string }> = {
	enquete: { label: 'Enquête publique en cours', court: 'À l’enquête', couleur: '#d9480f' },
	procedure: { label: 'Enquête terminée, décision attendue', court: 'Décision attendue', couleur: '#e8a317' },
	delivre: { label: 'Permis délivré', court: 'Permis délivré', couleur: '#2b8a3e' },
	realise: { label: 'Réalisé', court: 'Réalisé', couleur: '#5c6f91' },
	abandonne: { label: 'Abandonné ou refusé', court: 'Abandonné / refusé', couleur: '#868e96' },
	autre: { label: 'Autre', court: 'Autre', couleur: '#adb5bd' }
};

export const STATUTS_ORDRE: Statut[] = ['enquete', 'procedure', 'delivre', 'realise', 'abandonne'];

export const NATURES: Record<string, string> = {
	construction: 'Construction nouvelle',
	transformation: 'Transformation',
	adjonction: 'Adjonction',
	agrandissement: 'Agrandissement',
	changement: 'Changement d’affectation',
	reconstruction: 'Reconstruction après démolition',
	reconstruction_incendie: 'Reconstruction après incendie',
	renovation: 'Rénovation totale',
	demolition: 'Démolition totale',
	demolition_partielle: 'Démolition partielle',
	autre: 'Autre'
};

export const natureLabel = (n: string) => NATURES[n] ?? n;

/** « de Lausanne », « d’Aigle » */
export const deCommune = (nom: string) => (/^[aeiouyàâäéèêëîïôöûüAEIOUYÀÂÉÈÊÎÔÛ]/.test(nom) ? `d’${nom}` : `de ${nom}`);

/** Normalise un nom pour la recherche : sans accents, minuscules, ponctuation ramenée à des espaces. */
export const normaliser = (s: string) =>
	s
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '')
		.toLowerCase()
		.replace(/[-'’()\s]+/g, ' ')
		.trim();
