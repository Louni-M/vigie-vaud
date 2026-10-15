<script lang="ts">
	// PROTOTYPE (ticket #45) : volet minimal de la couche Conseils factice.
	import type { Contexte } from '#lib/registre/types.js';
	let { ctx }: { ctx: Contexte<undefined> } = $props();
</script>

<p class="note">
	Couche factice du prototype : objets et séances inventés. Un point violet par commune dont le conseil a des
	nouveautés. {ctx.active ? '' : '(masquée)'}
</p>

<style>
	.note {
		font-size: 13px;
		color: var(--muted);
	}
</style>
