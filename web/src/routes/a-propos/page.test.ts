import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import Page from './+page.svelte';

const VD_RESTRICTIONS =
	'https://www.vd.ch/mobilite/loffre-de-mobilite-a-votre-disposition/transports-individuels-motorises-tim/restrictions-de-circulation-et-travaux';

/** Le HTML de la page, sans les commentaires d'hydratation ni les classes de style que Svelte y pose. */
const html = render(Page)
	.body.replace(/<!--.*?-->/g, '')
	.replace(/ class="svelte-\w+"/g, '')
	.replace(/ svelte-\w+(?=")/g, '');
const [couches, sources] = html.split('<h2 id="sources">');

/** Le texte d'un morceau de HTML, sans balises ni espaces en trop. */
const texte = (morceau: string) =>
	morceau
		.replace(/<[^>]+>/g, '')
		.replace(/\s+/g, ' ')
		.trim();

/** Ce qui suit le titre `<h3>` donné, jusqu'au titre suivant. */
const section = (morceau: string, titre: string) => {
	const titreHtml = `<h3>${titre}</h3>`;
	expect(morceau, `titre « ${titre} »`).toContain(titreHtml);
	const suite = morceau.slice(morceau.indexOf(titreHtml) + titreHtml.length);
	const fin = suite.search(/<h[23][ >]/);
	return fin === -1 ? suite : suite.slice(0, fin);
};

describe('À propos, liste Sources', () => {
	it('montre la DGMR sous Routes, avec sa licence et sa voie d’accès, et nulle part ailleurs', () => {
		expect(texte(section(sources, 'Routes'))).toContain(
			'Restrictions de circulation DGMR (MapServer/596 et 595) Géodonnées État de Vaud (DGMR) Licence : Norme DCG 8401, sans rediffusion · Voie d’accès : Direct'
		);
		expect(texte(section(sources, 'Carte et communes'))).not.toContain('DGMR');
	});
});

describe('À propos, section Routes', () => {
	const routes = section(couches, 'Routes');

	it('vient après Conseils et son rattachement, avant la liste Sources', () => {
		expect(couches.indexOf('<h3>Routes</h3>')).toBeGreaterThan(couches.indexOf('id="rattachement"'));
	});

	it('tient en quatre paragraphes courts', () => {
		expect(routes.match(/<p[ >]/g)).toHaveLength(4);
	});

	it('dit ce que sont les données, d’où elles viennent, et renvoie à la page du canton', () => {
		expect(texte(routes)).toContain('restrictions de circulation en cours et à venir');
		expect(texte(routes)).toContain('DGMR');
		expect(texte(routes)).toContain('fermetures, déviations, feux et restrictions particulières');
		expect(texte(routes)).toContain('géodonnées de l’État de Vaud');
		expect(routes).toContain(`href="${VD_RESTRICTIONS}"`);
	});

	it('dit leur portée : surtout les routes cantonales, pas toujours les communales, jamais les autoroutes', () => {
		expect(texte(routes)).toContain('surtout sur les routes cantonales');
		expect(texte(routes)).toContain('traversées de localité et chemins communaux');
		expect(texte(routes)).toContain('n’y figurent pas toujours');
		expect(texte(routes)).toContain('les autoroutes pas du tout');
	});

	it('dit qu’elles sont lues en direct, sans stockage ni rediffusion, et que la signalisation fait foi', () => {
		expect(texte(routes)).toContain('ne stocke ni ne rediffuse');
		expect(texte(routes)).toContain('DCG 8401');
		expect(texte(routes)).toContain('n’en garde aucune trace');
		expect(routes).toMatch(/<strong>La signalisation sur place fait foi<\/strong>/);
	});

	it('explique en une phrase le rattachement aux communes', () => {
		expect(texte(routes)).toContain(
			'rattachée à chaque commune où son tracé parcourt au moins 20 m, sinon à celle qui en contient la plus grande part ; une déviation l’est à toutes les communes qu’elle traverse'
		);
	});
});
