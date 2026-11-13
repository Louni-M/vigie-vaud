// Linter du site : configurations recommandées d'ESLint, de typescript-eslint et d'eslint-plugin-svelte, sans
// formateur (décision de #184, pour éviter un reformatage massif). Les types restent vérifiés par svelte-check.
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import { defineConfig, globalIgnores } from 'eslint/config';
import globals from 'globals';
import ts from 'typescript-eslint';

// État de référence : les constats présents à l'ajout d'ESLint (#195), gelés fichier par fichier.
// Tout nouveau constat échoue, sauf s'il reprend une règle déjà gelée dans le même fichier.
// Pour réduire : retirer une règle (ou toute la ligne) d'un fichier, lancer « pnpm exec eslint <fichier> », corriger,
// committer. Ne jamais ajouter d'entrée ici pour du code nouveau : le corriger, ou un
// « // eslint-disable-next-line <règle> -- <motif> » sur sa ligne.
const ETAT_DE_REFERENCE = {
	'src/lib/components/Consultation.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/components/DossierCarte.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/components/DossierFiche.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/conseils/FicheObjet.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/conseils/FicheSeance.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/conseils/LigneObjet.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/conseils/LigneSeance.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/conseils/Onglet.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/conseils/SourceElement.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/conseils/TeteSeance.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/conseils/Volet.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/conseils/numeros.ts': ['prefer-const'],
	'src/lib/couches/hotels-de-ville/Volet.svelte': ['no-empty-pattern'],
	'src/lib/couches/permis/Fiche.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/permis/Onglet.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/permis/Volet.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/permis/donnees.svelte.ts': ['svelte/prefer-svelte-reactivity'],
	'src/lib/couches/routes/Fiche.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/couches/routes/donnees.svelte.ts': ['svelte/prefer-svelte-reactivity'],
	'src/lib/couverture-courante.svelte.ts': ['svelte/prefer-svelte-reactivity'],
	'src/lib/fil/Fil.svelte': ['svelte/no-navigation-without-resolve'],
	'src/lib/fil/chargement.svelte.ts': ['prefer-const'],
	'src/lib/masquage.ts': ['no-control-regex'],
	'src/lib/registre/FicheOuverte.svelte': ['svelte/no-navigation-without-resolve', 'svelte/no-unused-svelte-ignore'],
	'src/lib/registre/Volet.svelte': ['svelte/no-navigation-without-resolve', 'svelte/prefer-svelte-reactivity'],
	'src/lib/registre/navigateur.ts': ['svelte/no-navigation-without-resolve'],
	'src/lib/registre/registre.svelte.ts': ['svelte/prefer-svelte-reactivity'],
	'src/lib/socle/Recherche.svelte': ['svelte/prefer-svelte-reactivity'],
	'src/routes/(carte)/+layout.svelte': ['svelte/no-navigation-without-resolve'],
	'src/routes/+error.svelte': ['svelte/no-navigation-without-resolve'],
	'src/routes/a-propos/+page.svelte': ['svelte/no-navigation-without-resolve'],
	'src/routes/couverture/+page.svelte': ['svelte/no-navigation-without-resolve'],
	'src/routes/enquete-publique/+page.svelte': ['svelte/no-navigation-without-resolve'],
	'src/routes/protection-des-donnees/+page.svelte': ['no-irregular-whitespace', 'svelte/no-navigation-without-resolve'],
	'tests/faux-navigateur.svelte.ts': ['svelte/prefer-svelte-reactivity']
};

export default defineConfig(
	globalIgnores(['build/', '.svelte-kit/', 'static/', 'src/lib/schema.ts']),
	js.configs.recommended,
	ts.configs.recommended,
	svelte.configs.recommended,
	{
		languageOptions: {
			parserOptions: { extraFileExtensions: ['.svelte'] },
			globals: { ...globals.browser, ...globals.node }
		},
		rules: {
			// TypeScript (svelte-check) vérifie déjà les noms inconnus, sans les faux positifs de no-undef sur les types.
			'no-undef': 'off',
			// Les espaces insécables de la typographie française (« : », « n° 12 », « 3 jours ») sont voulus dans les
			// textes ; la règle reste active entre les instructions du code.
			'no-irregular-whitespace': ['error', { skipStrings: true, skipTemplates: true, skipJSXText: true }],
			// Mêmes exceptions que TypeScript (noUnusedLocals, noUnusedParameters) : un paramètre préfixé par « _ »,
			// une propriété écartée par déstructuration avant un « ...reste ».
			'@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', ignoreRestSiblings: true }]
		}
	},
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: { parserOptions: { parser: ts.parser } }
	},
	Object.entries(ETAT_DE_REFERENCE).map(([fichier, regles]) => ({
		files: [fichier],
		rules: Object.fromEntries(regles.map((regle) => [regle, 'off']))
	}))
);
