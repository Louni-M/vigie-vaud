<script lang="ts">
	/*
	 * Aperçu de ce qui est ouvert, en bas de la carte sur téléphone : il laisse choisir avant d'ouvrir la fiche.
	 * Le registre rend celui d'une commune (« Pully · Voir la fiche › », sans résumé par couche en J0) ; l'`Apercu`
	 * de la couche rend celui de l'élément ouvert. La croix ferme la fiche, et l'aperçu avec elle.
	 */
	import type { Commune } from '#lib/types.js';
	import type { Registre } from './registre.svelte.js';
	import type { Chargeur } from './types.js';

	let { registre, commune, onvoir }: { registre: Registre; commune: Commune; onvoir: () => void } = $props();

	const couche = $derived(
		registre.couches.find((c) => c.id === registre.ouvert?.couche && c.composants.Apercu) ?? null
	);
	const chargerApercu = (c: NonNullable<typeof couche>) =>
		registre.composant(c, 'Apercu') as ReturnType<Chargeur<unknown, { voir: () => void }>>;
</script>

<div class="apercu">
	{#if couche && registre.ouvert}
		{#key `${registre.ouvert.couche}:${registre.ouvert.element}`}
			{#await chargerApercu(couche) then module}
				<module.default ctx={registre.contexte(couche)} voir={onvoir} />
			{:catch}
				<button class="commune" type="button" onclick={onvoir}>
					<strong>{commune.nom}</strong> · <span>Voir la fiche ›</span>
				</button>
			{/await}
		{/key}
	{:else}
		<button class="commune" type="button" onclick={onvoir}>
			<strong>{commune.nom}</strong> · <span>Voir la fiche ›</span>
		</button>
	{/if}
	<button class="fermer" type="button" aria-label="Fermer l’aperçu de {commune.nom}" onclick={registre.fermerFiche}>
		×
	</button>
</div>

<style>
	.apercu {
		position: relative;
		border-radius: 10px;
		box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
	}
	/* Place pour la croix, en haut à droite. */
	.apercu > :global(:first-child) {
		padding-right: 48px;
	}
	.commune {
		display: block;
		width: 100%;
		min-height: 52px;
		padding: 12px 14px;
		border: 0;
		border-radius: 10px;
		background: var(--surface);
		font: inherit;
		font-size: 15px;
		text-align: left;
		color: var(--muted);
		cursor: pointer;
	}
	.commune strong {
		font-size: 17px;
		color: var(--text);
	}
	.commune span {
		color: var(--accent);
		font-weight: 600;
	}
	.fermer {
		position: absolute;
		top: 0;
		right: 0;
		width: 44px;
		height: 44px;
		border: 0;
		background: none;
		font-size: 24px;
		line-height: 1;
		color: var(--muted);
		cursor: pointer;
	}
</style>
