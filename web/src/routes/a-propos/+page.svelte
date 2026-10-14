<script lang="ts">
	import { resolve } from '$app/paths';
</script>

<svelte:head>
	<title>À propos – Chantiers Vaud</title>
</svelte:head>

<main class="page">
	<h1>À propos</h1>
	<p>
		<strong>Chantiers Vaud</strong> rend visibles, sur une carte simple, toutes les demandes de permis de construire
		mises à l’enquête publique dans le canton de Vaud. L’objectif : que chaque habitante et chaque habitant puisse
		savoir ce qui se prépare près de chez soi et, au besoin, consulter le dossier pendant l’enquête. Le site
		informe sur les projets ; il ne prend pas position à leur sujet.
	</p>
	<p>
		Les règles de l’enquête publique (consultation, observations, oppositions, recours) sont résumées, avec les
		textes officiels, sur la page <a href={resolve('/infos-legales')}>Informations légales</a>.
	</p>

	<h2>D’où viennent les données ?</h2>
	<p>
		Source : Géodonnées Etat de Vaud – couche « Demandes de permis de construire (enquête publique) » gérée par la
		Centrale des autorisations en matière de construction (CAMAC). <strong>Ce site ne stocke ni ne rediffuse
		ces données</strong> : c’est votre navigateur qui interroge directement, à chaque visite, le service public
		du canton (ogc.vd.ch). Vous voyez donc toujours l’état actuel de la couche cantonale. Ces données sont
		<strong>dépourvues de foi publique</strong> : seule la publication dans la
		<a href="https://www.vd.ch/territoire-et-construction/permis-de-construire/faq/avis-denquete/publication-fao" target="_blank" rel="noopener">Feuille des avis officiels (FAO)</a>
		fait foi. Chaque fiche renvoie vers l’avis d’enquête officiel.
	</p>
	<p>
		Les communes sont attribuées en croisant l’emplacement de chaque dossier avec les limites communales
		actuelles de swisstopo (swissBOUNDARIES3D) ; un ancien dossier d’une commune fusionnée apparaît donc sous la
		commune d’aujourd’hui. Fond de carte et recherche d’adresses © swisstopo.
	</p>

	<h2>Protection des données</h2>
	<p>
		Ce site ne reprend pas les noms de propriétaire, de requérant ou d’architecte des avis officiels : seulement la
		nature des travaux, leur description, les dates et le statut. Lorsqu’une description mentionne un particulier
		(« pour le compte de M. … »), son nom est remplacé automatiquement par « [particulier] », dans votre navigateur,
		avant affichage ; les entreprises et
		collectivités restent nommées. Ce masquage automatique peut laisser passer un cas isolé : il suffit de nous le
		signaler pour qu’il soit corrigé. Les avis officiels, eux, contiennent ces informations pendant la durée de
		l’enquête.
	</p>
	<p>
		La mesure d’audience, si elle est activée, se fait sans cookie et sans donnée personnelle. La géolocalisation
		« Autour de moi » reste dans votre navigateur.
	</p>

	<h2>Recevoir une alerte</h2>
	<p>
		L’État de Vaud propose un service gratuit d’alerte par courriel pour chaque nouvel avis dans un rayon autour
		d’une adresse :
		<a href="https://www.vd.ch/prestation/sabonner-aux-avis-denquete" target="_blank" rel="noopener">InfoCamac</a>.
	</p>

	<h2>Projet</h2>
	<p>
		Projet citoyen, non commercial et indépendant de l’administration cantonale. Le code source est ouvert.
	</p>
</main>
