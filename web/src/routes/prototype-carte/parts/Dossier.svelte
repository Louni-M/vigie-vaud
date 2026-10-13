<script lang="ts">
	// PROTOTYPE jetable (ticket #7) : fiche d'un dossier ; le lien vers la commune ouvre la fiche commune sur place.
	import DossierFiche from '#lib/components/DossierFiche.svelte';
	import type { Dossier } from '#lib/types.js';
	import type { Proto } from '../proto.svelte.js';
	let { p, d }: { p: Proto; d: Dossier } = $props();
	function intercepter(e: MouseEvent) {
		const a = (e.target as HTMLElement).closest('a');
		if (!a?.pathname.includes('/commune/')) return;
		e.preventDefault();
		const c = p.communeDe(d);
		if (c) p.ouvrirCommune(c);
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div onclick={intercepter}><DossierFiche {d} /></div>
