import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import Page from './+page.svelte';

/** Le texte de la page, sans balises, commentaires ni espaces en trop. */
const texte = render(Page)
	.body.replace(/<!--[\s\S]*?-->/g, '')
	.replace(/<[^>]+>/g, '')
	.replace(/\s+/g, ' ');

describe('Protection des données, destinataires', () => {
	it('dit que l’État de Vaud reçoit l’adresse IP pour les permis et les routes, la zone affichée pour les permis seulement', () => {
		expect(texte).toContain(
			'L’État de Vaud (ogc.vd.ch, Suisse), pour les permis de construire et les restrictions de circulation : votre adresse IP et, pour les permis, la zone affichée.'
		);
	});

	it('ne nomme l’État de Vaud qu’une fois : les restrictions n’ajoutent aucun destinataire', () => {
		expect(texte.match(/L’État de Vaud \(/g)).toHaveLength(1);
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
