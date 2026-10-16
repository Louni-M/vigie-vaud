<script lang="ts">
	/*
	 * PROTOTYPE (ticket #51) : ce que la couche Conseils dessine. Toutes les variantes : le marqueur du Grand Conseil,
	 * au Parlement (Cité). B : une pastille par commune avec le nombre d'objets des 30 derniers jours (son conseil
	 * plus le Grand Conseil qui la nomme). C : un cercle autour de l'hôtel de ville des communes au conseil couvert,
	 * avec la date de la prochaine séance (ou de la dernière). Marqueurs DOM : au-dessus des hôtels de ville.
	 */
	import { onMount, untrack } from 'svelte';
	import { Marker } from 'maplibre-gl';
	import type { Contexte } from '#lib/registre/types.js';
	import { CONSEILS, PARLEMENT, activite, charger, conseils, jourSemaine, dateDe, seancesDe } from './donnees.svelte.js';
	import { ouvrirGrandConseil, proto } from './proto.svelte.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();
	const map = untrack(() => ctx.map);
	const communes = untrack(() => ctx.communes);
	charger(communes);

	const telephone = () => matchMedia('(max-width: 760px) and (min-height: 521px)').matches;

	function clicGrandConseil() {
		const v = proto.variante;
		if (v === 'A') {
			ouvrirGrandConseil();
			map.flyTo({ center: PARLEMENT, zoom: Math.max(map.getZoom(), 13), offset: [0, telephone() ? -60 : 0] });
		} else if (v === 'B') {
			proto.filQui = 'Grand Conseil';
			proto.vue = 'fil';
		} else {
			proto.agendaConseil = 'VD';
			proto.vue = 'couches';
		}
	}

	function ouvrirCommune(slug: string) {
		proto.onglet = 'conseils';
		ctx.ouvrir({ commune: slug });
	}

	function el(html: string, classe: string, titre: string, clic: () => void) {
		const d = document.createElement('button');
		d.type = 'button';
		d.className = classe;
		d.title = titre;
		d.setAttribute('aria-label', titre);
		d.innerHTML = html;
		d.addEventListener('click', (e) => {
			e.stopPropagation();
			clic();
		});
		return d;
	}

	const gc = new Marker({
		element: el('<span>GC</span>', 'proto-gc', 'Grand Conseil, au Parlement (Cité, Lausanne)', clicGrandConseil),
		anchor: 'bottom'
	}).setLngLat(PARLEMENT);

	let autres: Marker[] = [];
	$effect(() => {
		const v = proto.variante;
		const actif = ctx.active;
		const xs = conseils.elements;
		untrack(() => {
			for (const m of autres) m.remove();
			autres = [];
			if (actif) gc.addTo(map);
			else gc.remove();
			if (!actif || !xs.length) return;
			if (v === 'B') {
				for (const [slug, n] of activite(30)) {
					const c = communes.find((c) => c.slug === slug);
					const total = n.communal + n.gc;
					if (!c || !total) continue;
					const titre = `${c.nom} : ${total} objet${total > 1 ? 's' : ''} en 30 jours${n.communal ? ` (${n.communal} au conseil communal)` : ''}`;
					const taille = Math.min(34, 18 + Math.sqrt(total) * 3);
					const m = new Marker({
						element: el(`<span style="--t:${taille}px">${total}</span>`, `proto-activite${n.communal ? ' communal' : ''}`, titre, () => ouvrirCommune(slug)),
						offset: [14, -10]
					}).setLngLat(c.hotel);
					autres.push(m.addTo(map));
				}
			}
			if (v === 'C') {
				for (const cs of CONSEILS) {
					if (!cs.commune) continue;
					const c = communes.find((c) => c.slug === cs.commune);
					if (!c) continue;
					const s = seancesDe(cs.commune);
					const prochaine = s.avenir[0];
					const derniere = s.passees[0];
					const texte = prochaine ? `Séance ${jourSemaine.format(dateDe(prochaine))}` : derniere ? `Dernière séance ${jourSemaine.format(dateDe(derniere))}` : '';
					const m = new Marker({
						element: el(`<span class="anneau"></span><span class="date${prochaine ? ' avenir' : ''}">${texte}</span>`, 'proto-agenda', `${cs.nom} : ${texte}`, () => ouvrirCommune(cs.commune!)),
						anchor: 'left',
						offset: [-13, 0]
					}).setLngLat(c.hotel);
					autres.push(m.addTo(map));
				}
				const s = seancesDe(null);
				const p = s.avenir[0] ?? s.passees[0];
				if (p) gc.getElement().dataset.date = `${s.avenir[0] ? '' : 'Dernière : '}${jourSemaine.format(dateDe(p))}`;
			} else delete gc.getElement().dataset.date;
		});
	});

	onMount(() => () => {
		gc.remove();
		for (const m of autres) m.remove();
	});
</script>

<style>
	:global(.proto-gc) {
		position: relative;
		display: grid;
		place-items: center;
		width: 34px;
		height: 30px;
		padding: 0;
		border: 2px solid #fff;
		border-radius: 4px 4px 2px 2px;
		background: #7a3e9d;
		color: #fff;
		font: 700 12px system-ui, sans-serif;
		box-shadow: 0 2px 6px rgb(0 0 0 / 0.35);
		cursor: pointer;
		/* Fronton du Parlement */
		clip-path: polygon(50% 0, 100% 28%, 100% 100%, 0 100%, 0 28%);
		padding-top: 6px;
	}
	:global(.proto-gc[data-date])::after {
		content: attr(data-date);
		position: absolute;
		left: 38px;
		top: 6px;
		white-space: nowrap;
		padding: 1px 6px;
		border-radius: 4px;
		background: #7a3e9d;
		color: #fff;
		font-size: 11px;
	}
	:global(.proto-activite) {
		padding: 0;
		border: 0;
		background: none;
		cursor: pointer;
	}
	:global(.proto-activite span) {
		display: grid;
		place-items: center;
		width: var(--t);
		height: var(--t);
		border-radius: 50%;
		border: 2px solid #fff;
		background: #b48fcb;
		color: #fff;
		font: 700 11px system-ui, sans-serif;
		box-shadow: 0 1px 4px rgb(0 0 0 / 0.3);
	}
	:global(.proto-activite.communal span) {
		background: #7a3e9d;
	}
	:global(.proto-agenda) {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 0;
		border: 0;
		background: none;
		cursor: pointer;
		pointer-events: auto;
	}
	:global(.proto-agenda .anneau) {
		width: 26px;
		height: 26px;
		border-radius: 50%;
		border: 3px solid #7a3e9d;
		box-shadow: 0 0 0 2px #fff;
	}
	:global(.proto-agenda .date) {
		padding: 1px 6px;
		border-radius: 4px;
		background: #fff;
		color: #7a3e9d;
		font: 600 11px system-ui, sans-serif;
		white-space: nowrap;
		box-shadow: 0 1px 3px rgb(0 0 0 / 0.25);
	}
	:global(.proto-agenda .date.avenir) {
		background: #7a3e9d;
		color: #fff;
	}
</style>
