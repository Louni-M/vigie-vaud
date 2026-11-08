<script lang="ts">
	import { PROCEDURE_PERMIS } from '#lib/labels.js';

	// L'ancienne page « L'enquête publique » (#165) : supprimée au profit de la page de l'État de Vaud, son adresse
	// y renvoie, pour les liens et favoris qui y mènent encore. Hors du sitemap, et non indexée.
</script>

<svelte:head>
	<title>L’enquête publique – Vigie Vaud</title>
	<meta name="robots" content="noindex" />
	<meta http-equiv="refresh" content="0; url={PROCEDURE_PERMIS}" />
	<link rel="canonical" href={PROCEDURE_PERMIS} />
</svelte:head>

<main class="page" id="contenu" tabindex="-1">
	<h1>L’enquête publique</h1>
	<p>
		Cette page a déménagé&nbsp;: les étapes de l’enquête publique et de la procédure du permis de construire sont
		décrites sur la page de l’État de Vaud,
		<a href={PROCEDURE_PERMIS}>Les étapes de la procédure du permis de construire</a>.
	</p>
</main>
