<script lang="ts">
	/*
	 * Badge de fraîcheur des sites d'une plateforme (« mis à jour il y a 45 min · sites de 19 communes »), après la
	 * liste de la rubrique Conseils communaux : un seul badge pour toutes ses communes couvertes, au lieu d'un par site.
	 * Les dates viennent de `conseils/import.json`, comme pour BadgeFraicheur.
	 */
	import { libelleBadgeSites } from '#lib/fraicheur.js';
	import { dernierImport } from '#lib/imports-conseils.js';
	import { importsCourants } from '#lib/imports-courants.svelte.js';
	import type { Source } from '#lib/schema.js';

	let { plateforme, sources }: { plateforme: string; sources: readonly Source[] } = $props();

	const imports = $derived(sources.map((s) => dernierImport(importsCourants(), s)));

	/** L'âge affiché suit l'heure : relu toutes les 30 s. */
	let maintenant = $state(new Date());
	$effect(() => {
		const t = setInterval(() => (maintenant = new Date()), 30_000);
		return () => clearInterval(t);
	});
</script>

<span class="badge" title="La plus ancienne des dernières mises à jour des sites de la plateforme {plateforme}"
	>{libelleBadgeSites(imports, maintenant)}</span
>

<style>
	.badge {
		font-size: 12px;
		font-weight: 400;
		color: var(--color-muted);
		white-space: nowrap;
	}
</style>
