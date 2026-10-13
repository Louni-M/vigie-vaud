import { error } from '@sveltejs/kit';
import { getCommuneResume, getCommunes, getMeta } from '#lib/data.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	const communes = await getCommunes(fetch);
	const commune = communes.find((c) => c.slug === params.slug);
	if (!commune) error(404, 'Commune introuvable');
	// Seuls les dossiers actifs et récents sont intégrés à la page ; l'historique complet
	// est chargé à la demande.
	const resume = await getCommuneResume(fetch, commune.slug);
	return {
		commune,
		actifs: resume.actifs,
		recents: resume.recents,
		parAnnee: resume.par_annee,
		meta: await getMeta(fetch)
	};
};
