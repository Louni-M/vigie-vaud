import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import config from '../../../../config.json';
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

/** Ce qui suit le titre `<h2>` d'identifiant donné, jusqu'au titre `<h2>` suivant. */
const sectionH2 = (id: string) => {
	const debut = html.indexOf(`<h2 id="${id}">`);
	expect(debut, `section #${id}`).toBeGreaterThan(-1);
	const suite = html.slice(debut);
	const fin = suite.indexOf('<h2', 1);
	return fin === -1 ? suite : suite.slice(0, fin);
};

describe('À propos, section du robot communal', () => {
	const robot = sectionH2('robot');

	it('est la section où mène le lien du User-Agent du robot', () => {
		const lien = new URL(`${config.site}/a-propos#robot`);
		expect(lien.pathname.endsWith('/a-propos')).toBe(true);
		expect(html).toContain(`<h2 id="${lien.hash.slice(1)}">`);
	});

	it('dit qui est le robot : ses deux noms, et qu’il n’est pas un robot d’IA', () => {
		expect(texte(robot)).toContain('VigieVaud-sonde');
		expect(texte(robot)).toContain('VigieVaud-import');
		expect(texte(robot)).toContain('pas un robot d’IA');
	});

	it('dit ce qu’il lit et ce qu’il garde', () => {
		expect(texte(robot)).toContain(
			'La page de liste des Séances du conseil, les pages des Séances et des Objets récents, et la page des membres'
		);
		expect(texte(robot)).toContain('des métadonnées et des liens');
		expect(texte(robot)).toContain('aucun texte intégral');
		expect(texte(robot)).toContain('ne republie aucun document');
	});

	it('donne son rythme en chiffres', () => {
		expect(texte(robot)).toContain('Une fois par jour, une requête à la fois');
		expect(texte(robot)).toContain('au moins 5 secondes entre deux requêtes vers un même réseau');
		expect(texte(robot)).toContain('au plus 60 requêtes par commune');
		expect(texte(robot)).toContain('rattrapage');
	});

	it('donne ses règles, le droit en une phrase, et pourquoi le filtrer par adresse IP ne marche pas', () => {
		expect(texte(robot)).toMatch(/robots\.txt.*Crawl-delay.*VigieVaud/);
		expect(texte(robot)).toContain('User-agent: *');
		expect(texte(robot)).toContain('429 ou 503');
		expect(texte(robot)).toContain(
			'Les actes officiels ne sont pas protégés par le droit d’auteur (art. 5 LDA) ; le robot n’en garde que les métadonnées et le lien.'
		);
		expect(texte(robot)).toContain('GitHub Actions');
		expect(texte(robot)).toContain('jamais par l’adresse IP');
	});

	it('donne l’arrêt par robots.txt en premier, puis par courriel en 7 jours, et le ralentissement par Crawl-delay', () => {
		const t = texte(robot);
		expect(t).toContain('User-agent: VigieVaud Disallow: /');
		expect(t).toContain('dès le lendemain');
		expect(t).toContain(`écrire à ${config.courriel}`);
		expect(t).toContain('dans les 7 jours');
		expect(t.indexOf('Disallow: /')).toBeLessThan(t.indexOf('dans les 7 jours'));
		expect(t).toContain('Crawl-delay: 30');
	});

	it('dit que ce qui est déjà importé reste, et renvoie à Protection des données pour une personne', () => {
		expect(texte(robot)).toContain('Ce qui est déjà importé reste en ligne');
		expect(robot).toContain('href="/protection-des-donnees#retrait"');
	});
});

describe('À propos, section Conseils', () => {
	const conseils = section(couches, 'Conseils');

	it('dit que des conseils sont lus sur le site de leur commune, par le robot, et y renvoie', () => {
		expect(texte(conseils)).toContain('lus sur le site de leur commune, une fois par jour');
		expect(conseils).toContain('href="#robot"');
	});

	it('dit que le niveau varie, que le contenu des documents n’est pas lu, et jusqu’où remonte l’archive', () => {
		expect(texte(conseils)).toContain('« objets et séances », « séances et préavis » ou « séances seulement »');
		expect(texte(conseils)).toContain('les pages et les noms des fichiers, pas le contenu des documents');
		expect(texte(conseils)).toContain('un préavis n’a donc ni statut ni auteur·e, et rien n’est deviné');
		expect(texte(conseils)).toContain('aussi loin que le site');
		expect(texte(conseils)).toContain('premier import');
	});
});
