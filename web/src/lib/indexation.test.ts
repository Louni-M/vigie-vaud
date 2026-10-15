import { describe, expect, it } from 'vitest';
import { adresseCanonique, robots, sitemap } from './indexation.js';

const SITE = 'https://louni-m.github.io/vigie-vaud';

describe('adresse canonique d’une page', () => {
	it('est absolue, construite depuis l’adresse publique du site', () => {
		expect(adresseCanonique(SITE, '/')).toBe('https://louni-m.github.io/vigie-vaud/');
		expect(adresseCanonique(SITE, '/couverture')).toBe('https://louni-m.github.io/vigie-vaud/couverture');
		expect(adresseCanonique(SITE, '/commune/pully')).toBe('https://louni-m.github.io/vigie-vaud/commune/pully');
	});

	it('suit l’adresse publique quand elle change (nom de domaine)', () => {
		expect(adresseCanonique('https://vigievaud.ch', '/commune/pully')).toBe('https://vigievaud.ch/commune/pully');
		expect(adresseCanonique('https://vigievaud.ch', '/')).toBe('https://vigievaud.ch/');
	});

	it('n’a jamais de paramètres ni de fragment', () => {
		expect(adresseCanonique(SITE, '/commune/pully?d=248845&vue=46.5,6.6,14')).toBe(
			'https://louni-m.github.io/vigie-vaud/commune/pully'
		);
		expect(adresseCanonique(SITE, '/?couches=permis#carte')).toBe('https://louni-m.github.io/vigie-vaud/');
	});
});

describe('sitemap.xml', () => {
	it('liste l’accueil, les pages fixes et chaque commune, en adresses absolues', () => {
		expect(sitemap(SITE, ['pully', 'bourg-en-lavaux'])).toBe(
			`<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://louni-m.github.io/vigie-vaud/</loc></url>
<url><loc>https://louni-m.github.io/vigie-vaud/couverture</loc></url>
<url><loc>https://louni-m.github.io/vigie-vaud/a-propos</loc></url>
<url><loc>https://louni-m.github.io/vigie-vaud/enquete-publique</loc></url>
<url><loc>https://louni-m.github.io/vigie-vaud/protection-des-donnees</loc></url>
<url><loc>https://louni-m.github.io/vigie-vaud/commune/pully</loc></url>
<url><loc>https://louni-m.github.io/vigie-vaud/commune/bourg-en-lavaux</loc></url>
</urlset>
`
		);
	});

	it('a 305 adresses pour les 300 communes, sur l’adresse publique en configuration', () => {
		const slugs = Array.from({ length: 300 }, (_, i) => `commune-${i}`);
		expect(sitemap('https://vigievaud.ch', slugs).match(/<loc>https:\/\/vigievaud\.ch\//g)).toHaveLength(305);
	});
});

describe('robots.txt', () => {
	it('autorise tout et donne l’adresse absolue du sitemap', () => {
		expect(robots('https://vigievaud.ch')).toBe(
			'User-agent: *\nDisallow:\n\nSitemap: https://vigievaud.ch/sitemap.xml\n'
		);
	});
});
