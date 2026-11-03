<script lang="ts">
	import { AUDIENCE } from '#lib/audience.js';
	import { COURRIEL, DEPOT_DONNEES } from '#lib/config.js';
	import { canonique } from '#lib/indexation.js';
	import DemoMasquage from './DemoMasquage.svelte';
	import EtapesRetrait from './EtapesRetrait.svelte';
	import TrajetVisite from './TrajetVisite.svelte';

	// Deux parties (#16) : ce que le site publie sur des personnes (ADR 0007), puis la déclaration exigée par
	// l'art. 19 nLPD (responsable, finalités, destinataires et leur pays). Tout ce qui parle de GoatCounter
	// n'apparaît que si la mesure d'audience est activée à la construction (`VITE_GOATCOUNTER`). « En bref », le
	// sommaire et les diagrammes (#165) résument le texte sans rien y ajouter : la page se lit sans eux.

	/** À changer quand le fond de la page change, pas pour une retouche de forme. */
	const MISE_A_JOUR = '2026-11-03';
	const miseAJour = new Intl.DateTimeFormat('fr-CH', { dateStyle: 'long', timeZone: 'UTC' }).format(
		new Date(MISE_A_JOUR)
	);

	const NLPD = 'https://www.fedlex.admin.ch/eli/cc/2022/491/fr';
	const OPDO = 'https://www.fedlex.admin.ch/eli/cc/2022/568/fr';

	const sommaire = [
		{
			id: 'personnes',
			titre: 'Ce que le site publie sur des personnes',
			sous: [
				{ id: 'origine', titre: 'Quelles données, d’où' },
				{ id: 'elus-connus', titre: 'La liste des élu·e·s connu·e·s' },
				{ id: 'masques-par-defaut', titre: 'Élu·e·s masqué·e·s par défaut' },
				{ id: 'retrait', titre: 'Retrait d’un nom' }
			]
		},
		{
			id: 'visite',
			titre: 'Ce que votre visite transmet',
			sous: [
				{ id: 'responsable', titre: 'Responsable et finalités' },
				{ id: 'destinataires', titre: 'Destinataires' },
				{ id: 'droits', titre: 'Vos droits' },
				...(AUDIENCE ? [{ id: 'statistiques', titre: 'Statistiques de visite' }] : [])
			]
		}
	];

	// Le sommaire suit la lecture : l'intertitre passé en dernier au tiers haut de l'écran est marqué. Sans
	// JavaScript, le sommaire reste une simple liste de liens.
	const ancres = sommaire.flatMap((p) => [p.id, ...p.sous.map((s) => s.id)]);
	let actif = $state<string | null>(null);
	const partieActive = $derived(
		sommaire.find((p) => p.id === actif || p.sous.some((s) => s.id === actif))?.id ?? null
	);

	function suitLaLecture(_: HTMLElement) {
		let image = 0;
		const lit = () => {
			image = 0;
			const seuil = innerHeight * 0.3;
			let dernier: string | null = null;
			for (const id of ancres) {
				const titre = document.getElementById(id);
				if (titre && titre.getBoundingClientRect().top <= seuil) dernier = id;
			}
			actif = dernier;
		};
		const auDefilement = () => {
			if (!image) image = requestAnimationFrame(lit);
		};
		addEventListener('scroll', auDefilement, { passive: true });
		lit();
		return {
			destroy() {
				removeEventListener('scroll', auDefilement);
				cancelAnimationFrame(image);
			}
		};
	}
</script>

<svelte:head>
	<title>Protection des données – Vigie Vaud</title>
	<meta
		name="description"
		content="Ce que Vigie Vaud publie sur des personnes, et ce que votre visite transmet : responsable, finalités, destinataires et vos droits."
	/>
	<link rel="canonical" href={canonique('/protection-des-donnees')} />
</svelte:head>

<main class="almanach" data-theme="almanach">
	<div class="cadre">
		<header class="tete">
			<h1>Protection des données</h1>
			<p class="date">Mise à jour le <time datetime={MISE_A_JOUR}>{miseAJour}</time></p>
		</header>

		<section class="bref" aria-labelledby="en-bref">
			<h2 id="en-bref">En bref</h2>
			<ul>
				<li>
					<svg viewBox="0 0 24 24" aria-hidden="true">
						<circle cx="12" cy="12" r="8.5" pathLength="1" />
						<circle cx="9.5" cy="10" r="1" class="plein" />
						<circle cx="14" cy="14.5" r="1" class="plein" />
						<path d="M4 20 20 4" pathLength="1" />
					</svg>
					<span><strong>Aucun compte, aucun cookie.</strong></span>
				</li>
				<li>
					<svg viewBox="0 0 24 24" aria-hidden="true">
						<circle cx="12" cy="12" r="8.5" pathLength="1" />
						<path
							d="M3.5 12h17M12 3.5c2.5 2.6 3.5 5.4 3.5 8.5s-1 5.9-3.5 8.5c-2.5-2.6-3.5-5.4-3.5-8.5s1-5.9 3.5-8.5"
							pathLength="1"
						/>
					</svg>
					<span>
						Votre <strong>adresse IP</strong> est vue par l’hébergeur et par les services qui fournissent la carte et
						ses données.
					</span>
				</li>
				<li>
					<svg viewBox="0 0 24 24" aria-hidden="true">
						<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z" pathLength="1" />
						<circle cx="12" cy="10" r="2.3" pathLength="1" />
					</svg>
					<span>Votre <strong>position</strong> «&nbsp;Autour de moi&nbsp;» ne quitte pas votre appareil.</span>
				</li>
				<li>
					<svg viewBox="0 0 24 24" aria-hidden="true">
						<path
							d="M3 12s3.3-6 9-6c1.6 0 3 .5 4.2 1.2M21 12s-3.3 6-9 6c-1.6 0-3-.5-4.2-1.2M4 20 20 4"
							pathLength="1"
						/>
					</svg>
					<span>
						Les noms de <strong>particuliers sont masqués</strong>&nbsp;; les élu·e·s restent nommé·e·s.
					</span>
				</li>
				{#if AUDIENCE}
					<li>
						<svg viewBox="0 0 24 24" aria-hidden="true">
							<path d="M4 20h16M7 16v-4M12 16V6M17 16v-7" pathLength="1" />
						</svg>
						<span>
							Une <strong>mesure d’audience</strong> sans cookie compte les pages vues, sans garder votre adresse IP.
						</span>
					</li>
				{/if}
				<li>
					<svg viewBox="0 0 24 24" aria-hidden="true">
						<rect x="3" y="5" width="18" height="14" rx="2" pathLength="1" />
						<path d="m3.5 6 8.5 7 8.5-7" pathLength="1" />
					</svg>
					<span>
						Un nom a échappé au masquage&nbsp;? <a href="#retrait">Un courriel suffit</a>&nbsp;: il est
						<strong>retiré sous 7 jours</strong>.
					</span>
				</li>
			</ul>
		</section>

		<nav class="sommaire" aria-label="Sommaire" use:suitLaLecture>
			{#each sommaire as partie, i (partie.id)}
				<div class="partie-sommaire" class:active={partieActive === partie.id}>
					<a class="partie-lien" class:actif={actif === partie.id} href="#{partie.id}"
						><span class="numero">{i + 1}</span>{partie.titre}</a
					>
					<ul>
						{#each partie.sous as s (s.id)}
							<li><a href="#{s.id}" class:actif={actif === s.id}>{s.titre}</a></li>
						{/each}
					</ul>
				</div>
			{/each}
		</nav>

		<div class="corps">
			<section class="partie personnes" aria-labelledby="personnes">
				<h2 id="personnes"><span class="numero" aria-hidden="true">1</span>Ce que le site publie sur des personnes</h2>
				<p class="chapeau">
					Les élu·e·s sont nommé·e·s, puisqu’ils exercent un mandat public. Les noms de particuliers sont masqués&nbsp;;
					les entreprises et les collectivités restent nommées.
				</p>

				<DemoMasquage />

				<p>
					Pour les permis de construire, le site ne reprend pas les noms de propriétaire, de requérant ou d’architecte
					des avis officiels&nbsp;: seulement la nature des travaux, leur description, les dates et le statut. Lorsqu’une
					description mentionne un particulier («&nbsp;pour le compte de M. …&nbsp;»), son nom est remplacé automatiquement par
					«&nbsp;[particulier]&nbsp;», dans votre navigateur, avant affichage. Ce masquage automatique peut laisser passer un
					cas isolé&nbsp;: il suffit de le signaler à <a href="mailto:{COURRIEL}">{COURRIEL}</a> pour qu’il soit corrigé.
					Les avis officiels, eux, contiennent ces informations pendant la durée de l’enquête.
				</p>
				<p>
					Pour les conseils, les auteur·e·s des objets (motions, interpellations, postulats…) sont nommé·e·s, avec
					leur parti, puisque ce sont des élu·e·s. Les autres noms de personnes qui apparaissent dans les titres des
					objets et dans les ordres du jour des séances sont remplacés par «&nbsp;[particulier]&nbsp;» avant publication, lors
					de l’import quotidien, et leurs coordonnées (adresse, téléphone, courriel) par «&nbsp;[coordonnées]&nbsp;»&nbsp;: ils
					n’atteignent jamais le dépôt de données public. Les pétitions n’affichent pas leurs auteur·e·s.
				</p>

				<h3 id="origine">Quelles données, d’où</h3>
				<p>
					Le site ne publie sur des personnes que des données d’élu·e·s&nbsp;: leur nom, leur parti quand la source le
					donne, et les objets dont ils sont auteur·e·s. Elles viennent de sources publiques&nbsp;: OpenParlData, qui
					réunit les données du Grand Conseil et de quelques conseils communaux, et les sites des communes, pour les
					autres conseils. Des avis officiels d’enquête publique de la CAMAC, le site ne publie aucun nom de
					personne&nbsp;: il ne reprend pas les champs qui en contiennent et masque ceux des descriptions.
				</p>

				<h3 id="elus-connus">La liste des élu·e·s connu·e·s</h3>
				<p>
					Pour savoir quels noms laisser lisibles, le cron tient pour chaque conseil la liste de ses élu·e·s
					connu·e·s&nbsp;: les auteur·e·s de ses Objets (sauf les pétitions) et, pour un conseil lu sur le site de sa
					commune, les membres que nomme sa page des membres. Cette liste est publique, en clair, sans limite de
					durée, dans le
					<a href={DEPOT_DONNEES} target="_blank" rel="noopener">dépôt de données public</a>&nbsp;: pour un conseil lu sur
					le site de sa commune, dans le fichier <code>conseils/&lt;n° OFS&gt;/membres.json</code>&nbsp;; pour les autres,
					ce sont les auteur·e·s des Objets de l’archive.
				</p>
				<p>
					Elle ne se vide pas&nbsp;: une personne vue un jour comme membre ou comme auteur·e reste connue, pour qu’un·e
					ancien·ne élu·e reste lisible dans les titres de son mandat. À la fin du mandat, les mentions faites dans
					l’exercice du mandat restent&nbsp;; toute autre mention de la personne passe par le retrait décrit plus bas.
				</p>

				<h3 id="masques-par-defaut">Élu·e·s masqué·e·s par défaut</h3>
				<p>
					Un conseil dont le site ne publie pas de page des membres est lu quand même&nbsp;: ses élu·e·s nommé·e·s après
					une civilité («&nbsp;M.&nbsp;», «&nbsp;Mme&nbsp;») y sont alors masqué·e·s, comme un·e élu·e que la liste ne connaît pas encore.
					C’est voulu&nbsp;: en cas de doute, le site masque. Vigie Vaud ne démasque personne sur demande et ne tient aucune
					liste à la main&nbsp;; la seule voie est la page des membres du conseil, sur le site de la commune.
				</p>

				<div class="action">
					<h3 id="retrait">Retrait d’un nom</h3>
					<p class="appel">
						Le nom d’une personne est passé à travers le masquage&nbsp;? Un courriel suffit&nbsp;: il est retiré sous 7 jours.
					</p>
					<a class="bouton courriel" href="mailto:{COURRIEL}">
						<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
							<rect x="3" y="5" width="18" height="14" rx="2" />
							<path d="m3.5 6 8.5 7 8.5-7" />
						</svg>
						<!-- Sur téléphone, l'adresse passe à la ligne avant « @ », jamais au milieu d'un mot. -->
						<span>{COURRIEL.split('@')[0]}<wbr />@{COURRIEL.split('@')[1]}</span>
					</a>
					<EtapesRetrait />
					<p>
						Si le nom d’une personne est passé à travers le masquage, écrivez à
						<a href="mailto:{COURRIEL}">{COURRIEL}</a>, jamais par une issue, qui publierait le nom. Il est retiré dans
						les 7 jours, historique du dépôt de données public compris. Comme le cron relit les sources chaque jour,
						le dépôt de données garde une correction pour cet élément (son texte corrigé, sans le nom), appliquée à
						chaque import et à chaque rattrapage&nbsp;; quand le cas révèle une règle, le masquage est corrigé aussi. Le
						texte d’origine reste à la source&nbsp;: chez OpenParlData ou sur le site de la commune.
					</p>
				</div>
			</section>

			<section class="partie visite" aria-labelledby="visite">
				<h2 id="visite"><span class="numero" aria-hidden="true">2</span>Ce que votre visite transmet</h2>
				<p class="chapeau">
					Le site ne demande aucun compte et ne pose aucun cookie. Afficher une page et sa carte passe toutefois par
					les services ci-dessous, qui reçoivent au moins l’adresse IP de votre appareil. Cette déclaration répond à
					l’art. 19 de la <a href={NLPD} target="_blank" rel="noopener">loi fédérale sur la protection des données</a>
					(nLPD).
				</p>

				<TrajetVisite />

				<div class="fiches">
					<div>
						<h3 id="responsable">Responsable</h3>
						<p>Louni Merk, joignable à <a href="mailto:{COURRIEL}">{COURRIEL}</a>.</p>
					</div>
					<div>
						<h3 id="finalites">Finalités</h3>
						<ul>
							<li>afficher le site et sa carte&nbsp;;</li>
							<li>assurer la sécurité de l’hébergement&nbsp;;</li>
							{#if AUDIENCE}
								<li>établir des statistiques de visite agrégées.</li>
							{/if}
						</ul>
					</div>
				</div>

				<h3 id="destinataires">Destinataires</h3>
				<!--
					Liste écrite à la main : ce sont des services, pas des sources. À revoir à chaque nouvelle source Direct
					(sources.json, voie_acces « direct ») : le navigateur l'interroge lui-même, c'est donc un nouveau
					destinataire de l'adresse IP des visiteurs. Le diagramme TrajetVisite.svelte la reprend en bref.
				-->
				<table class="destinataires">
					<thead>
						<tr>
							<th scope="col">Service</th>
							<th scope="col">Pays</th>
							<th scope="col">Données reçues</th>
							<th scope="col">Garantie</th>
						</tr>
					</thead>
					<tbody>
						<tr>
							<th scope="row" data-titre="Service">
								<strong>GitHub Pages</strong> (GitHub), qui héberge le site et ses données
							</th>
							<td data-titre="Pays">États-Unis</td>
							<td data-titre="Données reçues">
								votre adresse IP, enregistrée pour la sécurité de l’hébergement, pendant une durée fixée par GitHub
							</td>
							<td data-titre="Garantie">GitHub est certifié selon le Swiss-U.S. Data Privacy Framework.</td>
						</tr>
						{#if AUDIENCE}
							<tr>
								<th scope="row" data-titre="Service"><strong>GoatCounter</strong>, la mesure d’audience</th>
								<td data-titre="Pays">Irlande, serveurs en Finlande et en Allemagne</td>
								<td data-titre="Données reçues">
									à chaque page vue, votre adresse IP, le nom de votre navigateur et le chemin de la page
									(<code>/commune/pully</code>), sans ses paramètres&nbsp;: ni le centre de la carte, ni le dossier ouvert,
									ni la page d’où vous venez. Il ne pose aucun cookie, ne conserve pas votre adresse IP et ne garde
									que des totaux.
								</td>
								<td data-titre="Garantie">
									Ces trois pays offrent une protection adéquate (<a href={OPDO} target="_blank" rel="noopener"
										>annexe 1 OPDo</a
									>).
								</td>
							</tr>
						{/if}
						<tr>
							<th scope="row" data-titre="Service">
								<strong>swisstopo</strong> (Office fédéral de topographie), pour le fond de carte et la recherche
								d’adresses
							</th>
							<td data-titre="Pays">Suisse</td>
							<td data-titre="Données reçues">votre adresse IP, la zone affichée et le texte d’une recherche d’adresse</td
							>
							<td data-titre="Garantie">en Suisse</td>
						</tr>
						<tr data-destinataire="vd">
							<th scope="row" data-titre="Service">
								<strong>L’État de Vaud</strong> (<code>ogc.vd.ch</code>), pour les permis de construire et les
								restrictions de circulation
							</th>
							<td data-titre="Pays">Suisse</td>
							<td data-titre="Données reçues">votre adresse IP et, pour les permis, la zone affichée</td>
							<td data-titre="Garantie">en Suisse</td>
						</tr>
					</tbody>
				</table>
				<p class="note">
					<strong>«&nbsp;Autour de moi&nbsp;»</strong>&nbsp;: la position de votre appareil n’est envoyée à personne&nbsp;; la carte
					charge ensuite la zone autour d’elle auprès de swisstopo et du canton, comme pour tout déplacement de la
					carte.
				</p>

				<h3 id="droits">Vos droits</h3>
				<p>Écrivez à <a href="mailto:{COURRIEL}">{COURRIEL}</a> pour&nbsp;:</p>
				<ul class="droits">
					<li>
						<svg viewBox="0 0 24 24" aria-hidden="true">
							<circle cx="10.5" cy="10.5" r="6.5" />
							<path d="m15.5 15.5 5 5" />
						</svg>
						<span>
							<strong>savoir</strong> si des données vous concernant sont traitées, et lesquelles (droit d’accès,
							<span class="article">art. 25 nLPD</span>)&nbsp;: la réponse est gratuite et vous parvient dans les 30 jours
							(<span class="article">art. 18 OPDo</span>)&nbsp;;
						</span>
					</li>
					<li>
						<svg viewBox="0 0 24 24" aria-hidden="true">
							<path d="M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17v3z" />
							<path d="m14.5 7.5 3 3" />
						</svg>
						<span>
							<strong>faire rectifier</strong> une donnée inexacte (<span class="article">art. 32 al. 1 nLPD</span>)&nbsp;;
						</span>
					</li>
					<li>
						<svg viewBox="0 0 24 24" aria-hidden="true">
							<circle cx="12" cy="12" r="8.5" />
							<path d="M6 18 18 6" />
						</svg>
						<span>
							<strong>faire effacer</strong> une donnée, ou <strong>interdire</strong> un traitement ou sa
							communication à des tiers (<span class="article">art. 32 al. 2 nLPD</span>).
						</span>
					</li>
				</ul>

				{#if AUDIENCE}
					<h3 id="statistiques">Statistiques de visite</h3>
					<p>
						Les statistiques de GoatCounter sont publiques&nbsp;:
						<a href={AUDIENCE.tableau} target="_blank" rel="noopener">tableau de bord de Vigie Vaud</a>.
					</p>
				{/if}
			</section>
		</div>
	</div>
</main>

<style>
	/* Hallmark · shape: Long Document, a sticky contents rail beside one reading column · genre: editorial · theme: Almanac (deal 2/3, seed publique-protection-des-donn-ad7e·cdea8084·2026-11-03·r0) · redesign: full
	 * hero: kept, the title and its date over a 2px ink rule · nav: kept (site header) · footer: kept (none) · imagery: none, three diagrams of the page's own facts · signature: the name crossed out and replaced by [particulier], live, in the source's own sentence
	 * axes: light/grotesk-sans/warm · posture: restrained · contrast: pass · fold: pass · v2.0.0 */
	/* Hallmark · pre-emit critique: P4 H4 E4 S5 R4 V4 · weakest: P, a legal page argues little; the diagrams carry the argument that the site shows what it hides and how */
	/* Hallmark · waive 1 · system-ui display, a serif and a mono from the system · a web font would add one more recipient of the visitor's IP address to the very page that lists them */
	/* Hallmark · waive 38iii · the part number in each h2 · the two parts of the page carry the same numbers in the sommaire rail */
	/* Hallmark · dismissed 63 · the middle dots are French inclusive writing (élu·e·s), the site's glossary spelling */
	/* Hallmark · dismissed 67 · {COURRIEL} is a constant holding the contact address in lower case, not text in capitals */
	/* Hallmark · dismissed 19 · the dash is in the title tag, the site-wide pattern "<page> – Vigie Vaud" every route shares */
	/* Hallmark · answered F-motion · the user asked for more and pleasanter motion than the theme's stillness: each diagram plays once on entry, never loops */

	/* Almanac sur la marque de Vigie Vaud : l'encre est le marine du site, le signal son orange, le papier une ardoise
	   pâle. Polices du système : une police web ferait un destinataire de plus. */
	[data-theme='almanach'] {
		--color-paper: oklch(95.5% 0.008 255);
		--color-paper-2: oklch(92.5% 0.012 255);
		--color-sheet: oklch(99% 0.003 255);
		--color-ink: oklch(25% 0.045 257);
		--color-ink-2: oklch(31% 0.03 257);
		--color-muted: oklch(46% 0.025 257);
		--color-rule: oklch(85% 0.014 255);
		--color-rule-2: oklch(34.7% 0.073 257);
		--color-accent: oklch(53.4% 0.168 38);
		--color-accent-2: oklch(46% 0.15 38);
		--color-accent-wash: oklch(94% 0.035 50);
		--color-accent-ink: oklch(98.5% 0.006 60);
		--color-focus: oklch(56.9% 0.202 260);
		--font-display: system-ui, -apple-system, 'Segoe UI', sans-serif;
		--font-body: 'Iowan Old Style', Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif;
		--font-outlier: ui-monospace, 'SF Mono', 'Cascadia Mono', Menlo, Consolas, monospace;
		--radius-pill: 2px;
		--rule-hair: 1px;
		--rule-bar: 2px;
		--tracking-display: -0.02em;
		--space-3xs: 2px;
		--space-2xs: 4px;
		--space-xs: 8px;
		--space-sm: 12px;
		--space-md: 16px;
		--space-lg: 24px;
		--space-xl: 40px;
		--space-2xl: 64px;
		--space-3xl: 96px;
		--text-xs: 0.8125rem;
		--text-sm: 0.875rem;
		--text-md: 1rem;
		--text-lg: 1.25rem;
		--text-body: 1.125rem;
		--text-display: clamp(2.5rem, 4.5vw + 1rem, 4.75rem);
		--text-section: clamp(1.875rem, 2vw + 1.1rem, 3rem);
		--text-title: clamp(1.25rem, 0.6vw + 1rem, 1.5rem);
		--text-lead: clamp(1.1875rem, 0.4vw + 1rem, 1.375rem);
		--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
		--ease-in: cubic-bezier(0.7, 0, 0.84, 0);
		--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
		--dur-micro: 120ms;
		--dur-short: 220ms;
		--container: 72rem;
		--gutter: var(--space-2xl);
		--rail: 13.5rem;
	}
	.almanach {
		display: block;
		background: var(--color-paper);
		color: var(--color-ink-2);
		font-family: var(--font-body);
		font-size: var(--text-body);
		line-height: 1.6;
	}
	:global(html:has(main.almanach)),
	:global(body:has(main.almanach)) {
		overflow-x: clip;
	}
	.almanach :focus-visible {
		outline: var(--rule-bar) solid var(--color-focus);
		outline-offset: var(--space-3xs);
	}
	.almanach ::selection {
		background: var(--color-accent-wash);
		color: var(--color-ink);
	}
	.cadre {
		max-width: var(--container);
		margin-inline: auto;
		padding: var(--space-2xl) var(--gutter) var(--space-3xl);
	}

	h1,
	h2,
	h3 {
		margin: 0;
		font-family: var(--font-display);
		font-weight: 600;
		letter-spacing: var(--tracking-display);
		color: var(--color-ink);
		overflow-wrap: break-word;
		min-width: 0;
		text-wrap: balance;
		scroll-margin-top: calc(var(--header-h) + var(--space-lg));
	}
	p {
		margin: var(--space-md) 0 0;
		max-width: 65ch;
		text-wrap: pretty;
	}
	a {
		color: var(--color-ink);
		text-decoration-color: var(--color-accent);
		text-decoration-thickness: var(--rule-hair);
		text-underline-offset: 0.18em;
		transition: text-decoration-thickness var(--dur-micro) var(--ease-out);
	}
	a:hover {
		text-decoration-thickness: var(--rule-bar);
	}
	code {
		font-family: var(--font-outlier);
		font-size: 0.85em;
		overflow-wrap: anywhere;
	}
	strong {
		font-weight: 600;
		color: var(--color-ink);
	}
	svg {
		fill: none;
		stroke: currentColor;
		stroke-width: 1.8;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.numero {
		font-family: var(--font-outlier);
		font-weight: 500;
		font-variant-numeric: tabular-nums;
		color: var(--color-accent);
	}

	/* L'en-tête : le titre et sa date, puis le filet d'encre sur toute la largeur. */
	.tete {
		padding-bottom: var(--space-lg);
		border-bottom: var(--rule-bar) solid var(--color-rule-2);
	}
	h1 {
		max-width: 16ch;
		font-size: var(--text-display);
		letter-spacing: -0.035em;
		line-height: 0.98;
	}
	.date {
		margin-top: var(--space-md);
		font-size: var(--text-sm);
		color: var(--color-muted);
	}

	/* En bref : la feuille du manuel, une ligne réglée par fait. */
	.bref {
		margin-top: var(--space-xl);
		padding: var(--space-lg);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
	}
	.bref h2 {
		font-size: var(--text-title);
	}
	.bref ul {
		list-style: none;
		margin: var(--space-sm) 0 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr));
		column-gap: var(--space-xl);
	}
	.bref li {
		display: flex;
		align-items: flex-start;
		gap: var(--space-sm);
		padding-block: var(--space-sm);
		border-top: var(--rule-hair) solid var(--color-rule);
		font-size: var(--text-md);
		line-height: 1.45;
	}
	.bref svg {
		flex: none;
		width: 1.5rem;
		height: 1.5rem;
		color: var(--color-accent);
	}
	.bref .plein {
		fill: currentColor;
		stroke: none;
	}

	/* Le sommaire. Sur grand écran, il devient un rail qui reste à côté du texte, avec un filet qui se remplit à
	   mesure de la lecture et l'intertitre courant marqué. */
	.sommaire {
		margin-top: var(--space-xl);
		padding-top: var(--space-md);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		font-family: var(--font-display);
		font-size: var(--text-sm);
		line-height: 1.35;
	}
	.partie-sommaire + .partie-sommaire {
		margin-top: var(--space-lg);
	}
	.partie-lien {
		display: flex;
		gap: var(--space-xs);
		font-weight: 600;
		color: var(--color-ink);
		text-decoration: none;
	}
	.sommaire ul {
		list-style: none;
		margin: var(--space-xs) 0 0;
		padding: 0 0 0 var(--space-md);
	}
	.sommaire li a {
		position: relative;
		display: block;
		padding: var(--space-2xs) 0 var(--space-2xs) var(--space-sm);
		color: var(--color-muted);
		text-decoration: none;
		transition:
			color var(--dur-short) var(--ease-out),
			transform var(--dur-short) var(--ease-out);
	}
	/* La marque de l'intertitre courant : un trait orange qui se dresse. */
	.sommaire li a::before {
		content: '';
		position: absolute;
		left: 0;
		top: var(--space-2xs);
		bottom: var(--space-2xs);
		border-left: var(--rule-bar) solid var(--color-accent);
		transform: scaleY(0);
		transition: transform var(--dur-short) var(--ease-out);
	}
	.sommaire li a:hover {
		color: var(--color-ink);
		transform: translateX(var(--space-3xs));
	}
	.sommaire li a.actif {
		color: var(--color-ink);
	}
	.sommaire li a.actif::before {
		transform: none;
	}
	.sommaire a:active {
		color: var(--color-accent);
	}

	/* Les deux parties. */
	.partie {
		margin-top: var(--space-3xl);
	}
	.partie > h2 {
		display: flex;
		align-items: baseline;
		gap: var(--space-sm);
		padding-top: var(--space-md);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		font-size: var(--text-section);
		line-height: 1.05;
	}
	.chapeau {
		margin-top: var(--space-lg);
		font-size: var(--text-lead);
		line-height: 1.5;
		color: var(--color-ink);
	}
	h3 {
		margin-top: var(--space-2xl);
		font-size: var(--text-title);
		line-height: 1.2;
	}
	h3 + p {
		margin-top: var(--space-sm);
	}

	/* L'encadré d'action du retrait : un creux dans le papier, l'orange en tête. */
	.action {
		margin-top: var(--space-2xl);
		padding: var(--space-xl);
		border-top: var(--rule-bar) solid var(--color-accent);
		background: var(--color-paper-2);
	}
	.action h3 {
		margin-top: 0;
	}
	.appel {
		margin-top: var(--space-sm);
		font-family: var(--font-display);
		font-size: var(--text-lg);
		font-weight: 600;
		line-height: 1.35;
		letter-spacing: -0.01em;
		color: var(--color-ink);
	}
	.almanach .courriel {
		gap: var(--space-xs);
		min-height: 48px;
		margin-top: var(--space-lg);
		padding: var(--space-sm) var(--space-lg);
		border-radius: var(--radius-pill);
		background: var(--color-accent);
		color: var(--color-accent-ink);
		font-family: var(--font-display);
		font-size: var(--text-md);
		font-weight: 600;
		text-align: left;
		transition:
			background-color var(--dur-micro) var(--ease-out),
			transform var(--dur-micro) var(--ease-out);
	}
	.almanach .courriel:hover {
		background: var(--color-accent-2);
		transform: translateY(-1px);
	}
	.almanach .courriel:active {
		transform: none;
	}
	.almanach .courriel svg {
		flex: none;
	}
	.action :global(.diagramme) {
		margin-block: var(--space-xl) 0;
		padding-inline: 0;
		border-top-width: var(--rule-hair);
		background: none;
	}

	/* Responsable et finalités côte à côte, un filet entre les deux. */
	.fiches {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--space-xl);
		margin-top: var(--space-2xl);
	}
	.fiches > div + div {
		padding-left: var(--space-xl);
		border-left: var(--rule-hair) solid var(--color-rule);
	}
	.fiches h3 {
		margin-top: 0;
	}
	.fiches ul {
		margin: var(--space-sm) 0 0;
		padding-left: var(--space-lg);
	}

	/* Destinataires : la table du manuel, sur sa feuille. */
	.destinataires {
		width: 100%;
		margin-top: var(--space-md);
		border-collapse: collapse;
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		font-size: var(--text-sm);
		line-height: 1.45;
	}
	.destinataires th,
	.destinataires td {
		padding: var(--space-sm);
		text-align: left;
		vertical-align: top;
	}
	.destinataires thead th {
		padding-block: var(--space-xs);
		border-bottom: var(--rule-bar) solid var(--color-rule-2);
		font-weight: 500;
		color: var(--color-muted);
	}
	.destinataires tbody tr + tr {
		border-top: var(--rule-hair) solid var(--color-rule);
	}
	.destinataires tbody th {
		width: 30%;
		font-weight: 400;
	}
	.destinataires tbody strong {
		font-family: var(--font-display);
	}
	.destinataires tbody tr {
		transition: background-color var(--dur-short) var(--ease-out);
	}
	.destinataires tbody tr:hover {
		background: var(--color-paper);
	}
	.note {
		margin-top: var(--space-lg);
	}

	/* Droits : une ligne réglée par droit, l'article cité en chiffres. */
	.droits {
		list-style: none;
		margin: var(--space-md) 0 0;
		padding: 0;
		max-width: 65ch;
		border-bottom: var(--rule-hair) solid var(--color-rule);
	}
	.droits li {
		display: flex;
		gap: var(--space-md);
		padding-block: var(--space-md);
		border-top: var(--rule-hair) solid var(--color-rule);
	}
	.droits svg {
		flex: none;
		width: 1.5rem;
		height: 1.5rem;
		margin-top: var(--space-3xs);
		color: var(--color-accent);
	}
	.droits strong {
		font-family: var(--font-display);
	}
	.article {
		font-family: var(--font-outlier);
		font-size: 0.82em;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		color: var(--color-ink);
	}

	/* Grand écran : le sommaire en rail à gauche, de « En bref » au bas de la page. */
	@media (min-width: 60rem) {
		.cadre {
			display: grid;
			grid-template-columns: var(--rail) minmax(0, 1fr);
			column-gap: var(--space-2xl);
		}
		.tete {
			grid-column: 1 / -1;
		}
		.bref,
		.corps {
			grid-column: 2;
		}
		.sommaire {
			grid-column: 1;
			grid-row: 2 / span 2;
			align-self: start;
			position: sticky;
			top: calc(var(--header-h) + var(--space-lg));
			margin-top: var(--space-xl);
			padding: 0 0 0 var(--space-md);
			border-top: 0;
		}
		/* Le filet de lecture, le long du rail. */
		.sommaire::before,
		.sommaire::after {
			content: '';
			position: absolute;
			left: 0;
			top: 0;
			bottom: 0;
			border-left: var(--rule-bar) solid var(--color-rule);
		}
		.sommaire::after {
			border-left-color: var(--color-accent);
			transform-origin: top;
			transform: scaleY(0);
		}
	}
	@media (max-width: 60rem) {
		.almanach {
			--gutter: var(--space-lg);
		}
	}
	@media (max-width: 40rem) {
		.almanach {
			--gutter: var(--space-md);
			--text-body: 1.0625rem;
		}
		.cadre {
			padding-top: var(--space-xl);
		}
		.bref,
		.action {
			margin-inline: calc(-1 * var(--space-xs));
			padding: var(--space-md) var(--space-sm);
		}
		.partie {
			margin-top: var(--space-2xl);
		}
		.fiches {
			grid-template-columns: minmax(0, 1fr);
			gap: var(--space-lg);
		}
		.fiches > div + div {
			padding: var(--space-lg) 0 0;
			border-left: 0;
			border-top: var(--rule-hair) solid var(--color-rule);
		}
		.fiches h3 {
			margin-top: 0;
		}
		/* Le tableau devient une fiche par destinataire, chaque case précédée de son titre de colonne. */
		.destinataires,
		.destinataires tbody,
		.destinataires tr,
		.destinataires th,
		.destinataires td {
			display: block;
			width: auto;
		}
		.destinataires thead {
			display: none;
		}
		.destinataires tbody tr {
			padding-block: var(--space-xs);
		}
		.destinataires tbody tr + tr {
			border-top-width: var(--rule-bar);
			border-top-color: var(--color-rule-2);
		}
		.destinataires th,
		.destinataires td,
		.destinataires tbody th {
			width: auto;
			padding: var(--space-2xs) var(--space-sm);
		}
		.destinataires [data-titre]::before {
			content: attr(data-titre);
			display: block;
			font-size: var(--text-xs);
			font-weight: 500;
			color: var(--color-muted);
		}
	}

	/* Le mouvement : à l'écran seulement, et seulement si l'on n'a pas demandé de le réduire. Il part toujours d'un
	   état visible ; sans lui, la page est la même, immobile. */
	@media screen and (prefers-reduced-motion: no-preference) {
		:global(html:has(main.almanach)) {
			scroll-behavior: smooth;
		}
		h1,
		.date {
			animation: monte 0.8s var(--ease-out) both;
		}
		.date {
			animation-delay: 0.12s;
		}
		.bref li {
			animation: monte 0.6s var(--ease-out) calc(0.25s + var(--rang, 0) * 0.07s) both;
		}
		.bref li:nth-child(2) {
			--rang: 1;
		}
		.bref li:nth-child(3) {
			--rang: 2;
		}
		.bref li:nth-child(4) {
			--rang: 3;
		}
		.bref li:nth-child(5) {
			--rang: 4;
		}
		.bref li:nth-child(6) {
			--rang: 5;
		}
		.bref svg > * {
			stroke-dasharray: 1;
			animation: trace 0.9s var(--ease-out) calc(0.45s + var(--rang, 0) * 0.07s) both;
		}
		.bref svg > .plein {
			stroke-dasharray: none;
			animation-name: apparait;
		}
		/* Arrivé par le sommaire, l'intertitre se souligne une fois. */
		:is(h2, h3):target {
			background: linear-gradient(var(--color-accent-wash), var(--color-accent-wash)) no-repeat left bottom /
				100% 0.45em;
			animation: souligne 1.4s var(--ease-out) 0.3s both;
		}
	}
	@supports (animation-timeline: scroll()) {
		@media screen and (prefers-reduced-motion: no-preference) and (min-width: 60rem) {
			.sommaire::after {
				animation: remplit linear both;
				animation-timeline: scroll(root);
			}
		}
	}
	@keyframes monte {
		from {
			opacity: 0;
			transform: translateY(0.6rem);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes trace {
		from {
			stroke-dashoffset: 1;
		}
		to {
			stroke-dashoffset: 0;
		}
	}
	@keyframes apparait {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}
	@keyframes remplit {
		from {
			transform: scaleY(0);
		}
		to {
			transform: none;
		}
	}
	@keyframes souligne {
		from {
			background-size: 0 0.45em;
		}
		to {
			background-size: 100% 0.45em;
		}
	}

	@media print {
		.almanach {
			background: none;
			font-size: 11pt;
		}
		.cadre {
			display: block;
			max-width: none;
			padding: 0;
		}
		.bref,
		.destinataires {
			background: none;
		}
		.action {
			background: none;
			padding-inline: 0;
		}
		.sommaire,
		.courriel {
			display: none;
		}
		.partie {
			margin-top: var(--space-xl);
		}
		.partie > h2 {
			break-after: avoid;
		}
		h3 {
			break-after: avoid;
		}
		.destinataires tr {
			break-inside: avoid;
		}
		/* Les adresses courriel se lisent déjà dans le texte du lien. */
		a[href^='http']::after {
			content: ' (' attr(href) ')';
			font-size: 0.85em;
			color: var(--color-muted);
			overflow-wrap: anywhere;
		}
	}
</style>
