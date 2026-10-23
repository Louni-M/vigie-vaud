// L'À propos avec des communes lues sur leur site : la page rendue sur un `sources.json` de test, qui déclare
// deux plateformes, trois communes couvertes et une non couverte, en plus des sources réelles.
import { render } from 'svelte/server';
import { describe, expect, it, vi } from 'vitest';
import { sourceNonCouverte, sourceSite } from '#tests/faux-conseils.js';
import type { FichierSources, Plateforme, Source } from '#lib/schema.js';

vi.mock('../../../../sources.json', async (importOriginal) => {
	const reel = ((await importOriginal()) as { default: FichierSources }).default;
	const plateforme = (id: string, nom: string): Plateforme => ({
		id,
		nom,
		editeur: `Éditeur de ${nom}`,
		variantes: [{ id: 'seances', marqueur: 'marqueur', niveaux: [['seances']] }]
	});
	const commune = (ofs: number, idPlateforme: string): Source =>
		sourceSite({
			id: `site-${ofs}`,
			nom: `Conseil communal de ${ofs} (site de la commune)`,
			attribution: {
				texte: `Commune ${ofs}`,
				lien: `https://${ofs}.ch/conseil`,
				licence: 'Actes officiels (art. 5 LDA) : métadonnées et liens seulement'
			},
			couverture: { communes: [ofs], mode: 'scrape' },
			conseil: { body_key: String(ofs), donne: ['seances'] },
			site: {
				plateforme: idPlateforme,
				variante: 'seances',
				seances: `https://${ofs}.ch/seances`
			}
		});
	// Déclarée comme le veut #154 : sa raison, sa plateforme seule, ni conseil ni sonde.
	const nonCouverte = sourceNonCouverte('preavis_seuls', { bfs: 5790, nom: '5790', site: 'https://5790.ch' });
	const fichier: FichierSources = {
		plateformes: [plateforme('i-web', 'i-web'), plateforme('quicksite', 'Quicksite')],
		sources: [...reel.sources, commune(5643, 'i-web'), commune(5891, 'quicksite'), nonCouverte, commune(5642, 'i-web')]
	};
	return { default: fichier };
});

const { default: Page } = await import('./+page.svelte');

/** Le texte de la page, sans balises ni espaces en trop. */
const texte = render(Page)
	.body.replace(/<!--[\s\S]*?-->/g, '')
	.replace(/<[^>]+>/g, '')
	.replace(/\s+/g, ' ');

describe('À propos, avec des communes lues sur leur site', () => {
	it('suit les conseils d’OpenParlData du compte des communes lues, par plateforme, sans la non couverte', () => {
		expect(texte).toContain(
			'(OpenParlData) : séances seulement ; et 3 communes dont Vigie Vaud lit le site : i-web (2), Quicksite (1). Couverture ›'
		);
	});

	it('donne ce nombre dans la section Conseils', () => {
		expect(texte).toContain('Les conseils de 3 communes sont lus sur le site de leur commune, une fois par jour');
	});

	it('cite les sites des communes en une seule entrée des Sources, avec leurs plateformes et leur licence', () => {
		expect(texte).toContain(
			'Sites des communes Les sites des communes dont Vigie Vaud lit le conseil, sur i-web et Quicksite : chaque commune, avec le lien vers son site et son état, est sur la page Couverture. Licence : Actes officiels (art. 5 LDA) : métadonnées et liens seulement · Voie d’accès : Cron'
		);
		expect(texte).not.toContain('Commune 5643');
		expect(texte).not.toContain('Commune de 5790');
		expect(texte.match(/Sites des communes/g)).toHaveLength(1);
	});
});
