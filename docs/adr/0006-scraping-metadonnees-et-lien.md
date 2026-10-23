# Scraping : métadonnées et lien seulement, robot poli

On ne stocke que des métadonnées et un lien : titre, date, type, auteur·e élu·e, commune, URL source. Jamais de
texte intégral, qu'il s'agisse de procès-verbaux ou d'articles. Les PDF sont lus pour en extraire les métadonnées,
jamais republiés.

## Conséquences

Le robot respecte `robots.txt`, limite son débit et s'identifie par un User-Agent qui donne une adresse de
contact. Pour les sites communaux, à partir de J3 Conseils communaux :

- **Débit.** Le robot n'envoie qu'une requête à la fois, et attend au moins 5 s entre deux requêtes vers un même
  réseau /24, ou le `Crawl-delay` du site s'il est plus grand. Il alterne entre les réseaux. L'unité est le /24, pas
  la plateforme : i-web a coupé toute sa plage au recensement, et deux plateformes qui partagent un /24 (Quicksite
  et le site du conseil de Montreux) se partagent la même cadence. Les sondes comptent dans ce débit. Le rattrapage
  et le passage ordinaire ne tournent jamais en même temps. Écartés : une seule cadence pour tout le robot (environ
  une heure par passage au lieu de 25 minutes) ; des réseaux lus en parallèle.
- **Blocage.** Une réponse 429 ou 503, une connexion refusée ou un délai dépassé arrête toute requête vers ce /24,
  sondes comprises, jusqu'à la fin du passage, ou plus longtemps si `Retry-After` le demande. Les communes de ce
  réseau que le robot n'a pas sondées sont en panne (« accès refusé »), dans l'issue `panne-source` de leur
  plateforme. Au passage suivant, une seule sonde teste le réseau avant les autres. Un 403 ou un 404 sur une seule
  page reste une panne de cette commune. Rien ne s'adapte tout seul : si un blocage revient, on ralentit ce réseau
  à la main.
- **Plafond.** Le passage ordinaire envoie au plus 60 requêtes par commune. Au-delà, l'import de la commune est en
  échec et noté dans le journal. Une requête en échec n'est pas refaite pendant le passage, mais au passage
  suivant. Le rattrapage n'a pas de plafond, mais il suit le même débit.
- **`robots.txt`.** Il est lu une fois par jour et par hôte, avant la sonde. S'il répond par une erreur 4xx, tout
  est permis. S'il répond par une erreur 5xx ou si l'hôte est injoignable, tout est interdit (RFC 9309).
  `robots.txt` règle ce que le robot lit, pas ce vers quoi le site renvoie :
  - Une page de liste interdite n'est pas sondée, et sa commune est en panne (« le site refuse les robots »). La
    déclarer non couverte reste une décision humaine.
  - Un document interdit garde son lien, mais il n'est jamais ouvert. Ce qu'il faudrait l'ouvrir pour connaître
    (le nom d'origine du fichier chez Quicksite) reste vide. Exemple : le module Conseil de Vevey n'autorise que
    ses pages de Séances et ses téléchargements. Vevey ne donne donc que des Séances.
- **Identité.** Les règles de `robots.txt` s'appliquent au nom `VigieVaud`. Le suffixe dit le rôle de la requête :
  `VigieVaud-sonde` ou `VigieVaud-import`. Le User-Agent donne le courriel de contact et un lien vers la section
  de l'À propos qui explique ce que lit le robot, à quel rythme, et comment une commune peut demander l'arrêt. Le
  robot n'est pas un robot d'IA : les interdictions qui visent nommément ces robots (Nyon, Renens) ne le
  concernent pas, mais une interdiction faite à tous (`*`) le concerne.
- **Mentions légales.** Plusieurs sites communaux soumettent toute reproduction à autorisation. Le robot ne garde
  que des métadonnées et des liens, et les actes officiels (procès-verbaux, rapports, préavis) ne sont pas
  protégés par le droit d'auteur (LDA, art. 5). On ne demande donc aucune autorisation et on n'écrit pas aux
  communes avant de les lire. Écarté : demander une autorisation, ce qui laisserait croire qu'elle est nécessaire,
  et un refus nous lierait. La licence déclarée d'une source communale le dit : « Actes officiels (art. 5 LDA) :
  métadonnées et liens seulement ».
- **Arrêt à la demande.** Une commune qui demande l'arrêt n'est plus lue et devient non couverte (« à la demande
  de la commune »). Ce qui est déjà importé reste en ligne et dans le dépôt de données, comme archive (ADR-0008).
  Une demande qui touche une personne passe par la procédure de retrait habituelle. Il en va de même d'une commune
  déclarée non couverte parce que son `robots.txt` interdit désormais le robot. Une commune a deux voies, que
  l'À propos donne dans cet ordre : interdire `VigieVaud` dans son `robots.txt`, qui arrête le robot dès le
  lendemain sans dépendre de personne, ou écrire au courriel de contact, qui l'arrête dans les 7 jours par une PR
  sur `sources.json`. Une commune qui veut seulement ralentir le robot le fait par `Crawl-delay`. Comme le robot
  tourne sur GitHub Actions, dont les adresses changent, l'À propos déconseille de le filtrer par adresse IP.
