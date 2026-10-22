# Vigie Vaud

Tableau de bord du canton de Vaud, destiné d'abord aux habitants : il rassemble sur une carte ce qui se passe dans
chaque commune (conseils, permis, routes, trains, presse, météo…) et informe sans prendre position. Chantiers Vaud,
l'ancien nom du site, désigne désormais sa couche Permis.

## Langage

### Carte et interface

**Couche** :
Ensemble d'éléments d'un même domaine, affiché sur la carte et activable depuis le panneau des couches (Permis,
Hôtels de ville, Routes, Trains, Incidents, Météo, Presse…). Une couche s'appuie sur une ou plusieurs sources ; la
fiche commune a un onglet par couche, qu'elle soit activée ou non. La couche Hôtels de ville est **permanente** :
on ne peut pas la désactiver.
_À éviter_ : calque, layer, module

**Volet** :
Le panneau d'une couche, ouvert depuis le panneau des couches : interrupteur, badge de fraîcheur, attribution, puis
ce que la couche y ajoute (réglages, légende, liste des éléments de la zone visible pour les Permis).
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
**approximative**. Les anciennes communes n'ont pas de marqueur.
_À éviter_ : mairie, marqueur commune

**Fiche commune** :
Le panneau d'une commune, organisé en onglets (Conseil, Permis, Presse, Radio, Météo).
_À éviter_ : page commune, profil

**Fiche du Grand Conseil** :
Le panneau du Grand Conseil, ouvert par son marqueur : ses Séances et tous ses Objets, qu'ils nomment une commune ou
non. C'est la seule fiche qui n'est pas celle d'une commune ; les conseils communaux restent dans l'onglet Conseil de
leur fiche commune.
_À éviter_ : page du Grand Conseil, fiche cantonale

**Dossier** :
Une demande de permis de construire de la CAMAC, identifiée par son numéro CAMAC.
_À éviter_ : permis (pour un dossier isolé), demande

**Fil cantonal** :
La colonne qui liste les nouveautés de toutes les sources des 14 derniers jours (Objets déposés, Séances tenues,
nouveaux dossiers, restrictions de circulation commencées), plus les Séances et les restrictions à venir, groupées par
jour. Une restriction y entre par son début, jamais par sa levée. Elle est filtrable par type et limitée à la zone
visible de la carte ou étendue à tout le canton. Elle ne dépend pas des couches activées : l'interrupteur d'une couche
gouverne la carte, pas le fil.
_À éviter_ : flux, timeline, actualités

**Nouveau dossier** :
Un dossier dont l'enquête publique a débuté depuis moins de 14 jours.
_À éviter_ : nouveau permis

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
(« importé il y a 6 h · Grand Conseil »).

**Couverture** :
Ce qu'une source apporte à chaque commune, selon deux axes : son **mode** (API, scrapé ou non couvert), déclaré
une fois pour toutes, et son **état** (disponible, en panne depuis une date donnée, surveillance interrompue, non
surveillée ou inconnu), mesuré par les sondes. Seules les sources des couches qui ont un onglet dans la fiche commune
ont une Couverture, et parmi elles seulement celles dont les éléments appartiennent à une commune, par leur position
(dossiers, restrictions de circulation) ou parce qu'ils viennent de son conseil : une source dont les éléments
n'atteignent une commune que par rattachement par nom (le Grand Conseil, la presse) **porte sur le canton** et n'a pas
de Couverture. Une couche couvre une commune dès qu'une de ses sources la couvre ; une couche dont aucune source n'a de
Couverture les couvre toutes.
Une source peut déclarer ses **limites** : ce qu'elle ne publie pas toujours dans les communes qu'elle couvre (la
DGMR : les routes communales). Elles ne changent ni le mode ni l'état.
Une commune **non couverte** par la couche choisie (sur bureau, celle dont le volet est ouvert ; sur mobile, celle
dont on a demandé à voir la Couverture) est grisée sur la carte ; une panne ne grise rien.
_À éviter_ : disponibilité (pour la Couverture entière)

**Vue** :
Sur téléphone, l'un des quatre écrans plein écran (Carte, Fil, Couches, Fiche), choisi dans la barre du bas ; une
seule est affichée à la fois.
_À éviter_ : onglet (réservé aux onglets d'une fiche commune), page

**Aperçu** :
Sur téléphone, la carte courte d'un élément ou d'une fiche ouverte, en bas de la vue Carte, avec « Voir la fiche › »
qui mène à la vue Fiche.
_À éviter_ : popup, carte (ambigu avec la carte géographique)

**Recherche** :
Le champ « Adresse, commune, n° de dossier ou d'objet » et ses résultats : communes, fiches, éléments des couches,
adresses et lieux, et « Autour de moi ». Sur téléphone, elle s'ouvre en plein écran par-dessus la vue Carte et se
referme sur la carte ; ce n'est pas une cinquième vue.
_À éviter_ : barre d'adresse, géocodeur

### Données

**Source** :
Un service ou un site d'où provient une donnée : API, flux RSS ou site scrapé. C'est à la source, pas à la couche,
que tiennent l'attribution, la voie d'accès, la fraîcheur et la Couverture.

**Plateforme** :
Le logiciel d'un éditeur sur lequel tournent les sites de plusieurs communes (i-web, Quicksite…). Les communes d'une
plateforme se lisent de la même façon ; la source reste le site de chaque commune, qui porte l'attribution et la
Couverture. Chaque commune emploie l'une des **variantes** de sa plateforme, qui dit où sont ses Séances et ses Objets
(i-web : module Séances, module Objets ou pages ; Quicksite : ancienne génération, `coreapi` ou module Conseil).
_À éviter_ : CMS, éditeur (pour la plateforme) ; registre des communes scrapées (ce sont leurs sources déclarées)

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
rattachement n'a pas de fiche commune : il n'apparaît que dans le fil cantonal et, s'il vient du Grand Conseil, dans
la fiche du Grand Conseil.
_À éviter_ : géolocalisation, affectation

**Incident** :
Un événement tiré des communiqués de la police cantonale et rattaché à une commune.

### Conseils

**Conseil** :
Un organe délibérant : le Grand Conseil, ou le conseil communal ou général d'une commune.

**Grand Conseil** :
Le parlement cantonal vaudois. Il a son propre marqueur sur la carte, au Parlement (Cité, Lausanne), qui ouvre la
fiche du Grand Conseil. Ses Objets sont rattachés aux communes qu'ils nomment ; ses Séances ne sont rattachées à aucune.

**Objet** :
Toute affaire qu'un conseil enregistre et suit (interpellation, motion, postulat, question, préavis, pétition,
projet de loi ou de décret, rapport…), sauf les demandes de grâce, avec son numéro, son titre, sa date, son type et,
quand le conseil les publie, ses auteur·e·s et son statut. Le numéro, unique dans son conseil, est celui que le conseil
lui donne (`26_INT_140`, `INT26/056`). Le type et le statut sont ceux que le conseil leur donne, sans regroupement de
notre part ; ce qu'il ne publie pas reste inconnu, jamais déduit (un préavis n'a pas d'office la Municipalité pour
auteure, ni un statut « adopté » parce que sa Séance est passée). Correspond aux *affairs* d'OpenParlData.
_À éviter_ : affaire, intervention

**Séance** :
Une réunion d'un conseil, avec sa date et son ordre du jour. Correspond aux *meetings* d'OpenParlData.
_À éviter_ : réunion, session

### Planification

**Jalon** :
Une étape de développement publiable seule (J0 à J7), avec sa branche et sa PR. Ce qui vient après J7 forme la
**phase 2**.
_À éviter_ : sprint, version
