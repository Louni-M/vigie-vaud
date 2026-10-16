# Élu·e·s nommé·e·s, particuliers masqués

Les élu·e·s sont nommé·e·s, puisqu'ils exercent un mandat public. Les noms de particuliers sont masqués
(`web/src/lib/masquage.ts`) ; les entreprises et les collectivités restent nommées.

## Conséquences

- Ce qui passe par le cron est masqué avant le commit, pas dans le navigateur : l'historique du dépôt de données est
  public et sert d'archive (ADR-0005, ADR-0008), un nom qui y entre y reste. Le cron a donc sa propre version de
  `masquage`, fidèle à celle du site.
- Pour les conseils, le masquage s'applique au titre des Objets, à celui de leurs documents et au titre des points
  d'ordre du jour, mais épargne les élu·e·s connu·e·s du conseil : toute personne qui apparaît comme contributrice
  d'un Objet de ce conseil autre qu'une pétition, sur tout l'historique. Une pétition n'affiche pas d'auteur·e : on ne
  sait pas qui l'a déposée. Ses auteur·e·s, que Lausanne nomme sans civilité dans les titres (« Pétition de Exemple
  Paul et crts »), y sont masqué·e·s comme après une civilité, sauf élu·e connu·e ou entité ; le site, qui ne masque
  que les permis, n'a pas cette règle.
  Les coordonnées d'un particulier y sont masquées avec son nom, en « [coordonnées] » : tout téléphone suisse et tout
  courriel, où qu'il soit, et l'adresse postale (voie et numéro, NPA et localité) qui suit un particulier masqué
  (« Pétition déposée le 27 août 2024 de [particulier] - [coordonnées] : »). Une adresse qui ne suit pas un particulier
  reste : c'est celle d'une entité, ou d'un immeuble ou d'un bien-fonds sujet de l'Objet (« Préavis N° 2023/44 -
  Chemin de la Colline 6-8 - Vente du bien-fonds »).
  Un titre de document est souvent le nom du fichier (« 17_17_mai_reponse_interpellation_exemple.pdf v1.0 ») ou, au
  Grand Conseil, une URL : il passe par le même masquage, qui n'y voit un nom qu'après une civilité ou « Pétition
  de ».
  Les pétitionnaires que la source connaît (prénom et nom des contributeurs d'une pétition, qu'OpenParlData donne
  mais que le dépôt n'affiche pas) sont en plus masqué·e·s dans les textes de leur pétition, sous toutes les formes
  que Lausanne leur donne : nom de fichier (« 2025_08_rp_petition_paul_exemple_parc.pdf »), sans civilité ni « de »
  (« Pétition Exemple Paul_toilettes », « par Exemple Paul et crts », « (Paul Exemple) »), nom de famille seul
  (« rapport pétition Exemple.pdf »), à la casse et aux accents près. Les textes de la pétition : son titre, ceux de
  ses documents et de ses points d'ordre du jour, et le même document joint à un autre Objet (un rapport-préavis
  qui répond à la pétition et à un postulat). Un·e élu·e connu·e reste ; un nom de famille porté par un·e élu·e
  connu·e, ou de moins de trois lettres, n'est masqué qu'avec le prénom. Ailleurs dans le conseil, le nom de
  famille seul n'est pas masqué : il masquerait des élu·e·s homonymes (prénom d'une élue = nom d'un pétitionnaire).
  OpenParlData nomme parfois un·e pétitionnaire du nom complet d'une autre personne, un·e élu·e même : le prénom et
  le nom de famille de la source comptent aussi. Au Grand Conseil, les contributeurs d'une pétition sont ses
  rapporteur·e·s, élu·e·s connu·e·s : rien n'y change. Un nom qu'OpenParlData ne connaît pas, seul dans un nom de
  fichier (« …_reponse_interpellation_exemple.pdf »), reste lisible.
  Les demandes de grâce ne sont pas des Objets, et leurs points d'ordre du jour sont retirés.
- Une amélioration du masquage vaut pour les imports suivants. L'historique n'est réécrit qu'à la main, sur demande
  ou quand un nom est signalé ; l'À propos dit comment demander un retrait.
