// PROTOTYPE jetable (ticket #7) : jamais pré-générée, introuvable hors du serveur de développement.
import { error } from '@sveltejs/kit';

export const prerender = false;
export const ssr = false;

export const load = () => {
	if (!import.meta.env.DEV) error(404, 'Introuvable');
};
