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
