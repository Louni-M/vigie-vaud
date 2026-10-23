<script lang="ts">
	import { resolve } from '$app/paths';
	import { COURRIEL, DEPOT, DEPOT_DONNEES } from '#lib/config.js';
	import { canonique } from '#lib/indexation.js';
	import { COUCHES } from '#lib/registre/couches.js';
	import {
		conseilsCouverts,
		grouperSources,
		libelleVoie,
		PLATEFORMES,
		phraseSitesLus,
		SENS_VOIES,
		source,
		SOURCES
	} from '#lib/sources.js';

	// La liste Sources est générée depuis sources.json : une source ajoutée y apparaît sous la couche qui la
	// déclare, ou sous « Carte et communes » si aucune couche ne la déclare. Les sources communales y sont réunies
	// en une entrée « Sites des communes ».
	const groupes = grouperSources(COUCHES, SOURCES, PLATEFORMES);
	/** Une source par voie d'accès employée, pour la légende des voies. */
	const voies = [...new Map(SOURCES.map((s) => [s.voie_acces, s])).values()];
	// La liste des conseils couverts aussi : une ligne par source qui a un bloc `conseil` et n'est pas un site,
	// puis le compte des communes lues sur leur site, par plateforme (sans les communes non couvertes).
	const conseils = conseilsCouverts(SOURCES, PLATEFORMES);
	const sitesLus = phraseSitesLus(conseils.sites);
	/** « i-web et Quicksite » : les plateformes de l'entrée « Sites des communes ». */
	const ET = new Intl.ListFormat('fr', { type: 'conjunction' });
	// Le lien vers la page vd.ch des Routes est celui de l'attribution, déclaré une fois dans sources.json.
	const DGMR = source('dgmr-restrictions');
</script>

<svelte:head>
	<title>À propos – Vigie Vaud</title>
	<meta
		name="description"
		content="Vigie Vaud rassemble sur une carte ce qui se passe dans chaque commune vaudoise. D’où viennent ses données, et leurs limites."
	/>
	<link rel="canonical" href={canonique('/a-propos')} />
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

	<h3>Conseils</h3>
	<p>
		Les <strong>Objets</strong> (motions, postulats, interpellations, décrets, préavis…) et les
		<strong>Séances</strong>, avec leur ordre du jour, du Grand Conseil et de conseils communaux. Ils viennent
		d’<a href="https://openparldata.ch" target="_blank" rel="noopener">OpenParlData</a>, une plateforme qui
		rassemble les données des parlements suisses, ou du site de la commune.
	</p>
	<p>
		À l’inverse des permis, ces données sont <strong>importées une fois par jour</strong>, puis conservées dans le
		<a href={DEPOT_DONNEES} target="_blank" rel="noopener">dépôt de données public</a> de Vigie Vaud : un Objet ou
		une Séance reste consultable même s’il disparaît de la source.
	</p>
	<p>
		Les conseils de {conseils.sites.communes} commune{conseils.sites.communes > 1 ? 's' : ''} sont lus sur le site de leur commune, une fois par jour, par le <a href="#robot">robot de Vigie Vaud</a>. Ce
		qu’on en tire dépend de ce que chaque site publie :
	</p>
	<ul>
		<li>
			le niveau varie d’une commune à l’autre : « objets et séances », « séances et préavis » ou « séances
			seulement » ;
		</li>
		<li>
			le robot lit les pages et les noms des fichiers, pas le contenu des documents : un préavis n’a donc ni statut
			ni auteur·e, et rien n’est deviné ;
		</li>
		<li>
			l’archive remonte aussi loin que le site ; si le site ne garde que les Séances récentes ou à venir, elle part
			du premier import.
		</li>
	</ul>
	<p>
		Le type d’un Objet et son statut sont ceux que donne le conseil, sans traduction ni regroupement. Les pétitions
		n’affichent pas leurs auteur·e·s, et les demandes de grâce sont écartées. Ce que le site publie sur les personnes
		nommées dans les titres est expliqué sur la page
		<a href={resolve('/protection-des-donnees')}>Protection des données</a>.
	</p>
	<p>Conseils couverts :</p>
	<ul class="conseils">
		{#each conseils.sources as c, i (c.source.id)}
			<li><strong>{c.source.nom}</strong> : {c.donne}{sitesLus || i < conseils.sources.length - 1 ? ' ;' : '.'}</li>
		{/each}
		{#if sitesLus}
			<li>{sitesLus}. <a href={resolve('/couverture')}>Couverture ›</a></li>
		{/if}
	</ul>
	<p>
		Vigie Vaud ne lit pas encore les autres conseils communaux. Ce que chaque source couvre, commune par commune, est
		sur la page <a href={resolve('/couverture')}>Couverture</a>.
	</p>

	<h3 id="rattachement">Comment les objets du Grand Conseil sont rattachés aux communes</h3>
	<p>
		Un Objet d’un conseil communal appartient à sa commune. Un Objet du Grand Conseil porte sur tout le canton :
		Vigie Vaud le rattache aux communes dont il cite le nom, et le montre dans la fiche de chacune, sous « Au Grand
		Conseil ». Les Séances du Grand Conseil ne sont rattachées à aucune commune.
	</p>
	<p>Ce rattachement est automatique. Il suit quelques règles :</p>
	<ul>
		<li>
			le site lit le titre de l’Objet et le texte de ses documents ; une commune nommée dans le titre passe avant
			celles des documents ;
		</li>
		<li>
			le nom d’une ancienne commune ou un ancien nom mène à la commune d’aujourd’hui : un Objet qui cite Gressy
			apparaît sous Yverdon-les-Bains ;
		</li>
		<li>
			un nom porté par plusieurs communes (Chavannes, Belmont, Corcelles, Romanel, Mont) n’est jamais reconnu seul,
			faute de savoir de laquelle il s’agit ;
		</li>
		<li>
			un nom qui désigne autre chose que la commune est écarté : un district ou une région (« district de Nyon »),
			une rue (« avenue de Morges »), une institution (« Université de Lausanne »), une route ou une ligne de
			transport ;
		</li>
		<li>
			quand les documents d’un Objet citent plus de dix communes, ce sont des énumérations : seul son titre
			compte.
		</li>
	</ul>
	<p>
		Des erreurs restent possibles : une commune citée en passant, ou un nom qui n’a pas été reconnu. La plupart des
		Objets ne nomment d’ailleurs aucune commune ; ils restent visibles dans la fiche du Grand Conseil. Pour
		signaler une erreur de rattachement, écrivez à <a href="mailto:{COURRIEL}">{COURRIEL}</a>, ou ouvrez une issue
		sur le <a href="{DEPOT}/issues" target="_blank" rel="noopener">dépôt public</a> : elle sera corrigée à la main.
	</p>

	<h3>Routes</h3>
	<p>
		Les restrictions de circulation en cours et à venir publiées par la Direction générale de la mobilité et des
		routes (DGMR) : fermetures, déviations, feux et restrictions particulières, tirées des géodonnées de l’État de
		Vaud. Le canton les présente aussi sur sa page
		<a href={DGMR.attribution.lien} target="_blank" rel="noopener">Restrictions de circulation et travaux</a>.
	</p>
	<p>
		Elles portent surtout sur les routes cantonales, avec quelques traversées de localité et chemins communaux. Les
		travaux sur les routes communales (à Lausanne, par exemple) n’y figurent pas toujours, et les autoroutes pas du
		tout.
	</p>
	<p>
		Comme pour les permis, <strong>ce site ne stocke ni ne rediffuse ces données</strong>, comme le demande la norme
		DCG 8401 : votre navigateur les lit directement auprès du canton, à chaque visite. Une restriction levée
		disparaît du site, qui n’en garde aucune trace. <strong>La signalisation sur place fait foi</strong>.
	</p>
	<p>
		Une restriction est rattachée à chaque commune où son tracé parcourt au moins 20 m, sinon à celle qui en contient
		la plus grande part ; une déviation l’est à toutes les communes qu’elle traverse.
	</p>

	<h2 id="robot">Le robot de Vigie Vaud</h2>
	<p>
		Pour les conseils communaux qu’OpenParlData n’expose pas, Vigie Vaud lit le site de la commune avec un robot.
		Ce qui suit s’adresse au service informatique d’une commune comme à toute personne curieuse.
	</p>
	<ul class="robot">
		<li>
			<strong>Qui.</strong> Il se présente sous les noms <code>VigieVaud-sonde</code> (la vérification quotidienne
			de la page de liste) et <code>VigieVaud-import</code> (la lecture), avec un courriel de contact et un lien vers
			cette section. Ce n’est pas un robot d’IA.
		</li>
		<li>
			<strong>Ce qu’il lit.</strong> La page de liste des Séances du conseil, les pages des Séances et des Objets
			récents, et la page des membres du conseil. Il n’en garde que des métadonnées et des liens, aucun texte
			intégral, et ne republie aucun document.
		</li>
		<li>
			<strong>Son rythme.</strong> Une fois par jour, une requête à la fois, au moins 5 secondes entre deux
			requêtes vers un même réseau, au plus 60 requêtes par commune. De temps en temps, un rattrapage de
			l’historique, lancé à la main, relit un site au même rythme.
		</li>
		<li>
			<strong>Ses règles.</strong> Il suit <code>robots.txt</code> et <code>Crawl-delay</code> sous le nom
			<code>VigieVaud</code> ; une règle faite à tous les robots (<code>User-agent: *</code>) le concerne aussi. Il
			s’arrête après une réponse 429 ou 503.
		</li>
		<li>
			<strong>Le droit.</strong> Les actes officiels ne sont pas protégés par le droit d’auteur (art. 5 LDA) ; le
			robot n’en garde que les métadonnées et le lien.
		</li>
		<li>
			<strong>Où il tourne.</strong> Sur GitHub Actions, dont les adresses IP changent. Pour le filtrer, passez par
			son User-Agent ou par <code>robots.txt</code>, jamais par l’adresse IP.
		</li>
	</ul>
	<p>Une commune qui ne veut plus être lue a deux voies :</p>
	<ol class="robot">
		<li>
			interdire <code>VigieVaud</code> dans le <code>robots.txt</code> de son site : le robot s’arrête dès le
			lendemain, sans attendre personne ;
			<pre><code>User-agent: VigieVaud
Disallow: /</code></pre>
		</li>
		<li>
			écrire à <a href="mailto:{COURRIEL}">{COURRIEL}</a> : le robot est arrêté dans les 7 jours.
		</li>
	</ol>
	<p>
		Pour seulement le ralentir, un <code>Crawl-delay</code> suffit, en secondes :
	</p>
	<pre><code>User-agent: VigieVaud
Crawl-delay: 30</code></pre>
	<p>
		Ce qui est déjà importé reste en ligne et dans le dépôt de données, comme archive d’actes officiels. Une demande
		qui touche une personne passe par le retrait décrit sur la page
		<a href={resolve('/protection-des-donnees')}>Protection des données</a>.
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
				{#if 'plateformes' in s}
					<li>
						<span class="nom">{s.nom}</span>
						<span>
							Les sites des communes dont Vigie Vaud lit le conseil{s.plateformes.length > 0
								? `, sur ${ET.format(s.plateformes)}`
								: ''} : chaque commune, avec le lien vers son site et son état, est sur la page
							<a href={resolve('/couverture')}>Couverture</a>.
						</span>
						<span class="details">Licence : {s.licence} · Voie d’accès : {libelleVoie(s)}</span>
					</li>
				{:else}
					<li>
						<span class="nom">{s.nom}</span>
						<a href={s.attribution.lien} target="_blank" rel="noopener">{s.attribution.texte}</a>
						<span class="details">Licence : {s.attribution.licence} · Voie d’accès : {libelleVoie(s)}</span>
					</li>
				{/if}
			{/each}
		</ul>
	{/each}

	<h2>Contact</h2>
	<p>
		Pour tout ce qui touche une personne (un nom mal masqué, une demande de retrait, vos droits sur vos données),
		écrivez à <a href="mailto:{COURRIEL}">{COURRIEL}</a>. Pour une erreur de rattachement, le courriel convient
		aussi bien qu’une issue. Pour le reste (une erreur, une source, une suggestion), ouvrez de préférence une issue
		sur le <a href="{DEPOT}/issues" target="_blank" rel="noopener">dépôt public</a>.
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
		scroll-margin-top: calc(var(--header-h) + 12px);
	}
	.chapeau {
		font-size: 17px;
	}
	.conseils,
	.robot {
		padding-left: 20px;
	}
	.robot li + li {
		margin-top: 6px;
	}
	pre {
		margin: 6px 0 10px;
		padding: 8px 12px;
		border: 1px solid var(--line);
		border-radius: 8px;
		background: var(--surface);
		font-size: 13px;
		overflow-x: auto;
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
