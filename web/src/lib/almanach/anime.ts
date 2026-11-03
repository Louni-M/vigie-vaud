// Le déclencheur des animations d'une page Almanach (#165). Rendu à la construction dans son état final, qui sert
// aussi sans JavaScript, à l'impression et quand le mouvement est réduit, un élément revient à son état de départ
// (`attente`) et joue une seule fois (`joue`) quand il entre à l'écran. L'état est porté par `data-js-etat`, que seul
// ce script pose : sans lui, rien n'est caché. Les états ne s'appliquent qu'à l'écran : chaque élément animé écrit
// ses règles sous `@media screen and (prefers-reduced-motion: no-preference)`.

export function anime(n: HTMLElement) {
	if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
	n.dataset.jsEtat = 'attente';
	const observateur = new IntersectionObserver(
		(entrees) => {
			// Bien entré : 40 % de l'élément à l'écran, ou, pour un élément plus haut que l'écran, qui n'atteint jamais
			// ces 40 %, 40 % de l'écran occupés par lui.
			const entre = (e: IntersectionObserverEntry) =>
				e.intersectionRatio >= 0.4 || e.intersectionRect.height >= (e.rootBounds?.height ?? innerHeight) * 0.4;
			if (!entrees.some(entre)) return;
			n.dataset.jsEtat = 'joue';
			observateur.disconnect();
		},
		// L'élément joue quand il est bien entré, pas dès que son bord affleure en bas de l'écran.
		{ threshold: [0.1, 0.2, 0.3, 0.4], rootMargin: '0px 0px -12% 0px' }
	);
	observateur.observe(n);
	return { destroy: () => observateur.disconnect() };
}
