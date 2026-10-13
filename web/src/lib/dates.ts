const fmt = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'long', year: 'numeric' });
const fmtCourt = new Intl.DateTimeFormat('fr-CH', { day: '2-digit', month: '2-digit', year: 'numeric' });

const parse = (iso: string) => new Date(`${iso}T00:00:00`);

export const dateLongue = (iso?: string | null) => (iso ? fmt.format(parse(iso)) : '—');
export const dateCourte = (iso?: string | null) => (iso ? fmtCourt.format(parse(iso)) : '—');

/** Jours restants jusqu'à la fin de l'enquête, jour de fin inclus (0 = dernier jour). */
export function joursRestants(fin?: string | null, aujourdhui = new Date()): number | null {
	if (!fin) return null;
	const today = new Date(aujourdhui.getFullYear(), aujourdhui.getMonth(), aujourdhui.getDate());
	return Math.round((parse(fin).getTime() - today.getTime()) / 86_400_000);
}
