# Vigie Vaud

Tableau de bord du canton de Vaud, destiné d'abord aux habitants : il rassemble sur une carte ce qui se passe dans
chaque commune (conseils, permis, routes, trains, presse, météo…) et informe sans prendre position. Chantiers Vaud,
l'ancien nom du site, désigne désormais sa couche Permis.

## Langage

### Carte et interface

**Couche** :
Ensemble d'éléments d'un même domaine, dessiné sur la carte (Permis, Hôtels de ville, Routes, Trains, Incidents,
Météo, Presse…). Une couche s'appuie sur une ou plusieurs sources et déclare ses rubriques ; la fiche commune a un
onglet par couche. La carte ne dessine qu'une couche à la fois, la **couche dessinée** : celle de l'onglet de la fiche
commune ouverte, sinon celle de la rubrique ouverte, sinon aucune. La couche Hôtels de ville est **permanente** :
toujours dessinée, comme le marqueur du Grand Conseil.
_Mot visiteur_ : aucun ; le visiteur voit des rubriques.
_À éviter_ : calque, layer, module

**Sommaire** :
Ce que montre le panneau à l'arrivée : une ligne par rubrique, avec son nom, une phrase et son nombre d'éléments dans
la zone affichée (pour tout le canton, au Grand Conseil). Il remplace le fil cantonal comme écran d'arrivée. Ce n'est
pas le sommaire d'une page Almanach (À propos, Protection des données), qui liste ses parties.
_Mot visiteur_ : « Ce que montre Vigie Vaud » ; le lien qui y ramène, « Tous les sujets ».
_À éviter_ : accueil, menu, fil

**Rubrique** :
Un sujet tel que le visiteur le nomme, déclaré par une couche : son nom, sa phrase, son rang au sommaire, et ce qu'il
ouvre, la liste de la couche dans le panneau ou une fiche propre. Une rubrique n'est pas une couche : la couche
Conseils en déclare deux, Conseils communaux (sa liste) et Grand Conseil (sa fiche). Un sujet porte le nom de sa
rubrique partout : sommaire, liste, légende, onglet de la fiche commune, résultats de la recherche.
_Mot visiteur_ : son nom (« Permis de construire », « Routes », « Conseils communaux », « Grand Conseil ») ;
ensemble, les « sujets ».
_À éviter_ : catégorie, thème, couche (pour la rubrique)

**Panneau** :
La feuille posée sur la carte, à gauche sur bureau et en plein écran sur téléphone : le sommaire, ou la rubrique
qu'on y a ouverte, une seule à la fois. Il est dans l'adresse sous la clé `volet`.
_Mot visiteur_ : « Sujets », dans la barre du bas du téléphone.
_À éviter_ : colonne, barre latérale

**Volet** :
La liste d'une rubrique ouverte dans le panneau : le lien de retour au sommaire et le nom de la rubrique, puis ce que
la couche y met (réglages, compte et liste des éléments de la zone affichée), et après la liste les badges de
fraîcheur et l'attribution de ses sources.
_Mot visiteur_ : aucun ; le visiteur voit la rubrique ouverte.
_À éviter_ : réglages (pour le volet entier), tiroir

**Commune** :
L'une des communes vaudoises actuelles, telles que les définit le répertoire officiel de l'OFS.
_À éviter_ : localité, village (pour la commune)

**Ancienne commune** :
Une commune disparue dans une fusion (Cully, aujourd'hui dans Bourg-en-Lavaux). On la retrouve par son nom, qui
mène à la commune qui l'a absorbée.
_À éviter_ : commune fusionnée (ambigu : désigne aussi la nouvelle commune)

**Hôtel de ville** :
Le marqueur unique d'une commune sur la carte, qui ouvre sa fiche commune. Il est placé sur le siège de son
administration communale ; à défaut, sur un point de la commune en terre ferme, et sa position est alors dite
**approximative**. Les anciennes communes n'ont pas de marqueur. La légende de la carte l'explique.
_Mot visiteur_ : « Hôtel de ville ».
_À éviter_ : mairie, marqueur commune

**Fiche commune** :
Le panneau d'une commune, organisé en onglets, un par couche, chacun au nom de sa rubrique (Permis de construire,
Conseils communaux, Routes).
_Mot visiteur_ : la fiche ; « Détail » dans la barre du bas du téléphone.
_À éviter_ : page commune, profil

**Fiche du Grand Conseil** :
Le panneau du Grand Conseil, ouvert par son marqueur : ses Séances et tous ses Objets, qu'ils nomment une commune ou
non. C'est la seule fiche qui n'est pas celle d'une commune ; les conseils communaux restent dans l'onglet Conseil de
leur fiche commune.
_À éviter_ : page du Grand Conseil, fiche cantonale

**Dossier** :
Une demande de permis de construire de la CAMAC, identifiée par son numéro CAMAC.
_À éviter_ : permis (pour un dossier isolé), demande

**Restriction de circulation** :
Un tronçon de route touché par une mesure publiée par la DGMR (fermeture, déviation, feux, restriction particulière…),
avec ses dates et sa route, en cours ou à venir. Une fermeture et sa déviation sont deux restrictions distinctes.
_À éviter_ : tracé, perturbation (réservé aux Trains), chantier (Chantiers Vaud désigne la couche Permis)

**Travaux** :
Les restrictions de circulation que la DGMR publie sous un même nom pour une même route (une fermeture, sa déviation,
un sens unique…). Ce n'est pas un élément qu'on ouvre : chaque restriction renvoie aux autres de ses travaux. Deux noms
différents font deux travaux, même au même endroit (« Morcles Le Revers feux » et « … nuit »).
_À éviter_ : chantier, intervention

**Gare** :
Un point d'arrêt du train dans le canton, quel que soit l'exploitant (CFF, MOB, LEB…), marqué sur la carte par la
couche Trains ; on y consulte ses prochains départs et leurs retards. Les arrêts de métro, de bus et de bateau n'en
sont pas.
_À éviter_ : arrêt, station

**Perturbation** :
Une information sur le trafic ferroviaire (interruption, travaux, retards…) publiée par les CFF et qui touche le
canton.
_À éviter_ : incident (réservé à la police), restriction (réservé aux Routes)

**Badge de fraîcheur** :
L'indication, sur chaque couche, de l'âge de la dernière donnée et de sa source. Pour une source lue en direct qui ne
date pas ses données (la CAMAC, la DGMR), c'est l'heure de la dernière consultation (« consulté il y a 2 min ·
DGMR ») ; pour une source qui passe par le cron une fois par jour (les conseils), l'âge du dernier import réussi
(« mis à jour il y a 6 h · Grand Conseil »). Les sites d'une plateforme ont un seul badge, qui ne nomme pas la
plateforme (« mis à jour il y a 1 j · sites de 19 communes »).

**Couverture** :
Ce qu'une source apporte à chaque commune, selon deux axes : son **mode** (API, scrapé ou non couvert), déclaré
une fois pour toutes, et son **état** (disponible, en panne depuis une date donnée, surveillance interrompue, non
surveillée ou inconnu), mesuré par les sondes. Seules les sources des couches qui ont un onglet dans la fiche commune
ont une Couverture, et parmi elles seulement celles dont les éléments appartiennent à une commune, par leur position
(dossiers, restrictions de circulation) ou parce qu'ils viennent de son conseil : une source dont les éléments
n'atteignent une commune que par rattachement par nom (le Grand Conseil, la presse) **porte sur le canton** et n'a pas
de Couverture. Une couche couvre une commune dès qu'une de ses sources la couvre ; une couche dont aucune source n'a de
Couverture les couvre toutes.
La source d'un conseil communal déclare aussi son **niveau**, ce qu'elle en donne : « objets et séances »,
« séances et préavis » ou « séances seulement ». Un niveau ne change ni le mode ni l'état.
Une source peut déclarer ses **limites** : ce qu'elle ne publie pas toujours dans les communes qu'elle couvre (la
DGMR : les routes communales). Elles ne changent ni le mode ni l'état.
Une commune **non couverte** par la couche dessinée est grisée sur la carte ; une panne ne grise rien.
_Mot visiteur_ : « Sources par commune » (la page `/couverture` et ses liens) ; en tête de l'onglet d'une commune non
couverte, « Pas encore de données … pour cette commune ».
_À éviter_ : disponibilité (pour la Couverture entière)

**Vue** :
Sur téléphone, l'un des trois écrans plein écran, choisi dans la barre du bas : le panneau, la carte et la fiche ;
une seule est affichée à la fois. La fiche n'a son bouton que quand une fiche est ouverte.
_Mot visiteur_ : « Sujets », « Carte », « Détail ».
_À éviter_ : onglet (réservé aux onglets d'une fiche commune), page

**Aperçu** :
Sur téléphone, la carte courte d'un élément ou d'une fiche ouverte, en bas de la vue Carte, avec « Voir la fiche › »
qui mène à la vue Fiche.
_À éviter_ : popup, carte (ambigu avec la carte géographique)

**Recherche** :
Le champ « Adresse, commune, n° de dossier ou d'objet » et ses résultats : communes, fiches, éléments des couches,
adresses et lieux, et « Autour de moi ». Sur téléphone, elle est en tête de la carte et du panneau, s'ouvre en plein
écran par-dessus eux et se referme sur la vue d'où on l'a ouverte ; ce n'est pas une quatrième vue.
_À éviter_ : barre d'adresse, géocodeur

### Données

**Source** :
Un service ou un site d'où provient une donnée : API, flux RSS ou site scrapé. C'est à la source, pas à la couche,
que tiennent l'attribution, la voie d'accès, la fraîcheur et la Couverture.

**Destinataire** :
Un service qui reçoit des données de la visite d'un visiteur, au moins son adresse IP : l'hébergeur, les services
que le navigateur interroge lui-même (swisstopo, l'État de Vaud) et la mesure d'audience. Ce n'est pas une source :
une source lue par le cron n'est le destinataire de rien.
_À éviter_ : tiers, sous-traitant, prestataire

**Plateforme** :
Le logiciel d'un éditeur sur lequel tournent les sites de plusieurs communes (i-web, Quicksite…). Les communes d'une
plateforme se lisent de la même façon ; la source reste le site de chaque commune, qui porte l'attribution et la
Couverture. Chaque commune emploie l'une des **variantes** de sa plateforme, qui dit où sont ses Séances et ses Objets
(i-web : module Séances ; Quicksite : ancienne génération, `coreapi`, module Conseil, ou module Conseil dont la liste
des Séances est sur le site de la Ville, à Vevey).
_À éviter_ : CMS, éditeur (pour la plateforme) ; registre des communes scrapées (ce sont leurs sources déclarées)

**Recherche `coreapi`** :
La liste des documents du conseil d'un site Quicksite de nouvelle génération, que le navigateur remplit et que le
cron demande page par page (`site.coreapi`, `site.recherches`). Une commune qui sépare ses préavis et ses
procès-verbaux en a deux. Dans le code du cron, « recherche » seule désigne celle-ci ; ce n'est pas la Recherche du
site.
_À éviter_ : requête (réservé aux requêtes du robot), API

**Voie d'accès** :
La manière dont le site obtient une source : **Direct** (le navigateur appelle la source), **Cron** (la source
passe par le cron et le dépôt de données), **Worker** (la source passe par le relais Cloudflare) ou **Préparée**
(la source est transformée une fois en fichier, publié avec le site ; par exemple les limites des communes).
_À éviter_ : backend, proxy (pour le Worker)

**Sonde** :
La requête de vérification que le cron envoie à une source, quelle que soit sa voie d'accès, sans en conserver les
données. Seules les sondes décident qu'une source est **en panne** : l'échec d'un visiteur ne change pas la
Couverture, pas plus qu'un import du cron en échec, qui ne fait que vieillir le badge de fraîcheur.
_À éviter_ : ping, healthcheck, test

**Rattrapage** :
La relecture, lancée à la main, de tout l'historique qu'une source garde, pour un conseil, une plateforme ou toutes
les sources à la fois. Il complète le dépôt de données sans rien en effacer.
_À éviter_ : backfill, réimport

**Rattachement** :
L'association d'un élément à une commune : par sa position (dossiers ; restrictions de circulation, rattachées à
chaque commune qu'elles traversent), par son conseil (Objets et Séances d'un conseil communal, qui n'appartiennent
qu'à leur commune), ou, pour une source qui porte sur le canton (Grand Conseil, presse), par le nom de la commune dans
son texte. Le nom d'une ancienne commune ou un ancien nom rattache à la commune actuelle. Un élément sans
rattachement n'a pas de fiche commune : s'il vient du Grand Conseil, il apparaît dans la fiche du Grand Conseil.
_À éviter_ : géolocalisation, affectation

**Masquage** :
Le remplacement, dans un élément publié, du nom d'un particulier par « [particulier] » et de ses coordonnées par
« [coordonnées] ». Les élu·e·s connu·e·s, les entreprises et les collectivités n'en font pas l'objet ; en cas de
doute, on masque.
_À éviter_ : anonymisation, caviardage

**Retrait** :
La suppression, à la demande, d'un nom de personne d'un élément publié, historique du dépôt de données compris. Il
tient face aux imports et aux rattrapages suivants. Une commune qui demande l'arrêt du robot n'obtient pas de
retrait : elle n'est plus lue, et rien de ce qui est déjà importé n'est effacé.
_À éviter_ : suppression (pour l'arrêt d'une commune), droit à l'oubli

**Incident** :
Un événement tiré des communiqués de la police cantonale et rattaché à une commune.

### Conseils

**Conseil** :
Un organe délibérant : le Grand Conseil, ou le conseil communal ou général d'une commune.

**Grand Conseil** :
Le parlement cantonal vaudois. Il a son propre marqueur sur la carte, au Parlement (Cité, Lausanne), qui ouvre la
fiche du Grand Conseil. Ses Objets sont rattachés aux communes qu'ils nomment ; ses Séances ne sont rattachées à aucune.

**Élu·e connu·e** :
Une personne qu'un conseil laisse lisible : auteur·e d'un de ses Objets (sauf une pétition) ou membre nommé·e par sa
page des membres, un jour ou l'autre. On ne cesse pas d'être un·e élu·e connu·e à la fin de son mandat.
_À éviter_ : élu·e (pour la personne que le masquage épargne), liste blanche

**Objet** :
Toute affaire qu'un conseil enregistre et suit (interpellation, motion, postulat, question, préavis, pétition,
projet de loi ou de décret, rapport…), sauf les demandes de grâce, avec son numéro, son titre, sa date, son type et,
quand le conseil les publie, ses auteur·e·s et son statut. Le numéro, unique dans son conseil, est celui que le conseil
lui donne (`26_INT_140`, `INT26/056`). Le type et le statut sont ceux que le conseil leur donne, sans regroupement de
notre part ; ce qu'il ne publie pas reste inconnu, jamais déduit (un préavis n'a pas d'office la Municipalité pour
auteure, ni un statut « adopté » parce que sa Séance est passée). Correspond aux *affairs* d'OpenParlData.
_Mot visiteur_ : « texte déposé » ; un préavis, « proposition de la Municipalité ».
_À éviter_ : affaire, intervention

**Séance** :
Une réunion d'un conseil, avec sa date et son ordre du jour. Correspond aux *meetings* d'OpenParlData.
_À éviter_ : réunion, session

### Planification

**Jalon** :
Une étape de développement publiable seule (J0 à J7), avec sa branche et sa PR. Seul J3 Conseils communaux se
publie en **étapes de J3**, une par plateforme, chacune avec sa branche et sa PR. Ce qui vient après J7 forme la
**phase 2**.
_À éviter_ : sprint, version
