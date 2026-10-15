<script lang="ts">
	/*
	 * Badge de fraîcheur d'une source (« consulté il y a 2 min · CAMAC »), rendu par le registre sous le nom de
	 * chaque onglet et dans le volet de la couche. L'état vient du code d'accès de la source ; tant que celui-ci
	 * n'est pas chargé, la source n'a encore rien donné. Le message d'échec et « Réessayer » sont rendus à côté
	 * (EchecSource), pas dans le badge : sous le nom d'un onglet, un bouton ne peut pas en contenir un autre.
	 */
	import { etatSource, libelleBadge } from '#lib/fraicheur.js';
	import type { Source } from '#lib/schema.js';

	let { source }: { source: Source } = $props();

	const etat = $derived(etatSource(source.id) ?? { derniere: null, erreur: null });

	/** L'âge affiché suit l'heure : relu toutes les 30 s. */
	let maintenant = $state(new Date());
	$effect(() => {
		const t = setInterval(() => (maintenant = new Date()), 30_000);
		return () => clearInterval(t);
	});
</script>

<span class="badge" class:erreur={etat.erreur} title={source.nom}>{libelleBadge(source, etat, maintenant)}</span>

<style>
	.badge {
		font-size: 12px;
		font-weight: 400;
		color: var(--muted);
		white-space: nowrap;
	}
	.erreur {
		color: var(--erreur);
	}
</style>
