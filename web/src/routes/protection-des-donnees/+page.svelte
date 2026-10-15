<script lang="ts">
	import { COURRIEL } from '#lib/config.js';

	// Première partie seulement (ce que le site publie sur des personnes, ADR 0007), reprise de l'ancienne page
	// À propos. La déclaration de l'art. 19 nLPD (« Ce que votre visite transmet ») et la mesure d'audience
	// s'ajoutent avec #36.
</script>

<svelte:head>
	<title>Protection des données – Vigie Vaud</title>
	<meta
		name="description"
		content="Ce que Vigie Vaud publie sur des personnes : élu·e·s nommé·e·s, particuliers masqués."
	/>
</svelte:head>

<main class="page texte">
	<h1>Protection des données</h1>

	<h2>Ce que le site publie sur des personnes</h2>
	<p>
		Les élu·e·s sont nommé·e·s, puisqu’ils exercent un mandat public. Les noms de particuliers sont masqués ; les
		entreprises et les collectivités restent nommées.
	</p>
	<p>
		Pour les permis de construire, le site ne reprend pas les noms de propriétaire, de requérant ou d’architecte des
		avis officiels : seulement la nature des travaux, leur description, les dates et le statut. Lorsqu’une
		description mentionne un particulier (« pour le compte de M. … »), son nom est remplacé automatiquement par
		« [particulier] », dans votre navigateur, avant affichage. Ce masquage automatique peut laisser passer un cas
		isolé : il suffit de le signaler à <a href="mailto:{COURRIEL}">{COURRIEL}</a> pour qu’il soit corrigé. Les avis
		officiels, eux, contiennent ces informations pendant la durée de l’enquête.
	</p>
</main>

<style>
	.texte {
		line-height: 1.55;
	}
	h1 {
		margin: 6px 0 12px;
		line-height: 1.2;
	}
	h2 {
		font-size: 21px;
		margin: 28px 0 8px;
	}
</style>
