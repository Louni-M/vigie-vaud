<script lang="ts">
	import { resolve } from '$app/paths';
	import { canonique } from '#lib/indexation.js';

	// Textes officiels consultés le 12 octobre 2026. Chaque affirmation de la page renvoie à l'une de ces sources ;
	// à relire si la LATC, le RLATC ou la LPA-VD sont modifiés.
	const SOURCES = {
		etapes: {
			url: 'https://www.vd.ch/territoire-et-construction/permis-de-construire/les-differentes-etapes-de-la-procedure-du-permis-construire',
			titre: 'vd.ch – Les différentes étapes de la procédure du permis de construire'
		},
		fao: {
			url: 'https://www.vd.ch/territoire-et-construction/permis-de-construire/faq/avis-denquete/publication-fao',
			titre: 'vd.ch – FAQ « Avis d’enquête / Publication FAO »'
		},
		avis: {
			url: 'https://www.vd.ch/prestation/consulter-les-avis-de-mise-a-lenquete',
			titre: 'vd.ch – Consulter les avis de mise à l’enquête'
		},
		juridictions: {
			url: 'https://www.vd.ch/justice/le-pouvoir-judiciaire/les-juridictions-administratives',
			titre: 'vd.ch – Les juridictions administratives'
		},
		latc: {
			url: 'https://prestations.vd.ch/pub/blv-publication/actes/consolide/700.11?id=94980419-1c0b-4c3e-bf5d-6d37d57902ec',
			titre: 'Loi sur l’aménagement du territoire et les constructions (LATC, BLV 700.11), art. 104 et 109 à 116'
		},
		rlatc: {
			url: 'https://prestations.vd.ch/pub/blv-publication/actes/consolide/700.11.1?id=12fdc2a6-5c95-4ad5-9433-0801702d6d2b',
			titre: 'Règlement d’application de la LATC (RLATC, BLV 700.11.1), art. 72'
		},
		lpa: {
			url: 'https://prestations.vd.ch/pub/blv-publication/actes/consolide/173.36?id=e23682d9-8d47-49d8-a8fb-54bfae0c3a2a',
			titre: 'Loi sur la procédure administrative (LPA-VD, BLV 173.36), art. 13, 47, 49, 55, 75 et 95'
		},
		lat: {
			url: 'https://www.fedlex.admin.ch/eli/cc/1979/1573_1573_1573/fr#art_33',
			titre: 'Loi fédérale sur l’aménagement du territoire (LAT, RS 700), art. 33'
		},
		ltf: {
			url: 'https://www.fedlex.admin.ch/eli/cc/2006/218/fr#art_89',
			titre: 'Loi sur le Tribunal fédéral (LTF, RS 173.110), art. 89'
		},
		atf: {
			url: 'https://www.bger.ch/ext/eurospider/live/fr/php/clir/http/index.php?highlight_docid=atf%3A%2F%2F140-II-214%3Afr&lang=fr&type=show_document',
			titre: 'Tribunal fédéral, ATF 140 II 214, consid. 2.3 (en allemand)'
		},
		cdc: {
			url: 'https://www.vd.ch/fileadmin/user_upload/organisation/cour_comptes/1_Rapports_d_audit/73_Guide_de_bonnes_pratiques_communales.pdf',
			titre: 'Cour des comptes du canton de Vaud – Guide de bonnes pratiques communales (septembre 2021), points 13 et 14'
		}
	} as const;
	type Cle = keyof typeof SOURCES;

	const sommaire = [
		{ id: 'enquete', titre: 'À quoi sert l’enquête publique' },
		{ id: 'intervenir', titre: 'Observations et oppositions' },
		{ id: 'forme', titre: 'Forme, délai et transparence' },
		{ id: 'apres', titre: 'Après l’enquête' },
		{ id: 'recours', titre: 'Recours : des conditions plus strictes' },
		{ id: 'dialogue', titre: 'S’informer et dialoguer' },
		{ id: 'sources', titre: 'Sources officielles' }
	];
</script>

{#snippet src(cle: Cle, detail = '')}
	<a class="ref" href={SOURCES[cle].url} target="_blank" rel="noopener" title={SOURCES[cle].titre}>{detail ||
			SOURCES[cle].titre.split(' – ')[0]}</a>
{/snippet}

<svelte:head>
	<title>L’enquête publique : ce que prévoit la loi – Vigie Vaud</title>
	<meta
		name="description"
		content="L’enquête publique d’un permis de construire dans le canton de Vaud : consultation du dossier, observations et oppositions, recours, avec les textes officiels."
	/>
	<link rel="canonical" href={canonique('/enquete-publique')} />
</svelte:head>

<main class="page texte">
	<p class="fil"><a href={resolve('/(carte)')}>Carte</a> › L’enquête publique</p>
	<h1>L’enquête publique : ce que prévoit la loi</h1>
	<p class="chapeau">
		Cette page résume les règles vaudoises qui s’appliquent pendant l’enquête publique d’une demande de permis de
		construire. Vigie Vaud informe sur les projets ; il ne prend pas position à leur sujet et ne recommande ni
		d’intervenir, ni de s’abstenir. Le site ne transmet aucune intervention aux communes.
	</p>
	<p class="avertissement">
		Informations générales, sans valeur de conseil juridique : seuls les textes officiels font foi. Textes consultés
		le 12 octobre 2026. En cas de doute sur un dossier, adressez-vous à la commune concernée ou à un ou une
		juriste.
	</p>

	<nav class="sommaire" aria-label="Sommaire">
		<ol>
			{#each sommaire as s (s.id)}
				<li><a href="#{s.id}">{s.titre}</a></li>
			{/each}
		</ol>
	</nav>

	<section id="enquete">
		<h2>À quoi sert l’enquête publique</h2>
		<p>
			La Municipalité met la demande de permis à l’enquête publique pendant trente jours
			({@render src('latc', 'LATC, art. 109 al. 1')}). Le délai court dès le lendemain de la publication dans la
			Feuille des avis officiels (FAO), dont le texte fait foi ({@render src('rlatc', 'RLATC, art. 72 al. 3')}).
		</p>
		<p>
			Pendant ce délai, la demande et ses annexes (plans, descriptif) sont à la disposition du public au greffe
			municipal ou au service technique de la commune ({@render src('rlatc', 'RLATC, art. 72 al. 2')} ;
			{@render src('fao', 'vd.ch, FAQ')}).
		</p>
		<p>
			Selon la Cour des comptes, l’enquête publique sert à faire connaître les projets et à recueillir les
			éventuelles remarques, afin que les autorités décident en connaissance de cause ; elle ne garantit pas
			l’octroi du permis ({@render src('cdc', 'Cour des comptes, 2021, point 13')}).
		</p>
		<p>
			L’avis officiel indique notamment le propriétaire, l’auteur du projet, le lieu et la destination des travaux,
			ainsi que les dérogations demandées ({@render src('latc', 'LATC, art. 109 al. 2')}). Vigie Vaud ne reprend
			aucun de ces noms.
		</p>
	</section>

	<section id="intervenir">
		<h2>Observations et oppositions : qui peut intervenir ?</h2>
		<p>
			La loi prévoit deux formes d’intervention pendant l’enquête : les <strong>observations</strong> sur le projet
			et les <strong>oppositions motivées</strong> ({@render src('latc', 'LATC, art. 109 al. 4')}).
		</p>
		<p>
			D’après l’État de Vaud, toute personne peut faire opposition, dans la mesure où le projet lèse des intérêts
			publics ou privés, en particulier de voisinage ({@render src('etapes', 'vd.ch, étapes de la procédure')}).
			Les personnes qui interviennent dans une enquête publique ont qualité de partie dans la procédure
			({@render src('lpa', 'LPA-VD, art. 13 al. 1 let. d')}).
		</p>
		<p>
			Les auteurs d’observations comme d’oppositions sont avisés de la décision. Pour une opposition, l’avis est
			envoyé sous pli recommandé et indique la voie, le mode et le délai de recours
			({@render src('latc', 'LATC, art. 116')}).
		</p>
	</section>

	<section id="forme">
		<h2>Forme, délai et transparence</h2>
		<ul>
			<li>
				<strong>Par écrit et dans le délai.</strong> Observations et oppositions sont déposées par écrit au greffe
				municipal, dans le délai d’enquête ({@render src('latc', 'LATC, art. 109 al. 4')}). Elles peuvent être
				consignées sur la feuille d’enquête ou adressées au greffe de la commune
				({@render src('rlatc', 'RLATC, art. 72 al. 5')}). L’État de Vaud indique que l’opposition est déposée au
				greffe ou transmise par lettre recommandée ({@render src('etapes', 'vd.ch')}).
			</li>
			<li>
				<strong>Identifiée, datée et signée.</strong> Elles mentionnent lisiblement le nom et l’adresse exacte de
				leur auteur, et sont datées et signées ({@render src('rlatc', 'RLATC, art. 72 al. 5')}).
			</li>
			<li>
				<strong>Motivée.</strong> Une opposition doit être motivée ({@render src('latc', 'LATC, art. 109 al. 4')}),
				c’est-à-dire expliquer en quoi le projet poserait problème. Avant de délivrer le permis, la Municipalité
				vérifie que le projet est conforme aux lois, aux règlements et aux plans d’affectation
				({@render src('latc', 'LATC, art. 104 al. 1')}).
			</li>
			<li>
				<strong>Consultable.</strong> Observations et oppositions sont jointes au dossier et peuvent être consultées
				par les intéressés ({@render src('latc', 'LATC, art. 109 al. 4')} ;
				{@render src('rlatc', 'RLATC, art. 72 al. 7')}).
			</li>
			<li>
				<strong>Collective.</strong> En cas d’intervention collective, les signataires désignent un représentant
				commun ; à défaut, le premier signataire les représente ({@render src('latc', 'LATC, art. 109 al. 5')}).
			</li>
			<li>
				<strong>Gratuite.</strong> Faire opposition est gratuit ({@render src('etapes', 'vd.ch')}).
			</li>
		</ul>
	</section>

	<section id="apres">
		<h2>Après l’enquête</h2>
		<p>
			Lorsque le projet requiert une autorisation cantonale, les oppositions et observations sont transmises aux
			départements concernés ({@render src('latc', 'LATC, art. 113 al. 2')}). La commune décide ensuite d’accorder
			ou de refuser le permis, et en informe le requérant et les opposants
			({@render src('etapes', 'vd.ch, étapes de la procédure')}).
		</p>
		<p>
			Pour les oppositions qui relèvent de sa compétence, la Municipalité détermine si elles sont justifiées, ce qui
			conduit à refuser le permis ou à faire modifier le projet, ou s’il convient de les lever et d’accorder le
			permis
			({@render src('cdc', 'Cour des comptes, 2021, point 14')}). Lorsqu’une opposition est écartée, l’avis
			mentionne les dispositions légales et réglementaires invoquées ({@render src('latc', 'LATC, art. 116 al. 1')}).
		</p>
	</section>

	<section id="recours">
		<h2>Recours : des conditions plus strictes</h2>
		<p>
			Le requérant ou les opposants qui contestent la décision communale peuvent recourir auprès de la Cour de droit
			administratif et public (CDAP) du Tribunal cantonal dans un délai de 30 jours
			({@render src('etapes', 'vd.ch')} ; {@render src('juridictions', 'juridictions administratives')} ;
			{@render src('lpa', 'LPA-VD, art. 95')}). Sans recours dans ce délai, la
			décision entre en force ({@render src('etapes', 'vd.ch')}).
		</p>
		<p>
			Pouvoir s’opposer ne suffit pas pour pouvoir recourir. Pour recourir, il faut en principe avoir pris part à la
			procédure précédente (par exemple par une opposition) ou en avoir été empêché, être atteint par la décision et
			avoir un <strong>intérêt digne de protection</strong> à ce qu’elle soit annulée ou modifiée
			({@render src('lpa', 'LPA-VD, art. 75 let. a')}). Le droit fédéral impose une qualité pour recourir au moins
			aussi large que devant le Tribunal fédéral ({@render src('lat', 'LAT, art. 33 al. 3 let. a')}), où le
			recourant doit être <strong>particulièrement atteint</strong> par la décision
			({@render src('ltf', 'LTF, art. 89 al. 1')}).
		</p>
		<p>
			Pour les voisins, le Tribunal fédéral admet en général cette qualité lorsque leur bien-fonds se trouve dans un
			rayon d’environ 100 mètres ; au-delà, une atteinte concrète doit être rendue vraisemblable. La distance n’est
			qu’un critère parmi d’autres : les juges procèdent à une appréciation d’ensemble des circonstances
			({@render src('atf', 'ATF 140 II 214, consid. 2.3')}).
		</p>
		<p>
			<strong>Frais.</strong> En procédure de recours, le recourant doit en principe verser une avance de frais
			({@render src('lpa', 'LPA-VD, art. 47 al. 2')}). Les frais sont supportés par la partie qui perd
			({@render src('lpa', 'art. 49 al. 1')}), qui peut aussi devoir verser une indemnité (dépens) à la partie
			qui obtient gain de cause ({@render src('lpa', 'art. 55')}).
		</p>
	</section>

	<section id="dialogue">
		<h2>S’informer et dialoguer</h2>
		<p>
			Pour toute question sur un dossier, la commune est l’interlocutrice : c’est elle qui tient le dossier à
			disposition pendant l’enquête ({@render src('rlatc', 'RLATC, art. 72 al. 2')}) et qui statue sur la demande
			({@render src('etapes', 'vd.ch')}). Il est aussi possible d’en parler directement avec le propriétaire ou
			l’auteur du projet, dont les noms figurent sur l’avis officiel ({@render src('latc', 'LATC, art. 109 al. 2')}) :
			un simple échange peut suffire à obtenir une précision.
		</p>
		<p>
			Ces échanges informels ne remplacent pas une observation ou une opposition, qui doivent être déposées par
			écrit dans le délai d’enquête ({@render src('latc', 'LATC, art. 109 al. 4')}).
		</p>
	</section>

	<section id="sources">
		<h2>Sources officielles</h2>
		<ul class="sources">
			{#each Object.values(SOURCES) as s (s.url)}
				<li><a href={s.url} target="_blank" rel="noopener">{s.titre}</a></li>
			{/each}
		</ul>
		<p class="source">
			Pour recevoir les nouveaux avis d’enquête autour d’une adresse, l’État de Vaud propose un abonnement gratuit :
			<a href="https://www.vd.ch/prestation/sabonner-aux-avis-denquete" target="_blank" rel="noopener">InfoCamac</a>.
			Voir aussi <a href={resolve('/a-propos')}>À propos</a>.
		</p>
	</section>
</main>

<style>
	.texte {
		line-height: 1.55;
	}
	.fil {
		font-size: 14px;
		color: var(--muted);
		margin: 0;
	}
	h1 {
		margin: 6px 0 12px;
		line-height: 1.2;
	}
	h2 {
		font-size: 19px;
		margin: 32px 0 8px;
		scroll-margin-top: calc(var(--header-h) + 12px);
	}
	.chapeau {
		font-size: 17px;
	}
	.avertissement {
		border: 1px solid var(--line);
		border-left: 4px solid var(--accent);
		border-radius: 8px;
		padding: 10px 14px;
		background: var(--surface-2);
		font-size: 14px;
	}
	.sommaire {
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: 8px;
		padding: 10px 14px;
		font-size: 15px;
	}
	.sommaire ol {
		margin: 0;
		padding-left: 22px;
	}
	.sommaire li a {
		display: inline-block;
		padding: 4px 0;
	}
	ul {
		padding-left: 20px;
	}
	li + li {
		margin-top: 8px;
	}
	.ref {
		white-space: nowrap;
	}
	.sources {
		font-size: 14px;
		overflow-wrap: anywhere;
	}
	@media (pointer: coarse), (max-width: 760px) {
		.sommaire li a {
			padding: 10px 0;
		}
		.sommaire li + li {
			margin-top: 0;
		}
	}
</style>
