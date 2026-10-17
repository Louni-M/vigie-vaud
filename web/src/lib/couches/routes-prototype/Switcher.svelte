<script lang="ts">
	/* PROTOTYPE : barre flottante des variantes (flèches, ou ← → du clavier hors d'un champ). */
	let {
		variantes,
		courante,
		choisir
	}: { variantes: [string, string][]; courante: string; choisir: (v: string) => void } = $props();

	const i = $derived(Math.max(0, variantes.findIndex(([v]) => v === courante)));
	const aller = (pas: number) => choisir(variantes[(i + pas + variantes.length) % variantes.length][0]);

	function touche(e: KeyboardEvent) {
		const t = e.target as HTMLElement | null;
		if (t?.closest('input, textarea, select, [contenteditable], .maplibregl-canvas')) return;
		if (e.key === 'ArrowLeft') aller(-1);
		if (e.key === 'ArrowRight') aller(1);
	}
</script>

<svelte:window onkeydown={touche} />

<div class="proto" role="group" aria-label="Variantes du prototype">
	<button type="button" onclick={() => aller(-1)} aria-label="Variante précédente">‹</button>
	<span>Prototype Routes · <strong>{variantes[i][0]}</strong> ({variantes[i][1]})</span>
	<button type="button" onclick={() => aller(1)} aria-label="Variante suivante">›</button>
</div>

<style>
	.proto {
		position: fixed;
		left: 50%;
		bottom: 18px;
		transform: translateX(-50%);
		z-index: 10000;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 8px;
		border-radius: 999px;
		background: #111;
		color: #fff;
		font-size: 13px;
		box-shadow: 0 6px 20px rgb(0 0 0 / 0.35);
		white-space: nowrap;
	}
	button {
		width: 30px;
		height: 30px;
		border: 0;
		border-radius: 50%;
		background: #333;
		color: #fff;
		font-size: 18px;
		line-height: 1;
		cursor: pointer;
	}
	button:hover {
		background: #555;
	}
	@media (max-width: 767px) {
		.proto {
			top: 128px;
			bottom: auto;
		}
	}
</style>
