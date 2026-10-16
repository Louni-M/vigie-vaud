<script lang="ts">
	/*
	 * PROTOTYPE (ticket #51) : en tête de l'onglet Conseil et de la fiche du Grand Conseil, la prochaine séance si
	 * elle est annoncée, sinon la dernière, avec les premiers points de son ordre du jour (repris de la variante C).
	 */
	import { dateDe, detailsDe, jourLong, seancesDe } from './donnees.svelte.js';

	let { conseil, ouvrir }: { conseil: string | null; ouvrir: (id: string) => void } = $props();
	const seances = $derived(seancesDe(conseil));
	const tete = $derived(seances.avenir.at(-1) ?? seances.passees[0]);
</script>

{#if tete}
	<div class="tete">
		<p class="etiquette">{tete.age < 0 ? 'Prochaine séance' : 'Dernière séance'}</p>
		<button type="button" class="date" onclick={() => ouvrir(tete.id)}>{jourLong.format(dateDe(tete))} ›</button>
		{#key tete.id}
			{#await detailsDe(tete)}
				<p class="note">Ordre du jour…</p>
			{:then d}
				{#if d.ordreDuJour.length}
					<ol>
						{#each d.ordreDuJour.slice(0, 5) as p, i (i)}
							<li>{#if p.objet}<button type="button" class="point" onclick={() => ouvrir(p.objet!)}>{p.titre}</button>{:else}{p.titre}{/if}</li>
						{/each}
					</ol>
					{#if d.ordreDuJour.length > 5}<button type="button" class="plus" onclick={() => ouvrir(tete.id)}>Les {d.ordreDuJour.length} points ›</button>{/if}
				{:else}
					<p class="note">Ordre du jour pas encore publié.</p>
				{/if}
			{:catch}
				<p class="note">Ordre du jour indisponible.</p>
			{/await}
		{/key}
		{#if tete.age >= 0}<p class="note">Prochaine séance pas encore annoncée.</p>{/if}
	</div>
{/if}

<style>
	.tete { padding: 10px 12px; border-radius: 8px; background: #e3f2f4; border-left: 4px solid #0b7285; }
	.etiquette { margin: 0; font-size: 12px; font-weight: 600; color: #0b7285; }
	.date { padding: 0; border: 0; background: none; font: inherit; font-size: 15px; font-weight: 700; cursor: pointer; text-align: left; }
	ol { margin: 6px 0 0; padding-left: 20px; font-size: 13px; }
	ol li { margin: 2px 0; display: list-item; }
	.point { padding: 0; border: 0; background: none; font: inherit; color: var(--accent); text-align: left; cursor: pointer; text-decoration: underline; }
	.note { margin: 4px 0 0; font-size: 12px; color: var(--muted); }
	.plus { margin-top: 4px; padding: 0; border: 0; background: none; font: inherit; font-size: 13px; color: var(--accent); cursor: pointer; }
</style>
