<script lang="ts">
	// PROTOTYPE jetable (ticket #7) : badge de fraîcheur d'une source.
	import { libelleBadge, type Proto } from '../proto.svelte.js';
	let { p, source }: { p: Proto; source: string } = $props();
	const s = $derived(p.sources[source]);
</script>

<span class="badge" class:millesime={s.sorte === 'millesime'} title="Sorte de fraîcheur : {s.sorte}">
	<i></i>{libelleBadge(s, p.maintenant)}
</span>

<style>
	.badge {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 2px 8px;
		border-radius: 999px;
		background: #eef6ee;
		color: #2b5e34;
		font-size: 11.5px;
		white-space: nowrap;
		line-height: 1.5;
	}
	.badge i {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #2b8a3e;
	}
	.millesime {
		background: #eef1f6;
		color: #4a5670;
	}
	.millesime i {
		background: #8b95a8;
	}
</style>
