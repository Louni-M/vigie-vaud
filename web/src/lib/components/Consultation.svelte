<script lang="ts">
	import { PROCEDURE_PERMIS } from '#lib/labels.js';
	import { deNom } from '#lib/registre/elision.js';

	let { commune }: { commune: string } = $props();
	const uid = $props.id();
</script>

<!--
	Résumé neutre : le détail est sur la page de l’État de Vaud sur la procédure (PROCEDURE_PERMIS). Un encadré dans la
	fiche, donc dans <main> : une note titrée et non un <aside>, qui serait un repère complémentaire hors du niveau
	supérieur.
-->
<div class="encadre" role="note" aria-labelledby="{uid}-titre">
	<h4 id="{uid}-titre">Consulter le dossier</h4>
	<p>
		Pendant l’enquête publique, le dossier complet (plans, descriptif) peut être consulté à l’administration
		communale {deNom(commune)}, au greffe ou au service technique. Renseignez-vous auprès de la commune pour les
		horaires.
	</p>
	<p>
		La loi permet aussi de déposer par écrit, dans le délai d’enquête, des observations ou une opposition motivée.
		Les étapes de la procédure, des oppositions au recours, sur la page de l’État de Vaud&nbsp;:
		<a href={PROCEDURE_PERMIS} target="_blank" rel="noopener">L’enquête publique&nbsp;: ce que prévoit la loi</a>.
	</p>
	<p class="muted">Informations générales, sans valeur de conseil juridique.</p>
</div>

<style>
	/* L'encadré de consultation en creux, l'orange en tête, comme l'encadré d'action de Protection des données. */
	.encadre {
		display: grid;
		gap: 8px;
		border-top: var(--rule-bar) solid var(--color-accent);
		padding: var(--space-md) var(--space-md) var(--space-lg);
		background: var(--color-paper-2);
		font-family: var(--font-body);
		font-size: 0.9375rem;
		line-height: 1.45;
	}
	h4 {
		margin: 0;
		font-family: var(--font-display);
		font-size: 15px;
		color: var(--color-ink);
	}
	p {
		margin: 0;
	}
	.muted {
		font-size: 12.5px;
	}
	/* Les liens soulignés : au survol, le soulignement s'épaissit. */
	a:hover {
		text-decoration-thickness: var(--rule-bar, 2px);
	}
</style>
