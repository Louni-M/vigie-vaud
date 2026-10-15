<script lang="ts">
	/*
	 * Échec du chargement d'une source, après la nouvelle tentative automatique : « Source en panne depuis le … »
	 * si la surveillance a constaté une panne, sinon le message de la couche (« Les permis n'ont pas pu être
	 * chargés ») et la cause vue du navigateur ; puis « Réessayer », qui recharge la source sans recharger la page.
	 * Rien n'est rendu tant que la source n'est pas en erreur : si le navigateur obtient les données, la couche
	 * s'affiche normalement, même si le cron déclare la panne.
	 */
	import { couvertureCourante } from '#lib/couverture-courante.svelte.js';
	import { etatSource, messageEchec } from '#lib/fraicheur.js';

	let { message, source }: { message: string; source: string } = $props();

	const etat = $derived(etatSource(source));
	const texte = $derived(etat && messageEchec(message, etat.erreur, couvertureCourante().etat(source)));
</script>

{#if etat && texte}
	<p class="echec" role="alert">
		<span>{texte}</span>
		<button class="bouton secondaire" type="button" onclick={() => etat.recharger()}>Réessayer</button>
	</p>
{/if}

<style>
	.echec {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 10px;
		margin: 0;
		color: var(--erreur);
	}
	.echec button {
		min-height: 32px;
		padding: 4px 10px;
		font-size: 13px;
	}
</style>
