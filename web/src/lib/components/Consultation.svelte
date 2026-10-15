<script lang="ts">
	import { resolve } from '$app/paths';
	import { deCommune } from '#lib/labels.js';

	let { commune }: { commune: string } = $props();
	const uid = $props.id();
</script>

<!-- Résumé neutre : le détail juridique, sourcé, est sur la page « L’enquête publique ». -->
<aside class="encadre" aria-labelledby="{uid}-titre">
	<h4 id="{uid}-titre">Consulter le dossier</h4>
	<p>
		Pendant l’enquête publique, le dossier complet (plans, descriptif) peut être consulté à l’administration
		communale {deCommune(commune)}, au greffe ou au service technique. Renseignez-vous auprès de la commune pour les
		horaires.
	</p>
	<p>
		La loi permet aussi de déposer par écrit, dans le délai d’enquête, des observations ou une opposition motivée.
		Qui peut le faire, à quelles conditions et avec quelles conséquences :
		<a href={resolve('/enquete-publique')}>L’enquête publique : ce que prévoit la loi</a>.
	</p>
	<p class="muted">Informations générales, sans valeur de conseil juridique.</p>
</aside>

<style>
	.encadre {
		display: grid;
		gap: 8px;
		border: 1px solid var(--line);
		border-left: 4px solid var(--accent);
		border-radius: 8px;
		padding: 12px 16px;
		background: var(--surface-2);
		font-size: 14px;
		line-height: 1.45;
	}
	h4 {
		margin: 0;
		font-size: 15px;
	}
	p {
		margin: 0;
	}
	.muted {
		color: var(--muted);
		font-size: 12.5px;
	}
</style>
