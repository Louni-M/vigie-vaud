<script lang="ts">
	/*
	 * Fiche d'un dossier ouvert, dans l'onglet Permis de sa commune : le registre a rendu le fil « Permis › n° … »
	 * au-dessus, et la remonte pour un autre dossier. Lue en direct sur le service du canton (déjà en mémoire le
	 * plus souvent : le registre vient de la chercher pour trouver la commune du dossier).
	 */
	import { untrack } from 'svelte';
	import { resolve } from '$app/paths';
	import DossierFiche from '#lib/components/DossierFiche.svelte';
	import { ErreurApi } from '#lib/api.js';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Dossier } from '#lib/types.js';
	import { permis, SOURCE, type Parametres } from './donnees.svelte.js';

	let { ctx }: { ctx: Contexte<Parametres> } = $props();

	const id = Number(untrack(() => ctx.ouvert?.element));

	let d = $state<Dossier | undefined>();
	let etat = $state<'chargement' | 'trouve' | 'absent' | 'erreur'>('chargement');
	let message = $state('');

	function charger() {
		etat = 'chargement';
		permis.fiche(id).then(
			(r) => {
				d = r;
				etat = r ? 'trouve' : 'absent';
			},
			(e) => {
				etat = 'erreur';
				message =
					e instanceof ErreurApi && e.hors_ligne
						? 'Vous semblez hors ligne : les dossiers sont lus en direct sur le service du canton.'
						: `${e instanceof ErreurApi ? e.message : 'Le dossier n’a pas pu être chargé.'} Réessayez dans un instant.`;
			}
		);
	}
	charger();
</script>

{#if etat === 'trouve' && d}
	<DossierFiche {d} />
{:else if etat === 'chargement'}
	<div class="squelette" aria-busy="true">
		<p class="muted">Chargement du dossier n° {id} auprès du service du canton…</p>
		<span style:width="35%"></span>
		<span style:width="70%" class="grand"></span>
		<span style:width="95%"></span>
		<span style:width="60%"></span>
	</div>
{:else if etat === 'absent'}
	<p>Aucun dossier n° {id} dans la couche du canton (les n° CAMAC ont 5 ou 6 chiffres).</p>
{:else}
	<p class="erreur" role="alert">
		{message}
		<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
	</p>
{/if}

<p class="source">
	{SOURCE} depuis votre navigateur ; ce site ne les stocke pas. Sans foi publique : seule la FAO fait foi.
	L’emplacement est indicatif.
	<a href={resolve('/enquete-publique')}>L’enquête publique : ce que prévoit la loi</a>
</p>

<style>
	.squelette {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.squelette span {
		display: block;
		height: 14px;
		border-radius: 7px;
		background: var(--line);
	}
	.squelette .grand {
		height: 24px;
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		color: var(--erreur);
	}
	.source {
		margin-top: 28px;
	}
</style>
