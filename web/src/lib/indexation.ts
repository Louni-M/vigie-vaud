// Indexation par les moteurs de recherche (ADR 0012) : chaque page pré-générée porte une adresse canonique absolue
// et sans paramètres, et `sitemap.xml` liste ces mêmes adresses. Les deux sont construits ici, depuis l'adresse
// publique du site en configuration (`SITE`), jamais depuis l'adresse de la requête.
import { SITE } from './config.js';

/**
 * Adresse canonique d'une page : l'adresse publique du site (sans barre finale) suivie du chemin de la page, sans
 * paramètres ni fragment. Une vue de la carte (`?vue=`, `?d=`…) a la canonique de sa page.
 */
export function adresseCanonique(site: string, chemin: string): string {
	return site + chemin.replace(/[?#].*$/, '');
}

/** Adresse canonique d'une page du site, pour son `<link rel="canonical">`. */
export const canonique = (chemin: string) => adresseCanonique(SITE, chemin);

/** Pages fixes indexées, dans l'ordre du sitemap. La 404 n'en fait pas partie (elle porte `noindex`). */
export const PAGES_FIXES = ['/', '/couverture', '/a-propos', '/enquete-publique', '/protection-des-donnees'] as const;

/** Chemin de la fiche d'une commune, relatif à la base du site (ADR 0012). */
export const cheminCommune = (slug: string) => `/commune/${slug}`;

/** `sitemap.xml` : les pages fixes puis la fiche de chaque commune, en adresses canoniques. */
export function sitemap(site: string, slugs: readonly string[]): string {
	const chemins = [...PAGES_FIXES, ...slugs.map(cheminCommune)];
	return [
		'<?xml version="1.0" encoding="UTF-8"?>',
		'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
		...chemins.map((c) => `<url><loc>${adresseCanonique(site, c)}</loc></url>`),
		'</urlset>',
		''
	].join('\n');
}

/** `robots.txt` : tout est ouvert aux moteurs, et le sitemap est annoncé par son adresse absolue. */
export const robots = (site: string) => `User-agent: *\nDisallow:\n\nSitemap: ${site}/sitemap.xml\n`;
