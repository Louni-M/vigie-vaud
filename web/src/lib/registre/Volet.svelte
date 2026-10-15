<script lang="ts">
	/*
	 * Volet d'une couche, assemblé par le registre : interrupteur (ou « permanente »), attribution de chaque
	 * source tirée de sources.json, puis le `Volet` de la couche. Le badge de fraîcheur et le lien vers la
	 * page Couverture viendront s'ajouter ici.
	 */
	import { source } from '#lib/sources.js';
	import type { Registre } from './registre.svelte.js';
	import type { CoucheInscrite } from './types.js';

	let { couche, registre, onfermer }: { couche: CoucheInscrite; registre: Registre; onfermer: () => void } = $props();

	const active = $derived(registre.active(couche.id));
	const sources = $derived(couche.sources.map(source));
	const titre = $derived(`volet-${couche.id}`);
</script>

<section class="volet" id="volet-{couche.id}" aria-labelledby={titre}>
	<div class="tete">
		<h2 id={titre}>{couche.nom}</h2>
		{#if couche.permanente}
			<span class="permanente">permanente</span>
		{:else}
			<label class="interrupteur">
				<input
					type="checkbox"
					role="switch"
					checked={active}
					onchange={(e) => registre.activer(couche.id, e.currentTarget.checked)}
				/>
				Affichée
			</label>
		{/if}
		<button class="fermer" type="button" aria-label="Fermer le volet {couche.nom}" onclick={onfermer}>×</button>
	</div>

	<p class="attribution">
		{#each sources as s, i (s.id)}
			{#if i > 0}<span aria-hidden="true"> · </span>{/if}
			<a href={s.attribution.lien} target="_blank" rel="noopener">{s.attribution.texte}</a>
		{/each}
	</p>

	{#await registre.composant(couche, 'Volet') then module}
		{#if module}
			<module.default ctx={registre.contexte(couche)} />
		{/if}
	{:catch}
		<p class="erreur">Le volet n’a pas pu être chargé. Rechargez la page.</p>
	{/await}
</section>

<style>
	.volet {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 12px 14px 14px;
		background: var(--surface);
		border-radius: 10px;
		box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
		font-size: 14px;
	}
	.tete {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	h2 {
		flex: 1;
		margin: 0;
		font-size: 16px;
	}
	.interrupteur,
	.permanente {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		color: var(--muted);
	}
	.interrupteur {
		cursor: pointer;
	}
	.interrupteur input {
		width: 18px;
		height: 18px;
		margin: 0;
		accent-color: var(--accent);
	}
	.fermer {
		width: 32px;
		height: 32px;
		margin: -4px -6px -4px 0;
		border: 0;
		border-radius: 50%;
		background: none;
		font-size: 22px;
		line-height: 1;
		color: var(--muted);
		cursor: pointer;
	}
	.fermer:hover {
		background: var(--bg);
	}
	.attribution {
		margin: -4px 0 0;
		font-size: 12px;
		color: var(--muted);
	}
	.attribution a {
		color: inherit;
	}
	.erreur {
		margin: 0;
		color: var(--erreur);
	}
</style>
