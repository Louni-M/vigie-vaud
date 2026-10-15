<script lang="ts" module>
	/*
	 * PROTOTYPE (ticket #45) : choix de la variante du fil cantonal, `?fil=A|B|C` au chargement (le registre
	 * réécrit ensuite l'adresse sans ce paramètre ; le choix reste en mémoire), flèches ← → pour passer de l'une à
	 * l'autre. Le bandeau en haut à droite ne fait pas partie du design évalué.
	 */
	export const VARIANTES = [
		{ id: 'A', nom: 'Fil au rail' },
		{ id: 'B', nom: 'Colonne Fil | Fiche' },
		{ id: 'C', nom: 'Bandeau sur la carte' }
	] as const;
	export type Variante = (typeof VARIANTES)[number]['id'];

	function initiale(): Variante {
		if (typeof location === 'undefined') return 'A';
		const v = new URLSearchParams(location.search).get('fil');
		return VARIANTES.some((x) => x.id === v) ? (v as Variante) : 'A';
	}
	export const filChoisi = $state({ variante: initiale() });
</script>

<script lang="ts">
	function aller(pas: number) {
		const i = VARIANTES.findIndex((v) => v.id === filChoisi.variante);
		filChoisi.variante = VARIANTES[(i + pas + VARIANTES.length) % VARIANTES.length].id;
	}
	function clavier(e: KeyboardEvent) {
		const a = document.activeElement as HTMLElement | null;
		if (a && (a.matches('input, textarea, select, [contenteditable]') || a.classList.contains('maplibregl-canvas'))) return;
		if (e.key === 'ArrowLeft') aller(-1);
		if (e.key === 'ArrowRight') aller(1);
	}
	const courante = $derived(VARIANTES.find((v) => v.id === filChoisi.variante)!);
</script>

<svelte:window onkeydown={clavier} />

<div class="proto" role="group" aria-label="Variantes du prototype">
	<button type="button" aria-label="Variante précédente" onclick={() => aller(-1)}>‹</button>
	<span>Fil {courante.id} · {courante.nom}</span>
	<button type="button" aria-label="Variante suivante" onclick={() => aller(1)}>›</button>
</div>

<style>
	.proto { position: fixed; z-index: 100; top: 6px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 6px; padding: 4px 6px; border-radius: 999px; background: #111; color: #fff; font: 600 13px system-ui, sans-serif; box-shadow: 0 2px 10px rgb(0 0 0 / 0.4); }
	button { border: 0; background: #333; color: #fff; width: 26px; height: 26px; border-radius: 50%; font-size: 16px; cursor: pointer; }
	span { padding: 0 6px; white-space: nowrap; }
</style>
