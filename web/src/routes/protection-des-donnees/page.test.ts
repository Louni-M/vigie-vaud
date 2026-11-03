import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import Page from './+page.svelte';

const html = render(Page).body;

/** Le texte d'un fragment de la page, sans balises, commentaires ni espaces en trop. */
const sansBalises = (s: string) =>
	s
		.replace(/<!--[\s\S]*?-->/g, '')
		.replace(/<[^>]+>/g, '')
		.replace(/\s+/g, ' ')
		.trim();

/** Le texte de la page. */
const texte = sansBalises(html);

describe('Protection des données, destinataires', () => {
	const ligneVaud = sansBalises(html.match(/<tr[^>]*data-destinataire="vd"[^>]*>([\s\S]*?)<\/tr>/)![1]);

	it('dit que l’État de Vaud reçoit l’adresse IP pour les permis et les routes, la zone affichée pour les permis seulement', () => {
		expect(ligneVaud).toContain(
			'L’État de Vaud (ogc.vd.ch), pour les permis de construire et les restrictions de circulation'
		);
		expect(ligneVaud).toContain('Suisse');
		expect(ligneVaud).toContain('votre adresse IP et, pour les permis, la zone affichée');
	});

	it('ne nomme l’État de Vaud qu’une fois : les restrictions n’ajoutent aucun destinataire', () => {
		expect(texte.match(/L’État de Vaud \(/g)).toHaveLength(1);
	});
});

describe('Protection des données, sommaire et ancres', () => {
	const ids = [...html.matchAll(/<h[23][^>]*\bid="([^"]+)"/g)].map((m) => m[1]);

	it('donne une ancre à chaque intertitre', () => {
		const intertitres = html.match(/<h[23][\s>]/g) ?? [];
		expect(ids).toHaveLength(intertitres.length);
	});

	it('ne renvoie qu’à des intertitres qui existent', () => {
		const liens = [...html.matchAll(/href="#([^"]+)"/g)].map((m) => m[1]);
		expect(liens.length).toBeGreaterThan(0);
		for (const l of liens) expect(ids).toContain(l);
	});
});

describe('Protection des données, vos droits', () => {
	it('cite l’accès sous 30 jours, la rectification, l’effacement et l’interdiction', () => {
		expect(texte).toContain('droit d’accès, art. 25 nLPD');
		expect(texte).toContain('dans les 30 jours (art. 18 OPDo)');
		expect(texte).toContain('faire rectifier une donnée inexacte (art. 32 al. 1 nLPD)');
		expect(texte).toContain('faire effacer une donnée, ou interdire un traitement');
	});
});

describe('Protection des données, élu·e·s connu·e·s et retrait', () => {
	it('dit que la liste des élu·e·s connu·e·s est publique, en clair, sans limite de durée, et où elle est', () => {
		expect(texte).toContain('élu·e·s connu·e·s');
		expect(texte).toContain('publique, en clair, sans limite de durée');
		expect(texte).toMatch(/conseils\/(&lt;|<)n° OFS(&gt;|>)\/membres\.json/);
	});

	it('dit d’où elle vient et pourquoi elle ne se vide pas', () => {
		expect(texte).toContain('auteur·e·s de ses Objets');
		expect(texte).toContain('page des membres');
		expect(texte).toContain('ne se vide pas');
		expect(texte).toContain('les mentions faites dans l’exercice du mandat restent');
	});

	it('dit que des élu·e·s sont masqué·e·s par défaut, que c’est voulu, et qu’on ne démasque pas sur demande', () => {
		expect(texte).toContain('en cas de doute, le site masque');
		expect(texte).toContain('ne démasque personne sur demande');
		expect(texte).toContain('la seule voie est la page des membres');
	});

	it('promet le retrait d’un nom dans les 7 jours, par courriel jamais par une issue, et dit comment il tient', () => {
		expect(texte).toContain('dans les 7 jours');
		expect(texte).toContain('jamais par une issue, qui publierait le nom');
		expect(texte).toContain('historique du dépôt de données public compris');
		expect(texte).toContain('une correction pour cet élément');
		expect(texte).toContain('à chaque import et à chaque rattrapage');
	});
});
