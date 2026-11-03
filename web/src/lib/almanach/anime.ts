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
			if (!entrees.some((e) => e.isIntersecting)) return;
			n.dataset.jsEtat = 'joue';
			observateur.disconnect();
		},
		// L'élément joue quand il est bien entré, pas dès que son bord affleure en bas de l'écran.
		{ threshold: 0.4, rootMargin: '0px 0px -12% 0px' }
	);
	observateur.observe(n);
	return { destroy: () => observateur.disconnect() };
}
