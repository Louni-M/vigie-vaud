// Adresses du projet. Elles sont écrites une seule fois, dans `config.json` à la racine du dépôt, que peut
// lire aussi le pipeline Python (User-Agent des sondes) : le dépôt est renommé à la fin de J0 et un nom de
// domaine viendra plus tard. Aucun autre fichier ne doit les écrire en dur.
import config from '../../../config.json';

/** Dépôt public du code (lien de la licence AGPL-3.0, issues). */
export const DEPOT: string = config.depot;
/** Courriel de contact pour tout ce qui touche une personne (retrait, droits nLPD). */
export const COURRIEL: string = config.courriel;
/** Adresse publique du site, sans barre finale (adresses canoniques, sitemap). */
export const SITE: string = config.site;
/**
 * Adresse de base des Pages du dépôt de données (`etat-sources.json`), sans barre finale. En développement,
 * `DONNEES_LOCALES` la remplace par celle d'un clone local (`scripts/donnees-locales.ts`).
 */
export const DONNEES: string = (import.meta.env.VITE_DONNEES as string | undefined) || config.donnees;
/**
 * Dépôt GitHub du dépôt de données (issues `panne-source`) : il a le propriétaire du dépôt du code, et son nom
 * est le dernier segment de l'adresse de ses Pages (`…github.io/vigie-vaud-donnees`).
 */
export const DEPOT_DONNEES: string = DEPOT.replace(/[^/]+$/, config.donnees.split('/').at(-1)!);
