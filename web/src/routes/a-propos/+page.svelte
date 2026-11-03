<script lang="ts">
	import { resolve } from '$app/paths';
	import '#lib/almanach/almanach.css';
	import { anime } from '#lib/almanach/anime.js';
	import Sommaire, { type Partie } from '#lib/almanach/Sommaire.svelte';
	import { insecables } from '#lib/almanach/typographie.js';
	import { COURRIEL, DEPOT, DEPOT_DONNEES } from '#lib/config.js';
	import { canonique } from '#lib/indexation.js';
	import { PROCEDURE_PERMIS } from '#lib/labels.js';
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
	import DemoRattachement from './DemoRattachement.svelte';
	import DeuxChemins from './DeuxChemins.svelte';

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
	const communesLues = `${conseils.sites.communes} commune${conseils.sites.communes > 1 ? 's' : ''}`;
	/** « i-web et Quicksite » : les plateformes de l'entrée « Sites des communes ». */
	const ET = new Intl.ListFormat('fr', { type: 'conjunction' });
	// Le lien vers la page vd.ch des Routes est celui de l'attribution, déclaré une fois dans sources.json.
	const DGMR = source('dgmr-restrictions');

	// Le sommaire (#165) suit les parties de la page ; l'intro et les diagrammes la résument sans rien y ajouter.
	const sommaire: Partie[] = [
		{
			id: 'couches',
			titre: 'Les couches',
			sous: [
				{ id: 'permis', titre: 'Permis' },
				{ id: 'hotels-de-ville', titre: 'Hôtels de ville' },
				{ id: 'conseils', titre: 'Conseils' },
				{ id: 'rattachement', titre: 'Rattachement aux communes' },
				{ id: 'routes', titre: 'Routes' }
			]
		},
		{ id: 'robot', titre: 'Le robot de Vigie Vaud' },
		{ id: 'sources', titre: 'Sources' },
		{ id: 'contact', titre: 'Contact' },
		{ id: 'licence', titre: 'Licence et protection des données' }
	];
</script>

<svelte:head>
	<title>À propos – Vigie Vaud</title>
	<meta
		name="description"
		content="Vigie Vaud rassemble sur une carte ce qui se passe dans chaque commune vaudoise. D’où viennent ses données, et leurs limites."
	/>
	<link rel="canonical" href={canonique('/a-propos')} />
</svelte:head>

<main class="almanach" data-theme="almanach">
	<div class="cadre">
		<header class="tete">
			<h1>À propos</h1>
		</header>

		<div class="intro">
			<p class="chapeau">
				<strong>Vigie Vaud</strong> est un tableau de bord du canton de Vaud. Il rassemble sur une carte ce qui se passe
				dans chaque commune, pour que chaque habitante et chaque habitant sache ce qui se prépare près de chez soi.
			</p>
			<p>
				Le site informe&nbsp;; il ne prend pas position sur ce qu’il montre. C’est un projet citoyen et non commercial,
				indépendant de l’administration cantonale et des communes&nbsp;: il n’est ni publié, ni validé par elles.
			</p>

		</div>

		<Sommaire parties={sommaire} />

		<div class="corps">
			<section class="partie" aria-labelledby="couches">
				<h2 id="couches"><span class="numero" aria-hidden="true">1</span>Les couches</h2>

				<DeuxChemins />

				<h3 id="permis">Permis</h3>
				<p>
					Les demandes de permis de construire mises à l’enquête publique, tirées de la couche «&nbsp;Demandes de permis
					de construire (enquête publique)&nbsp;» des géodonnées de l’État de Vaud, gérée par la Centrale des
					autorisations en matière de construction (CAMAC).
				</p>
				<p>
					<strong>Ces données sont dépourvues de foi publique</strong>&nbsp;: seule la publication dans la
					<a
						href="https://www.vd.ch/territoire-et-construction/permis-de-construire/faq/avis-denquete/publication-fao"
						target="_blank"
						rel="noopener">Feuille des avis officiels (FAO)</a
					>
					fait foi. Chaque dossier renvoie vers son avis d’enquête officiel.
				</p>
				<p>
					<strong>Ce site ne stocke ni ne rediffuse ces données</strong>, comme le demande la norme DCG&nbsp;8401&nbsp;:
					c’est votre navigateur qui interroge directement, à chaque visite, le service public du canton (ogc.vd.ch).
					Vous voyez donc toujours l’état actuel de la couche cantonale.
				</p>
				<p>
					Chaque dossier est rattaché à une commune d’après sa position, croisée avec les limites communales actuelles
					de swisstopo&nbsp;: un ancien dossier d’une commune fusionnée apparaît donc sous la commune d’aujourd’hui.
				</p>
				<p>
					Pour recevoir par courriel chaque nouvel avis d’enquête autour d’une adresse, l’État de Vaud propose un
					service gratuit&nbsp;:
					<a href="https://www.vd.ch/prestation/sabonner-aux-avis-denquete" target="_blank" rel="noopener"
						>InfoCamac</a
					>. Les règles de l’enquête publique (consultation, observations, oppositions, recours) sont résumées sur la
					page
					<a href={PROCEDURE_PERMIS} target="_blank" rel="noopener">L’enquête publique&nbsp;: ce que prévoit la loi</a>.
				</p>

				<h3 id="hotels-de-ville">Hôtels de ville</h3>
				<p>
					Un marqueur par commune, placé sur le siège de son administration communale&nbsp;: l’adresse vient de
					l’annuaire de l’Union des communes vaudoises, et sa position du répertoire officiel des adresses de bâtiments
					de swisstopo. Un clic sur le marqueur ouvre la fiche de la commune. Cette couche est permanente&nbsp;: elle
					reste toujours affichée.
				</p>
				<p>
					Le marqueur tombe toujours sur la partie terrestre de la commune, jamais dans le lac. Quand le siège n’a pas
					pu être placé, le marqueur est posé sur un point de la commune en terre ferme, et la fiche indique
					«&nbsp;position approximative&nbsp;». Les anciennes communes n’ont pas de marqueur&nbsp;: on les retrouve par
					la recherche, qui mène à la commune d’aujourd’hui.
				</p>

				<h3 id="conseils">Conseils</h3>
				<p>
					Les <strong>Objets</strong> (motions, postulats, interpellations, décrets, préavis…) et les
					<strong>Séances</strong>, avec leur ordre du jour, du Grand Conseil et de conseils communaux. Ils viennent
					d’<a href="https://openparldata.ch" target="_blank" rel="noopener">OpenParlData</a>, une plateforme qui
					rassemble les données des parlements suisses, ou du site de la commune.
				</p>
				<p>
					À l’inverse des permis, ces données sont <strong>importées une fois par jour</strong>, puis conservées dans le
					<a href={DEPOT_DONNEES} target="_blank" rel="noopener">dépôt de données public</a> de Vigie Vaud&nbsp;: un
					Objet ou une Séance reste consultable même s’il disparaît de la source.
				</p>
				<p>
					Les conseils de {communesLues} sont lus sur le site de leur commune, une fois par jour, par le
					<a href="#robot">robot de Vigie Vaud</a>. Ce qu’on en tire dépend de ce que chaque site publie&nbsp;:
				</p>
				<ul>
					<li>
						le niveau varie d’une commune à l’autre&nbsp;: «&nbsp;objets et séances&nbsp;», «&nbsp;séances et
						préavis&nbsp;» ou «&nbsp;séances seulement&nbsp;»&nbsp;;
					</li>
					<li>
						le robot lit les pages et les noms des fichiers, pas le contenu des documents&nbsp;: un préavis n’a donc ni
						statut ni auteur·e, et rien n’est deviné&nbsp;;
					</li>
					<li>
						l’archive remonte aussi loin que le site&nbsp;; si le site ne garde que les Séances récentes ou à venir,
						elle part du premier import.
					</li>
				</ul>
				<p>
					Le type d’un Objet et son statut sont ceux que donne le conseil, sans traduction ni regroupement. Les
					pétitions n’affichent pas leurs auteur·e·s, et les demandes de grâce sont écartées. Ce que le site publie sur
					les personnes nommées dans les titres est expliqué sur la page
					<a href={resolve('/protection-des-donnees')}>Protection des données</a>.
				</p>
				<p>Conseils couverts&nbsp;:</p>
				<ul class="conseils">
					{#each conseils.sources as c, i (c.source.id)}
						<li>
							<strong>{c.source.nom}</strong>&nbsp;: {insecables(c.donne)}{sitesLus || i < conseils.sources.length - 1
								? '\u00a0;'
								: '.'}
						</li>
					{/each}
					{#if sitesLus}
						<li>{insecables(sitesLus)}. <a href={resolve('/couverture')}>Couverture ›</a></li>
					{/if}
				</ul>
				<p>
					Vigie Vaud ne lit pas encore les autres conseils communaux. Ce que chaque source couvre, commune par commune,
					est sur la page <a href={resolve('/couverture')}>Couverture</a>.
				</p>

				<h3 id="rattachement">Comment les objets du Grand Conseil sont rattachés aux communes</h3>
				<p>
					Un Objet d’un conseil communal appartient à sa commune. Un Objet du Grand Conseil porte sur tout le
					canton&nbsp;: Vigie Vaud le rattache aux communes dont il cite le nom, et le montre dans la fiche de chacune,
					sous «&nbsp;Au Grand Conseil&nbsp;». Les Séances du Grand Conseil ne sont rattachées à aucune commune.
				</p>
				<p>Ce rattachement est automatique. Il suit quelques règles&nbsp;:</p>
				<ul>
					<li>
						le site lit le titre de l’Objet et le texte de ses documents&nbsp;; une commune nommée dans le titre passe
						avant celles des documents&nbsp;;
					</li>
					<li>
						le nom d’une ancienne commune ou un ancien nom mène à la commune d’aujourd’hui&nbsp;: un Objet qui cite
						Gressy apparaît sous Yverdon-les-Bains&nbsp;;
					</li>
					<li>
						un nom porté par plusieurs communes (Chavannes, Belmont, Corcelles, Romanel, Mont) n’est jamais reconnu
						seul, faute de savoir de laquelle il s’agit&nbsp;;
					</li>
					<li>
						un nom qui désigne autre chose que la commune est écarté&nbsp;: un district ou une région («&nbsp;district
						de Nyon&nbsp;»), une rue («&nbsp;avenue de Morges&nbsp;»), une institution («&nbsp;Université de
						Lausanne&nbsp;»), une route ou une ligne de transport&nbsp;;
					</li>
					<li>
						quand les documents d’un Objet citent plus de dix communes, ce sont des énumérations&nbsp;: seul son titre
						compte.
					</li>
				</ul>

				<DemoRattachement />

				<p>
					Des erreurs restent possibles&nbsp;: une commune citée en passant, ou un nom qui n’a pas été reconnu. La
					plupart des Objets ne nomment d’ailleurs aucune commune&nbsp;; ils restent visibles dans la fiche du Grand
					Conseil. Pour signaler une erreur de rattachement, écrivez à <a href="mailto:{COURRIEL}">{COURRIEL}</a>, ou
					ouvrez une issue sur le <a href="{DEPOT}/issues" target="_blank" rel="noopener">dépôt public</a>&nbsp;: elle
					sera corrigée à la main.
				</p>

				<h3 id="routes">Routes</h3>
				<p>
					Les restrictions de circulation en cours et à venir publiées par la Direction générale de la mobilité et des
					routes (DGMR)&nbsp;: fermetures, déviations, feux et restrictions particulières, tirées des géodonnées de
					l’État de Vaud. Le canton les présente aussi sur sa page
					<a href={DGMR.attribution.lien} target="_blank" rel="noopener">Restrictions de circulation et travaux</a>.
				</p>
				<p>
					Elles portent surtout sur les routes cantonales, avec quelques traversées de localité et chemins communaux.
					Les travaux sur les routes communales (à Lausanne, par exemple) n’y figurent pas toujours, et les autoroutes
					pas du tout.
				</p>
				<p>
					Comme pour les permis, <strong>ce site ne stocke ni ne rediffuse ces données</strong>, comme le demande la
					norme DCG&nbsp;8401&nbsp;: votre navigateur les lit directement auprès du canton, à chaque visite. Une
					restriction levée disparaît du site, qui n’en garde aucune trace.
					<strong>La signalisation sur place fait foi</strong>.
				</p>
				<p>
					Une restriction est rattachée à chaque commune où son tracé parcourt au moins 20&nbsp;m, sinon à celle qui en
					contient la plus grande part&nbsp;; une déviation l’est à toutes les communes qu’elle traverse.
				</p>
			</section>

			<section class="partie" aria-labelledby="robot">
				<h2 id="robot"><span class="numero" aria-hidden="true">2</span>Le robot de Vigie Vaud</h2>
				<p>
					Pour les conseils communaux qu’OpenParlData n’expose pas, Vigie Vaud lit le site de la commune avec un robot.
					Ce qui suit s’adresse au service informatique d’une commune comme à toute personne curieuse.
				</p>
				<ul class="robot">
					<li>
						<strong>Qui.</strong> Il se présente sous les noms <code>VigieVaud-sonde</code> (la vérification quotidienne
						de la page de liste) et <code>VigieVaud-import</code> (la lecture), avec un courriel de contact et un lien
						vers cette section. Ce n’est pas un robot d’IA.
					</li>
					<li>
						<strong>Ce qu’il lit.</strong> La page de liste des Séances du conseil, les pages des Séances et des Objets
						récents, et la page des membres du conseil. Il n’en garde que des métadonnées et des liens, aucun texte
						intégral, et ne republie aucun document.
					</li>
					<li>
						<strong>Son rythme.</strong> Une fois par jour, une requête à la fois, au moins 5&nbsp;secondes entre deux
						requêtes vers un même réseau, au plus 60&nbsp;requêtes par commune. De temps en temps, un rattrapage de
						l’historique, lancé à la main, relit un site au même rythme.
					</li>
					<li>
						<strong>Ses règles.</strong> Il suit <code>robots.txt</code> et <code>Crawl-delay</code> sous le nom
						<code>VigieVaud</code>&nbsp;; une règle faite à tous les robots (<code>User-agent: *</code>) le concerne
						aussi. Il s’arrête après une réponse 429 ou 503.
					</li>
					<li>
						<strong>Le droit.</strong> Les actes officiels ne sont pas protégés par le droit d’auteur
						(art.&nbsp;5&nbsp;LDA)&nbsp;; le robot n’en garde que les métadonnées et le lien.
					</li>
					<li>
						<strong>Où il tourne.</strong> Sur GitHub Actions, dont les adresses IP changent. Pour le filtrer, passez
						par son User-Agent ou par <code>robots.txt</code>, jamais par l’adresse IP.
					</li>
				</ul>
				<p>Une commune qui ne veut plus être lue a deux voies&nbsp;:</p>
				<ol class="arret" use:anime>
					<li>
						<span class="delai" aria-hidden="true">dès le lendemain</span>
						interdire <code>VigieVaud</code> dans le <code>robots.txt</code> de son site&nbsp;: le robot s’arrête dès le
						lendemain, sans attendre personne&nbsp;;
						<pre><code>User-agent: VigieVaud
Disallow: /</code></pre>
					</li>
					<li>
						<span class="delai" aria-hidden="true"><span class="nombre">7</span> jours au plus</span>
						écrire à <a href="mailto:{COURRIEL}">{COURRIEL}</a>&nbsp;: le robot est arrêté dans les 7&nbsp;jours.
					</li>
				</ol>
				<p>
					Pour seulement le ralentir, un <code>Crawl-delay</code> suffit, en secondes&nbsp;:
				</p>
				<pre><code>User-agent: VigieVaud
Crawl-delay: 30</code></pre>
				<p>
					Le robot suit un <code>Crawl-delay</code> jusqu’à 30&nbsp;secondes et ne le raccourcit jamais&nbsp;: au-delà,
					il ne lit plus le site.
				</p>
				<p>
					Ce qui est déjà importé reste en ligne et dans le dépôt de données, comme archive d’actes officiels. Une
					demande qui touche une personne passe par le retrait décrit sur la page
					<a href="{resolve('/protection-des-donnees')}#retrait">Protection des données</a>.
				</p>
			</section>

			<section class="partie" aria-labelledby="sources">
				<h2 id="sources"><span class="numero" aria-hidden="true">3</span>Sources</h2>
				<p>
					Chaque source est citée avec son attribution, sa licence et sa voie d’accès. L’état de chaque source et les
					communes qu’elle couvre sont sur la page <a href={resolve('/couverture')}>Couverture</a>.
				</p>
				<ul class="voies">
					{#each voies as s (s.voie_acces)}
						<li><strong>{libelleVoie(s)}</strong>&nbsp;: {insecables(SENS_VOIES[s.voie_acces])}.</li>
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
											: ''}&nbsp;: chaque commune, avec le lien vers son site et son état, est sur la page
										<a href={resolve('/couverture')}>Couverture</a>.
									</span> <span class="details">Licence&nbsp;: {insecables(s.licence)} · Voie d’accès&nbsp;:
									{libelleVoie(s)}</span>
								</li>
							{:else}
								<li>
									<span class="nom">{s.nom}</span>
									<a href={s.attribution.lien} target="_blank" rel="noopener">{s.attribution.texte}</a>
									<span class="details">Licence&nbsp;: {insecables(s.attribution.licence)} · Voie d’accès&nbsp;:
									{libelleVoie(s)}</span>
								</li>
							{/if}
						{/each}
					</ul>
				{/each}
			</section>

			<section class="partie" aria-labelledby="contact">
				<h2 id="contact"><span class="numero" aria-hidden="true">4</span>Contact</h2>
				<div class="action">
					<p>
						Pour tout ce qui touche une personne (un nom mal masqué, une demande de retrait, vos droits sur vos
						données), écrivez à <a href="mailto:{COURRIEL}">{COURRIEL}</a>. Pour une erreur de rattachement, le
						courriel convient aussi bien qu’une issue. Pour le reste (une erreur, une source, une suggestion), ouvrez
						de préférence une issue sur le <a href="{DEPOT}/issues" target="_blank" rel="noopener">dépôt public</a>.
					</p>
				</div>
			</section>

			<section class="partie" aria-labelledby="licence">
				<h2 id="licence"><span class="numero" aria-hidden="true">5</span>Licence et protection des données</h2>
				<p>
					<a href={DEPOT} target="_blank" rel="noopener">Code source</a> sous licence AGPL-3.0. Les données restent sous
					les conditions de leur source, citées ci-dessus.
				</p>
				<p>
					Ce que le site publie sur des personnes, et ce que votre visite transmet&nbsp;: voir
					<a href={resolve('/protection-des-donnees')}>Protection des données</a>.
				</p>
			</section>
		</div>
	</div>
</main>

<style>
	/* Hallmark · shape: Long Document, the sticky contents rail of Protection des données beside one reading column · theme: Almanac, shared (#lib/almanach) · redesign: full
	 * signature: a Grand Conseil title read name by name, each name kept or set aside by the attachment rules · imagery: none, two diagrams of the page's own facts */
	/* Hallmark · waive 38iii · the part number in each h2 · the parts carry the same numbers in the sommaire rail */
	/* Hallmark · answered F-motion · each diagram plays once on entry, never loops; the two ways to stop the robot show their delays once */

	/* Les jetons, la base, l'en-tête, les parties et le sommaire sont communs aux pages Almanach (#lib/almanach). */

	.intro {
		margin-top: var(--space-xl);
	}
	.intro .chapeau {
		margin-top: 0;
	}
	ul,
	ol {
		max-width: 65ch;
		margin: var(--space-sm) 0 0;
		padding-left: var(--space-lg);
	}
	li + li {
		margin-top: var(--space-xs);
	}
	li::marker {
		color: var(--color-accent);
	}

	/* Les listes de référence : une ligne réglée par entrée, sans puce. */
	.conseils,
	.voies,
	.robot,
	.sources {
		list-style: none;
		padding: 0;
		border-bottom: var(--rule-hair) solid var(--color-rule);
	}
	.conseils li,
	.voies li,
	.robot li,
	.sources li {
		margin: 0;
		padding-block: var(--space-sm);
		border-top: var(--rule-hair) solid var(--color-rule);
	}
	.conseils strong,
	.voies strong {
		font-family: var(--font-display);
	}
	.voies {
		font-size: var(--text-md);
	}

	/* Le robot, en fiche : la question à gauche, la réponse à droite. */
	.robot {
		max-width: none;
	}
	.robot li {
		position: relative;
		padding-left: 10.5rem;
	}
	.robot strong {
		position: absolute;
		left: 0;
		width: 9.5rem;
		font-family: var(--font-display);
		font-size: var(--text-md);
	}

	/* Les deux voies pour qu'une commune ne soit plus lue, côte à côte, chacune avec son délai. */
	.arret {
		list-style: none;
		max-width: none;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr));
		gap: var(--space-lg);
	}
	.arret li {
		margin: 0;
		padding: var(--space-lg);
		overflow-wrap: anywhere;
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
	}
	.delai {
		display: block;
		margin-bottom: var(--space-xs);
		font-family: var(--font-display);
		font-size: var(--text-title);
		font-weight: 600;
		letter-spacing: var(--tracking-display);
		line-height: 1.2;
		color: var(--color-ink);
	}
	.nombre {
		font-family: var(--font-outlier);
		font-weight: 500;
		font-variant-numeric: tabular-nums;
		color: var(--color-accent);
	}

	/* Le code de robots.txt : un creux dans le papier, un filet d'encre en tête. */
	pre {
		max-width: 100%;
		margin: var(--space-sm) 0 0;
		padding: var(--space-sm) var(--space-md);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-paper-2);
		font-size: var(--text-md);
		line-height: 1.5;
		overflow-x: auto;
	}
	pre code {
		color: var(--color-ink);
		overflow-wrap: normal;
	}
	.arret pre {
		background: var(--color-paper);
	}

	/* Les sources : le nom, son attribution, puis sa licence et sa voie d'accès, en chiffres de machine. */
	.sources {
		max-width: none;
		overflow-wrap: anywhere;
	}
	.sources li {
		display: grid;
		gap: var(--space-3xs);
		font-size: var(--text-md);
		line-height: 1.45;
	}
	.nom {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--color-ink);
	}
	.details {
		font-family: var(--font-outlier);
		font-size: var(--text-xs);
		color: var(--color-muted);
	}

	/* Le contact : un creux dans le papier, l'orange en tête. */
	.action {
		margin-top: var(--space-lg);
		padding: var(--space-lg) var(--space-xl);
		border-top: var(--rule-bar) solid var(--color-accent);
		background: var(--color-paper-2);
	}
	.action p {
		margin-top: 0;
	}

	@media (max-width: 40rem) {
		.robot li {
			padding-left: 0;
		}
		.robot strong {
			position: static;
			display: block;
			width: auto;
		}
		.arret li,
		.action {
			margin-inline: calc(-1 * var(--space-xs));
			padding: var(--space-md) var(--space-sm);
		}
	}

	/* Les délais des deux voies arrivent l'un après l'autre, une fois, quand la liste entre à l'écran. */
	@media screen and (prefers-reduced-motion: no-preference) {
		:global(.arret[data-js-etat='attente']) .delai {
			opacity: 0;
		}
		:global(.arret[data-js-etat='joue']) .delai {
			animation: monte 0.6s var(--ease-out) 0.15s both;
		}
		:global(.arret[data-js-etat='joue']) li + li .delai {
			animation-delay: 0.45s;
		}
	}
	@keyframes monte {
		from {
			opacity: 0;
			transform: translateY(0.5rem);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}

	@media print {
		.arret li,
		.action,
		pre,
		.arret pre {
			background: none;
		}
		.arret li,
		.sources li {
			break-inside: avoid;
		}
	}
</style>
