<script lang="ts">
	/*
	 * Échec du chargement d'une source, après la nouvelle tentative automatique : le message de la couche
	 * (« Les permis n'ont pas pu être chargés »), la cause vue du navigateur et « Réessayer », qui recharge la
	 * source sans recharger la page. Rien n'est rendu tant que la source n'est pas en erreur.
	 */
	import type { EtatSourceExecution } from '#lib/fraicheur.js';

	let { message, etat }: { message: string; etat: EtatSourceExecution } = $props();

	const CAUSE = {
		hors_ligne: 'vous semblez hors ligne',
		indisponible: 'le service est indisponible pour le moment'
	};
</script>

{#if etat.erreur}
	<p class="echec" role="alert">
		<span>{message} : {CAUSE[etat.erreur]}.</span>
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
