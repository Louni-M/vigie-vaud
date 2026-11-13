import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import Consultation from './Consultation.svelte';

/** Le texte de l'encadré, sans balises, commentaires ni espaces en trop. */
const texte = (commune: string) =>
	render(Consultation, { props: { commune } })
		.body.replace(/<!--.*?-->/g, '')
		.replace(/<[^>]+>/g, '')
		.replace(/\s+/g, ' ');

describe('encadré « Consulter le dossier »', () => {
	it.each([
		['Pully', 'administration communale de Pully,'],
		['Aigle', 'administration communale d’Aigle,'],
		['Le Mont-sur-Lausanne', 'administration communale du Mont-sur-Lausanne,'],
		['Les Clées', 'administration communale des Clées,']
	])('nomme la commune %s après « de »', (commune, attendu) => {
		expect(texte(commune)).toContain(attendu);
	});
});
