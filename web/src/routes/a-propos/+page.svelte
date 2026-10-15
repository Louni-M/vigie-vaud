<script lang="ts">
	import { resolve } from '$app/paths';
	import { COURRIEL, DEPOT } from '#lib/config.js';
	import { COUCHES } from '#lib/registre/couches.js';
	import { grouperSources, libelleVoie, SENS_VOIES, SOURCES } from '#lib/sources.js';

	// La liste Sources est générée depuis sources.json : une source ajoutée y apparaît sous la couche qui la
	// déclare, ou sous « Carte et communes » si aucune couche ne la déclare.
	const groupes = grouperSources(COUCHES, SOURCES);
	/** Une source par voie d'accès employée, pour la légende des voies. */
	const voies = [...new Map(SOURCES.map((s) => [s.voie_acces, s])).values()];
</script>

<svelte:head>
	<title>À propos – Vigie Vaud</title>
	<meta
		name="description"
		content="Vigie Vaud rassemble sur une carte ce qui se passe dans chaque commune vaudoise. D’où viennent ses données, et leurs limites."
	/>
</svelte:head>

<main class="page texte">
	<h1>À propos</h1>
	<p class="chapeau">
		<strong>Vigie Vaud</strong> est un tableau de bord du canton de Vaud. Il rassemble sur une carte ce qui se passe
		dans chaque commune, pour que chaque habitante et chaque habitant sache ce qui se prépare près de chez soi.
	</p>
	<p>
		Le site informe ; il ne prend pas position sur ce qu’il montre. C’est un projet citoyen et non commercial,
		indépendant de l’administration cantonale et des communes : il n’est ni publié, ni validé par elles.
	</p>

	<h2>Les couches</h2>

	<h3>Permis</h3>
	<p>
		Les demandes de permis de construire mises à l’enquête publique, tirées de la couche « Demandes de permis de
		construire (enquête publique) » des géodonnées de l’État de Vaud, gérée par la Centrale des autorisations en
		matière de construction (CAMAC).
	</p>
	<p>
		<strong>Ces données sont dépourvues de foi publique</strong> : seule la publication dans la
		<a
			href="https://www.vd.ch/territoire-et-construction/permis-de-construire/faq/avis-denquete/publication-fao"
			target="_blank"
			rel="noopener">Feuille des avis officiels (FAO)</a
		>
		fait foi. Chaque dossier renvoie vers son avis d’enquête officiel.
	</p>
	<p>
		<strong>Ce site ne stocke ni ne rediffuse ces données</strong>, comme le demande la norme DCG 8401 : c’est votre
		navigateur qui interroge directement, à chaque visite, le service public du canton (ogc.vd.ch). Vous voyez donc
		toujours l’état actuel de la couche cantonale.
	</p>
	<p>
		Chaque dossier est rattaché à une commune d’après sa position, croisée avec les limites communales actuelles de
		swisstopo : un ancien dossier d’une commune fusionnée apparaît donc sous la commune d’aujourd’hui.
	</p>
	<p>
		Pour recevoir par courriel chaque nouvel avis d’enquête autour d’une adresse, l’État de Vaud propose un service
		gratuit :
		<a href="https://www.vd.ch/prestation/sabonner-aux-avis-denquete" target="_blank" rel="noopener">InfoCamac</a>.
		Les règles de l’enquête publique (consultation, observations, oppositions, recours) sont résumées sur la page
		<a href={resolve('/enquete-publique')}>L’enquête publique : ce que prévoit la loi</a>.
	</p>

	<h3>Hôtels de ville</h3>
	<p>
		Un marqueur par commune, placé sur le siège de son administration communale : l’adresse vient de l’annuaire de
		l’Union des communes vaudoises, et sa position du répertoire officiel des adresses de bâtiments de swisstopo. Un
		clic sur le marqueur ouvre la fiche de la commune. Cette couche est permanente : elle reste toujours affichée.
	</p>
	<p>
		Le marqueur tombe toujours sur la partie terrestre de la commune, jamais dans le lac. Quand le siège n’a pas pu
		être placé, le marqueur est posé sur un point de la commune en terre ferme, et la fiche indique
		« position approximative ». Les anciennes communes n’ont pas de marqueur : on les retrouve par la recherche, qui
		mène à la commune d’aujourd’hui.
	</p>

	<h2 id="sources">Sources</h2>
	<p>
		Chaque source est citée avec son attribution, sa licence et sa voie d’accès. L’état de chaque source et les
		communes qu’elle couvre sont sur la page <a href={resolve('/couverture')}>Couverture</a>.
	</p>
	<ul class="voies">
		{#each voies as s (s.voie_acces)}
			<li><strong>{libelleVoie(s)}</strong> : {SENS_VOIES[s.voie_acces]}.</li>
		{/each}
	</ul>
	{#each groupes as g (g.titre)}
		<h3>{g.titre}</h3>
		<ul class="sources">
			{#each g.sources as s (s.id)}
				<li>
					<span class="nom">{s.nom}</span>
					<a href={s.attribution.lien} target="_blank" rel="noopener">{s.attribution.texte}</a>
					<span class="details">Licence : {s.attribution.licence} · Voie d’accès : {libelleVoie(s)}</span>
				</li>
			{/each}
		</ul>
	{/each}

	<h2>Contact</h2>
	<p>
		Pour tout ce qui touche une personne (un nom mal masqué, une demande de retrait, vos droits sur vos données),
		écrivez à <a href="mailto:{COURRIEL}">{COURRIEL}</a>. Pour le reste (une erreur, une source, une suggestion),
		ouvrez une issue sur le <a href="{DEPOT}/issues" target="_blank" rel="noopener">dépôt public</a>.
	</p>

	<h2>Licence et protection des données</h2>
	<p>
		<a href={DEPOT} target="_blank" rel="noopener">Code source</a> sous licence AGPL-3.0. Les données restent sous les
		conditions de leur source, citées ci-dessus.
	</p>
	<p>
		Ce que le site publie sur des personnes, et ce que votre visite transmet : voir
		<a href={resolve('/protection-des-donnees')}>Protection des données</a>.
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
		margin: 34px 0 8px;
		scroll-margin-top: calc(var(--header-h) + 12px);
	}
	h3 {
		font-size: 17px;
		margin: 22px 0 6px;
	}
	.chapeau {
		font-size: 17px;
	}
	.voies {
		font-size: 14px;
		color: var(--muted);
		padding-left: 20px;
	}
	.sources {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 10px;
		overflow-wrap: anywhere;
	}
	.sources li {
		display: grid;
		gap: 1px;
		padding: 10px 14px;
		border: 1px solid var(--line);
		border-radius: 8px;
		background: var(--surface);
		font-size: 14px;
	}
	.nom {
		font-weight: 600;
	}
	.details {
		font-size: 13px;
		color: var(--muted);
	}
</style>
