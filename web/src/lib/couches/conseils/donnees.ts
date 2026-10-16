// Module de données de la couche Conseils, partagé par ses composants : il lit les fichiers que le cron publie sur
// les Pages du dépôt de données (fichiers de lecture et archive, ADR 0015). Le site n'y vérifie que `version` : le
// contenu est valide au JSON Schema dès l'écriture, côté cron.
import { DONNEES } from '#lib/config.js';
import type { IndexConseils } from '#lib/schema.js';

/** Seule version des fichiers des conseils que le site connaît. */
export const VERSION_CONSEILS = 1;

export interface DonneesConseils {
	/**
	 * `conseils/index.json` : les conseils couverts, dans l'ordre de `sources.json`, et le nombre d'Objets du Grand
	 * Conseil rattachés à chaque commune. Lu une fois par visite ; rejette s'il est injoignable, absent ou d'une
	 * version inconnue, et la demande suivante le relit.
	 */
	index(): Promise<IndexConseils>;
}

export interface Options {
	fetch: typeof fetch;
	/** Adresse de base des Pages du dépôt de données, sans barre finale. */
	donnees?: string;
}

export function creerDonneesConseils({ fetch: f, donnees = DONNEES }: Options): DonneesConseils {
	/** Un fichier du dépôt de données, par son chemin ; rejette s'il n'est pas lisible dans une version connue. */
	async function lire<T>(chemin: string): Promise<T> {
		const reponse = await f(`${donnees}/${chemin}`);
		if (!reponse.ok) throw new Error(`${chemin} : HTTP ${reponse.status}`);
		const contenu = (await reponse.json()) as { version?: unknown } | null;
		if (contenu?.version !== VERSION_CONSEILS)
			throw new Error(`${chemin} : version inconnue (${String(contenu?.version)})`);
		return contenu as T;
	}

	let index: Promise<IndexConseils> | null = null;

	return {
		index() {
			if (!index) {
				const lecture = lire<IndexConseils>('conseils/index.json');
				lecture.catch(() => {
					if (index === lecture) index = null;
				});
				index = lecture;
			}
			return index;
		}
	};
}

/** Les données des conseils de la visite en cours. */
export const conseils = creerDonneesConseils({ fetch: (entree, init) => fetch(entree, init) });
