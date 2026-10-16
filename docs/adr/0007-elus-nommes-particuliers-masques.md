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
  de ». Un nom de famille fondu dans un nom de fichier (« …_petition_exemple_parc.pdf ») reste donc lisible.
  Les demandes de grâce ne sont pas des Objets, et leurs points d'ordre du jour sont retirés.
- Une amélioration du masquage vaut pour les imports suivants. L'historique n'est réécrit qu'à la main, sur demande
  ou quand un nom est signalé ; l'À propos dit comment demander un retrait.
