<script lang="ts">
	import { AUDIENCE } from '#lib/audience.js';
	import { COURRIEL } from '#lib/config.js';
	import { canonique } from '#lib/indexation.js';

	// Deux parties (#16) : ce que le site publie sur des personnes (ADR 0007), puis la déclaration exigée par
	// l'art. 19 nLPD (responsable, finalités, destinataires et leur pays). Tout ce qui parle de GoatCounter
	// n'apparaît que si la mesure d'audience est activée à la construction (`VITE_GOATCOUNTER`).
</script>

<svelte:head>
	<title>Protection des données – Vigie Vaud</title>
	<meta
		name="description"
		content="Ce que Vigie Vaud publie sur des personnes, et ce que votre visite transmet : responsable, finalités, destinataires et vos droits."
	/>
	<link rel="canonical" href={canonique('/protection-des-donnees')} />
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
	<p>
		Pour les conseils, les auteur·e·s des objets (motions, interpellations, postulats…) sont nommé·e·s, avec leur
		parti, puisque ce sont des élu·e·s. Les autres noms de personnes qui apparaissent dans les titres des objets et
		dans les ordres du jour des séances sont remplacés par « [particulier] » avant publication, lors de l’import
		quotidien, et leurs coordonnées (adresse, téléphone, courriel) par « [coordonnées] » : ils n’atteignent jamais
		le dépôt de données public. Les pétitions n’affichent pas leurs
		auteur·e·s. Si un nom est passé à travers, écrivez à <a href="mailto:{COURRIEL}">{COURRIEL}</a> : il est retiré,
		historique du dépôt de données public compris. Le texte d’origine reste chez OpenParlData et sur le site du
		conseil.
	</p>

	<h2>Ce que votre visite transmet</h2>
	<p>
		Le site ne demande aucun compte et ne pose aucun cookie. Afficher une page et sa carte passe toutefois par les
		services ci-dessous, qui reçoivent au moins l’adresse IP de votre appareil. Cette déclaration répond à
		l’art. 19 de la loi fédérale sur la protection des données (nLPD).
	</p>

	<h3>Responsable</h3>
	<p>Louni Merk, joignable à <a href="mailto:{COURRIEL}">{COURRIEL}</a>.</p>

	<h3>Finalités</h3>
	<ul>
		<li>afficher le site et sa carte ;</li>
		<li>assurer la sécurité de l’hébergement ;</li>
		{#if AUDIENCE}
			<li>établir des statistiques de visite agrégées.</li>
		{/if}
	</ul>

	<h3>Destinataires</h3>
	<!--
		Liste écrite à la main : ce sont des services, pas des sources. À revoir à chaque nouvelle source Direct
		(sources.json, voie_acces « direct ») : le navigateur l'interroge lui-même, c'est donc un nouveau
		destinataire de l'adresse IP des visiteurs.
	-->
	<ul class="destinataires">
		<li>
			<strong>GitHub Pages</strong> (GitHub, États-Unis), qui héberge le site et ses données : votre adresse IP, enregistrée pour
			la sécurité de l’hébergement. GitHub est certifié selon le Swiss-U.S. Data Privacy Framework.
		</li>
		{#if AUDIENCE}
			<li>
				<strong>GoatCounter</strong> (Irlande, serveurs en Finlande et en Allemagne), la mesure d’audience : à
				chaque page vue, il reçoit votre adresse IP, le nom de votre navigateur et le chemin de la page
				(<code>/commune/pully</code>), sans ses paramètres : ni le centre de la carte, ni le dossier ouvert, ni la
				page d’où vous venez. Il ne pose aucun cookie, ne conserve pas votre adresse IP et ne garde que des
				totaux.
			</li>
		{/if}
		<li>
			<strong>swisstopo</strong> (Office fédéral de topographie, Suisse), pour le fond de carte et la recherche
			d’adresses : votre adresse IP, la zone affichée et le texte d’une recherche d’adresse.
		</li>
		<li>
			<strong>L’État de Vaud</strong> (<code>ogc.vd.ch</code>, Suisse), pour les permis de construire : votre
			adresse IP et la zone affichée.
		</li>
	</ul>
	<p>
		<strong>« Autour de moi »</strong> : la position de votre appareil n’est envoyée à personne ; la carte charge
		ensuite la zone autour d’elle auprès de swisstopo et du canton, comme pour tout déplacement de la carte.
	</p>

	<h3>Vos droits</h3>
	<p>
		Pour exercer vos droits d’accès et de rectification, écrivez à
		<a href="mailto:{COURRIEL}">{COURRIEL}</a>.
	</p>

	{#if AUDIENCE}
		<h3>Statistiques de visite</h3>
		<p>
			Les statistiques de GoatCounter sont publiques :
			<a href={AUDIENCE.tableau} target="_blank" rel="noopener">tableau de bord de Vigie Vaud</a>.
		</p>
	{/if}
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
	h3 {
		font-size: 17px;
		margin: 20px 0 6px;
	}
	.destinataires li + li {
		margin-top: 6px;
	}
</style>
