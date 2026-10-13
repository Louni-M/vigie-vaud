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

**Hôtel de ville** :
Le marqueur unique d'une commune sur la carte, qui ouvre sa fiche commune.
_À éviter_ : mairie, marqueur commune

**Fiche commune** :
Le panneau d'une commune, organisé en onglets (Conseil, Permis, Presse, Radio, Météo).
_À éviter_ : page commune, profil

**Dossier** :
Une demande de permis de construire de la CAMAC, identifiée par son numéro CAMAC.
_À éviter_ : permis (pour un dossier isolé), demande

**Fil cantonal** :
La colonne qui liste les nouveautés de toutes les sources, filtrable par type et limitée à la zone visible de la
carte.
_À éviter_ : flux, timeline, actualités

**Badge de fraîcheur** :
L'indication, sur chaque couche, de l'âge de la dernière donnée et de sa source (« il y a 4 min · DGMR »).

**Couverture** :
L'état de chaque source pour chaque commune : API, scrapé, non couvert, ou en panne depuis une date donnée.
Une commune **non couverte** est grisée sur la carte.

### Données

**Source** :
Un service ou un site d'où provient une donnée : API, flux RSS ou site scrapé. C'est à la source, pas à la couche,
que tiennent l'attribution, la voie d'accès, la fraîcheur et la Couverture.

**Voie d'accès** :
La manière dont le site obtient une source : **Direct** (le navigateur appelle la source), **Cron** (la source
passe par le cron et le dépôt de données), **Worker** (la source passe par le relais Cloudflare) ou **Préparée**
(la source est transformée une fois en fichier, publié avec le site ; par exemple les limites des communes).
_À éviter_ : backend, proxy (pour le Worker)

**Sonde** :
La requête de vérification que le cron envoie à une source, quelle que soit sa voie d'accès, sans en conserver les
données. Seules les sondes décident qu'une source est **en panne** : l'échec d'un visiteur ne change pas la
Couverture.
_À éviter_ : ping, healthcheck, test

**Rattachement** :
L'association d'un élément à une commune, par sa position (dossiers) ou par le nom de la commune dans son titre ou
sa description (éléments scrapés). Un élément sans rattachement n'apparaît que dans le fil cantonal.
_À éviter_ : géolocalisation, affectation

**Incident** :
Un événement tiré des communiqués de la police cantonale et rattaché à une commune.

### Conseils

**Conseil** :
Un organe délibérant : le Grand Conseil, ou le conseil communal ou général d'une commune.

**Grand Conseil** :
Le parlement cantonal vaudois. Il a son propre marqueur sur la carte, au Parlement (Cité, Lausanne).

**Objet** :
Une interpellation, une motion, un postulat, un préavis ou une question soumis à un conseil, avec son type, son
titre, son auteur·e, sa date et son statut. Correspond aux *affairs* d'OpenParlData.
_À éviter_ : affaire, intervention

**Séance** :
Une réunion d'un conseil, avec sa date et son ordre du jour. Correspond aux *meetings* d'OpenParlData.
_À éviter_ : réunion, session

### Planification

**Jalon** :
Une étape de développement publiable seule (J0 à J6), avec sa branche et sa PR. Ce qui vient après J6 forme la
**phase 2**.
_À éviter_ : sprint, version
