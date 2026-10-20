"""Ce que publient les conseils communaux, plateforme par plateforme (issue #119) : le robot de mesure.

Un seul outil, pour lire poliment quelques pages par commune et les relire ensuite sans refaire de requête :

    python3 -I docs/recherche/publications-conseils.py --cache /chemin/cache get URL [URL…]
    python3 -I docs/recherche/publications-conseils.py --cache /chemin/cache lot fichier-d-urls.txt
    python3 -I docs/recherche/publications-conseils.py --cache /chemin/cache pdf URL
    python3 -I docs/recherche/publications-conseils.py --cache /chemin/cache liens URL [motif]
    python3 -I docs/recherche/publications-conseils.py --cache /chemin/cache texte URL
    python3 -I docs/recherche/publications-conseils.py --cache /chemin/cache entites URL     # tableaux i-web

et pour le balayage de toutes les communes des plateformes (les passes 2 et 3 se calculent d'après le cache) :

    … balayage-1 > p1.txt ; … lot p1.txt
    … balayage-2 > p2.txt ; … lot p2.txt
    … balayage-3 > p3.txt ; … lot p3.txt
    … classer > docs/recherche/publications-conseils.csv
    … particuliers > /hors/du/depot.csv    # civilité + nom hors contexte d'élu·e, noms masqués

`--sites` donne le CSV du recensement (#118), qui fournit la plateforme de chaque hôte.

Règles tenues par le code, et non par la bonne volonté de celui qui le lance (ADR-0006) :

- **Une requête à la fois.** Un verrou de fichier (`fcntl`) empêche deux processus de tourner ensemble ; aucun fil.
- **Au moins 5 secondes entre deux requêtes vers le même réseau /24 ou la même plateforme** (plateforme lue dans
  `sites-communaux.csv` d'après le nom d'hôte), davantage si `Crawl-delay` le demande. Les dernières heures sont
  gardées dans le cache : elles valent d'un lancement à l'autre.
- **`robots.txt` d'abord**, lu une fois par hôte avec le User-Agent du recensement (#118) ; une URL interdite n'est
  pas demandée. Les redirections sont suivies à la main, chaque saut repassant par ces contrôles.
- **Blocage** : 403, 429, 503, connexion refusée ou délai dépassé bloquent le /24 et la plateforme pendant
  30 minutes ; le script refuse d'y retourner avant.
- **Cache** : chaque réponse est gardée (hors du dépôt) et jamais redemandée.
- **Plafonds** : 30 pages par commune, 3 PDF par plateforme. Hors de la commande `pdf`, une réponse PDF n'est pas
  téléchargée (on lit les en-têtes, puis on ferme).

Bibliothèque standard seulement (Python 3.11 ou plus). `pdffonts` et `pdftotext` (poppler) servent à savoir si un
PDF a une couche texte.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import gzip
import hashlib
import html
import json
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

UA = "VigieVaud-recherche/0.1 (+https://github.com/Louni-M/vigie-vaud)"
DELAI_MIN = 5.0          # secondes entre deux requêtes au même /24 ou à la même plateforme
BLOCAGE = 30 * 60        # secondes de pause après un signe de blocage
PAGES_PAR_COMMUNE = 30
PDF_PAR_PLATEFORME = 3
STATUTS_BLOCAGE = {403, 429, 503}
ICI = Path(__file__).resolve().parent


# --- Registre des sites (#118) ------------------------------------------------------------------------


def _hote(url: str) -> str:
    h = (urlsplit(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def charger_sites(chemin: Path) -> dict[str, dict]:
    """hôte (sans www) -> ligne du recensement."""
    sites = {}
    for ligne in csv.DictReader(chemin.open(encoding="utf-8")):
        for col in ("site", "url_finale", "page_conseil"):
            if ligne[col]:
                sites.setdefault(_hote(ligne[col]), ligne)
    return sites


# --- État persistant ----------------------------------------------------------------------------------


class Etat:
    def __init__(self, cache: Path):
        self.chemin = cache / "etat.json"
        d = json.loads(self.chemin.read_text()) if self.chemin.exists() else {}
        self.derniere: dict[str, float] = d.get("derniere", {})
        self.blocages: dict[str, dict] = d.get("blocages", {})
        self.pages: dict[str, int] = d.get("pages", {})
        self.pdf: dict[str, int] = d.get("pdf", {})
        self.delais: dict[str, float] = d.get("delais", {})
        self.journal: list = d.get("journal", [])

    def sauver(self) -> None:
        self.chemin.write_text(json.dumps({
            "derniere": self.derniere, "blocages": self.blocages, "pages": self.pages, "pdf": self.pdf,
            "delais": self.delais, "journal": self.journal[-5000:]}, ensure_ascii=False, indent=1))


class Refus(Exception):
    pass


class Robot:
    def __init__(self, cache: Path, sites: dict[str, dict]):
        self.cache = cache
        (cache / "rep").mkdir(parents=True, exist_ok=True)
        (cache / "pdf").mkdir(parents=True, exist_ok=True)
        self.sites = sites
        self.etat = Etat(cache)
        self._ips: dict[str, str] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._ctx_libre = ssl._create_unverified_context()

    # Clés de débit : le /24 de l'adresse et la plateforme.
    def cles(self, url: str) -> list[str]:
        h = urlsplit(url).hostname or ""
        if h not in self._ips:
            try:
                self._ips[h] = socket.gethostbyname(h).rsplit(".", 1)[0]
            except OSError:
                self._ips[h] = h
        ligne = self.sites.get(_hote(url))
        plateforme = ligne["plateforme"] if ligne else "hôte " + _hote(url)
        if plateforme in ("i-web", "OIOI web"):
            plateforme = "i-web/OIOI"  # une partie des sites i-web partage le serveur d'OIOI web (164.128.171.231)
        return ["/24 " + self._ips[h], "plateforme " + plateforme]

    def site(self, url: str) -> str:
        ligne = self.sites.get(_hote(url))
        return f"{ligne['ofs']} {ligne['commune']}" if ligne else _hote(url)

    def _attendre(self, url: str) -> list[str]:
        cles = self.cles(url)
        maintenant = time.time()
        for c in cles:
            b = self.etat.blocages.get(c)
            if b and maintenant - b["t"] < BLOCAGE:
                raise Refus(f"{c} bloqué depuis {time.strftime('%H:%M', time.localtime(b['t']))} ({b['raison']})")
        delai = max([DELAI_MIN] + [self.etat.delais.get(c, 0) for c in cles])
        reste = max(self.etat.derniere.get(c, 0) + delai - time.time() for c in cles)
        if reste > 0:
            time.sleep(reste)
        for c in cles:
            self.etat.derniere[c] = time.time()
        self.etat.sauver()
        return cles

    # Cache
    def _fichier(self, url: str) -> Path:
        return self.cache / "rep" / hashlib.sha1(url.encode()).hexdigest()

    def en_cache(self, url: str) -> dict | None:
        f = self._fichier(url).with_suffix(".json")
        return json.loads(f.read_text()) if f.exists() else None

    def corps(self, url: str) -> bytes:
        return self._fichier(url).with_suffix(".corps").read_bytes()

    def _requete(self, url: str, accepter_pdf: bool) -> dict:
        """Une requête HTTP, sans suivre les redirections, en passant par le limiteur."""
        cles = self._attendre(url)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip",
                                                   "Accept-Language": "fr-CH,fr;q=0.9"})
        ouvreur = urllib.request.build_opener(_SansRedirection, urllib.request.HTTPSHandler(context=self._ctx_libre))
        t0 = time.time()
        rep: dict = {"url": url, "date": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        corps = b""
        try:
            try:
                r = ouvreur.open(req, timeout=40)
            except urllib.error.HTTPError as e:
                r = e
            rep["statut"] = r.status if hasattr(r, "status") else r.code
            rep["entetes"] = {k.lower(): v for k, v in dict(r.headers or {}).items()}
            type_ = rep["entetes"].get("content-type", "")
            est_pdf = "pdf" in type_.lower()
            if est_pdf and not accepter_pdf:
                rep["non_lu"] = "PDF non téléchargé"
            else:
                corps = r.read(25_000_000 if accepter_pdf else 6_000_000)
            r.close()
        except Exception as e:  # délai, connexion refusée, DNS…
            rep["erreur"] = f"{type(e).__name__}: {e}"
        rep["duree"] = round(time.time() - t0, 2)
        if rep.get("entetes", {}).get("content-encoding", "").lower() == "gzip" or corps[:2] == b"\x1f\x8b":
            try:
                corps = gzip.decompress(corps)
            except OSError:
                pass
        signe = rep.get("statut") in STATUTS_BLOCAGE or (
            "erreur" in rep and re.search(r"refused|timed out|timeout|reset", rep["erreur"], re.I))
        if signe:
            for c in cles:
                self.etat.blocages[c] = {"t": time.time(), "raison": rep.get("erreur") or rep["statut"], "url": url}
        self.etat.journal.append([rep["date"], url, rep.get("statut") or rep.get("erreur"), rep["duree"]])
        self.etat.sauver()
        f = self._fichier(url)
        f.with_suffix(".corps").write_bytes(corps)
        f.with_suffix(".json").write_text(json.dumps(rep, ensure_ascii=False))
        if signe:
            raise Refus(f"signe de blocage sur {url} : {rep.get('erreur') or rep['statut']} ; pause de 30 min")
        return rep

    def _robots_de(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        p = urlsplit(url)
        racine = f"{p.scheme}://{p.netloc}"
        if racine in self._robots:
            return self._robots[racine]
        r_url = racine + "/robots.txt"
        rep = self.en_cache(r_url) or self._requete(r_url, False)
        rp = None
        texte = self.corps(r_url).decode("utf-8", "replace") if rep.get("statut") == 200 else ""
        if texte and not re.search(r"<html|<!doctype", texte[:500], re.I):
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(texte.splitlines())
            d = rp.crawl_delay(UA)
            if d:
                for c in self.cles(url):
                    self.etat.delais[c] = max(self.etat.delais.get(c, 0), float(d))
                self.etat.sauver()
        self._robots[racine] = rp
        return rp

    def get(self, url: str, pdf: bool = False, sauts: int = 6) -> dict:
        """GET poli avec cache ; suit les redirections. Rend la dernière réponse (avec `finale`)."""
        url = urllib.parse.quote(url.split("#")[0], safe=":/?&=%+;,@!$'()*~")  # accents dans le chemin
        rep = self.en_cache(url)
        if rep is None:
            rp = self._robots_de(url)
            if rp and not rp.can_fetch(UA, url):
                raise Refus(f"robots.txt interdit {url}")
            site = self.site(url)
            plateforme = self.cles(url)[1]
            if pdf:
                if self.etat.pdf.get(plateforme, 0) >= PDF_PAR_PLATEFORME:
                    raise Refus(f"plafond de {PDF_PAR_PLATEFORME} PDF atteint pour {plateforme}")
            elif self.etat.pages.get(site, 0) >= PAGES_PAR_COMMUNE:
                raise Refus(f"plafond de {PAGES_PAR_COMMUNE} pages atteint pour {site}")
            rep = self._requete(url, pdf)
            if pdf and "pdf" in rep.get("entetes", {}).get("content-type", "").lower():
                self.etat.pdf[plateforme] = self.etat.pdf.get(plateforme, 0) + 1
            elif not pdf:
                self.etat.pages[site] = self.etat.pages.get(site, 0) + 1
            self.etat.sauver()
        lieu = rep.get("entetes", {}).get("location")
        if rep.get("statut") in (301, 302, 303, 307, 308) and lieu and sauts:
            suite = self.get(urljoin(url, lieu), pdf, sauts - 1)
            return suite
        rep["finale"] = url
        return rep

    def decoder(self, rep: dict) -> str:
        corps = self.corps(rep["finale"])
        m = re.search(r"charset=([\w-]+)", rep.get("entetes", {}).get("content-type", ""), re.I) or \
            re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", corps[:4000], re.I)
        enc = (m[1].decode() if isinstance(m[1], bytes) else m[1]) if m else "utf-8"
        try:
            return corps.decode(enc, errors="replace")
        except LookupError:
            return corps.decode("utf-8", errors="replace")


class _SansRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


# --- Lecture des pages en cache ----------------------------------------------------------------------

LIEN = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S | re.I)


def texte_brut(fragment: str) -> str:
    fragment = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def liens(page: str, base: str) -> list[tuple[str, str]]:
    out = []
    for m in LIEN.finditer(page):
        h = re.search(r"href\s*=\s*[\"']([^\"']+)", m[1])
        if h and not h[1].startswith(("mailto:", "tel:", "javascript:")):
            titre = re.search(r"title\s*=\s*[\"']([^\"']+)", m[1])
            out.append((urljoin(base, html.unescape(h[1]).strip()),
                        texte_brut(m[2]) or (html.unescape(titre[1]) if titre else "")))
    return out


def couche_texte(chemin: Path) -> dict:
    """Polices déclarées et nombre de caractères extraits : un PDF scanné n'a ni l'un ni l'autre."""
    polices = subprocess.run(["pdffonts", str(chemin)], capture_output=True, text=True).stdout.splitlines()[2:]
    texte = subprocess.run(["pdftotext", "-l", "3", str(chemin), "-"], capture_output=True, text=True).stdout
    info = subprocess.run(["pdfinfo", str(chemin)], capture_output=True, text=True).stdout
    return {"polices": len(polices), "caracteres_3_pages": len(texte.strip()),
            "producteur": " ".join(re.findall(r"^(?:Producer|Creator):\s*(.*)$", info, re.M)),
            "pages": (re.search(r"^Pages:\s*(\d+)", info, re.M) or [None, "?"])[1]}


# --- Balayage : la page du conseil de chaque commune d'une plateforme ---------------------------------

PLATEFORMES = ["i-web", "Quicksite", "WebForge", "COMMUNEapp WEB", "imedia Communes", "OIOI web", "Webcommunes",
               "Hekl@"]


def plateforme(ligne: dict) -> str:
    """La plateforme du recensement (#118), corrigée : son motif `i-web\\.ch` attrape aussi `oioi-web.ch`, si bien
    que les sites OIOI web du serveur 164.128.171.231 y sont comptés comme i-web."""
    if ligne["plateforme"] == "i-web" and "i-web.ch" in ligne["indices"] and ligne["ip"] == "164.128.171.231":
        return "OIOI web"
    return ligne["plateforme"]


def communes_des_plateformes(chemin: Path) -> list[dict]:
    lignes = [l for l in csv.DictReader(chemin.open(encoding="utf-8")) if plateforme(l) in PLATEFORMES]
    for l in lignes:
        l["plateforme_corrigee"] = plateforme(l)
    return lignes


def balayage_1(chemin: Path) -> list[str]:
    """Première passe : la page du conseil trouvée par le recensement, sinon la page d'accueil. Les communes sont
    alternées d'une plateforme à l'autre, pour que le délai par plateforme se fasse pendant qu'on lit les autres
    (une requête à la fois, toujours)."""
    par_plateforme: dict[str, list[str]] = {p: [] for p in PLATEFORMES}
    for l in communes_des_plateformes(chemin):
        par_plateforme[l["plateforme_corrigee"]].append(l["page_conseil"] or l["url_finale"] or l["site"])
    urls = []
    while any(par_plateforme.values()):
        for p in PLATEFORMES:
            if par_plateforme[p]:
                urls.append(par_plateforme[p].pop(0))
    return urls


SOUS_PAGE = re.compile(r"s[ée]ance|sitzung|ordres? du jour|proc[èe]s|\bpv\b|pr[ée]avis|objets? politiques|motions|"
                       r"postulats|interpellations|documents?(?: du)? conseil|d[ée]cisions du conseil|archives", re.I)
HORS_SUJET = re.compile(r"municipal(?:e|ité)?s? ?$|d[ée]cisions municipales|enqu[êe]tes?|votations?|[ée]lections?|"
                        r"commissions?$|membres|composition|bureau|contact|r[èe]glement", re.I)


def page_de(robot: Robot, url: str) -> tuple[str, str] | None:
    """(URL finale, HTML) d'une page en cache, en suivant les redirections dans le cache seulement."""
    url = url.split("#")[0]
    for _ in range(6):
        rep = robot.en_cache(url)
        if rep is None or "erreur" in rep:
            return None
        lieu = rep.get("entetes", {}).get("location")
        if rep.get("statut") in (301, 302, 303, 307, 308) and lieu:
            url = urljoin(url, lieu).split("#")[0]
            continue
        if rep.get("statut") != 200 or rep.get("non_lu"):
            return None
        rep["finale"] = url
        return url, robot.decoder(rep)
    return None


def balayage_2(robot: Robot, chemin: Path, par_commune: int = 4) -> list[str]:
    """Deuxième passe : depuis la page lue en première passe, les sous-pages du même site qui parlent de séances,
    de préavis ou d'objets (au plus `par_commune`), plus, pour Quicksite, la recherche `coreapi` qui remplit les
    pages de documents de sa nouvelle génération."""
    urls: list[str] = []
    for l in communes_des_plateformes(chemin):
        # La page du conseil, ou à défaut (lien mort, erreur) la page d'accueil.
        p = page_de(robot, l["page_conseil"]) if l["page_conseil"] else None
        p = p or page_de(robot, l["url_finale"] or l["site"])
        if not p:
            continue
        finale, page = p
        hote = urlsplit(finale).hostname
        par_texte, par_adresse = [], []
        for lien, texte in liens(page, finale):
            lien = lien.split("#")[0]
            if urlsplit(lien).hostname != hote or lien == finale or ".pdf" in lien.lower():
                continue
            if "_doc/" in lien or "download" in lien.lower() or "/files/" in lien or "idm_medias" in lien:
                continue
            chemin_lien = urllib.parse.unquote(urlsplit(lien).path)
            if SOUS_PAGE.search(texte) and not HORS_SUJET.search(texte):
                par_texte.append(lien)
            elif SOUS_PAGE.search(chemin_lien.replace("-", " ")) and not HORS_SUJET.search(chemin_lien):
                par_adresse.append(lien)  # « Voir la liste », « Lire l'article » : l'adresse dit de quoi il s'agit
        choisis = list(dict.fromkeys(par_texte))[:par_commune]
        choisis += [x for x in dict.fromkeys(par_adresse) if x not in choisis][:2]
        urls += choisis
        urls += coreapi(page, finale)
    return list(dict.fromkeys(urls))


def balayage_3(robot: Robot, chemin: Path) -> list[str]:
    """Troisième passe : la recherche `coreapi` des sous-pages Quicksite trouvées en deuxième passe."""
    urls = []
    for u in balayage_2(robot, chemin):
        p = page_de(robot, u)
        if p:
            urls += coreapi(p[1], p[0])
    return list(dict.fromkeys(urls))


def coreapi(page: str, base: str) -> list[str]:
    """La requête que fait le navigateur pour remplir une page Quicksite de nouvelle génération (fragment HTML)."""
    s = re.search(r"/coreapi/elasticsearch/projects/([\w-]+)/assets/js/elasticsearch\.js", page)
    m = re.search(r'<section[^>]*class="tplDeepsearch"(.*?)>', page, re.S)
    if not (s and m):
        return []
    attrs = dict(re.findall(r'data-elasticsearch-([\w-]+)="([^"]*)"', m[1]))
    if "node" not in attrs:
        return []
    from urllib.parse import urlencode
    params = {"q": ""}
    for k in ("project", "node", "pagesize", "nodetype", "parentnode", "sort", "view", "query", "result",
              "filtertags", "initresult"):
        params["elasticsearch" + k.capitalize()] = attrs.get(k, "")
    params.update({"query": "", "date_from": "", "date_to": ""})
    return [urljoin(base, f"/coreapi/elasticsearch/projects/{s[1]}/{attrs.get('view', 'default')}/search?")
            + urlencode(params)]


# --- Classement : ce qu'un scraper déterministe tirerait de ces pages ------------------------------------

MOIS = "janvier février fevrier mars avril mai juin juillet août aout septembre octobre novembre décembre decembre"
N_MOIS = {m: i for i, m in zip([1, 2, 2, 3, 4, 5, 6, 7, 8, 8, 9, 10, 11, 12, 12], MOIS.split())}
DATE_LONGUE = re.compile(r"\b(\d{1,2})(?:er)?\s+(" + "|".join(MOIS.split()) + r")\s+(20\d\d)\b", re.I)
DATE_COURTE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](20\d\d|\d\d)\b")
PREAVIS = re.compile(r"pr[ée]avis(?: municipal)?(?:\s+(?:n[°o]\.?|nr\.?|no|\|))?\s*(?:\|\s*)?(?:"
                     r"(\d{1,3})\s*[/_-]\s*((?:19|20)?\d\d)\b|((?:19|20)\d\d)\s*[/_-]\s*(\d{1,3})\b|(\d{1,3})\s*\|\s*(20\d\d))"
                     r"|\bPM\s?(20\d\d)[-_](\d{1,2})|\bn°\s?(\d{1,2})[- ](20\d\d)\b", re.I)
AUTRES = re.compile(r"\b(motion|postulat|interpellation|question|p[ée]tition|r[ée]solution)s?\b\s+(?:n°\s?\S+\s+)?"
                    r"(?:de|du|des|d'|intitul|«|\")", re.I)
CONTEXTE_SEANCE = re.compile(r"s[ée]ance|conseil|\bpv\b|proc[èe]s|ordre du jour|convocation|\bodj\b|\boj\b", re.I)


def _dates(texte: str) -> list[tuple[int, int, int]]:
    out = []
    for m in DATE_LONGUE.finditer(texte):
        out.append((int(m[3]), N_MOIS[m[2].lower()], int(m[1])))
    for m in DATE_COURTE.finditer(texte):
        a = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
        if 1 <= int(m[2]) <= 12 and 1 <= int(m[1]) <= 31:
            out.append((a, int(m[2]), int(m[1])))
    return [d for d in out if 1990 <= d[0] <= 2030]


def signaux(pages: list[str]) -> dict:
    """Comptages bruts sur les pages d'une commune (texte visible et données i-web)."""
    seances, preavis, autres, toutes = set(), set(), set(), []
    iweb_seances = iweb_objets = 0
    recueils = {"preavis": 0, "pv": 0}  # i-web : recueils annuels (« Préavis 2023 », « 2024 ») à ouvrir un par un
    for page in pages:
        texte_entites = []
        rubrique = re.findall(r"([^>]{1,60}?)\s*\(sélectionné\)", texte_brut(page))
        for m in re.finditer(r'<table[^>]*\bid="([^"]*)"[^>]*data-entities="([^"]*)"', page):
            try:
                rangs = json.loads(html.unescape(m[2])).get("data", [])
            except ValueError:
                continue
            n = len(rangs)
            contenu = texte_brut(" | ".join(str(v) for r in rangs for k, v in r.items() if not k.endswith("-sort")))
            if "FutureSitzungen" not in m[1]:
                texte_entites.append(contenu)
            if "PastSitzungen" in m[1]:
                iweb_seances += n
                for d in _dates(contenu):
                    seances.add(d)
            if "geschaefte" in m[1].lower():
                iweb_objets += n
            if m[1] == "publikation" and rubrique:
                if re.search(r"(?i)pr[ée]avis", rubrique[-1]):
                    recueils["preavis"] += n
                elif re.search(r"(?i)proc[èe]s|\bpv\b|s[ée]ances", rubrique[-1]):
                    recueils["pv"] += n
        texte = texte_brut(page) + " " + " ".join(texte_entites)
        # Fenêtres autour des mots de séance : les dates qui y tombent sont des dates de séance.
        for m in CONTEXTE_SEANCE.finditer(texte):
            for d in _dates(texte[m.start(): m.end() + 60]):
                seances.add(d)
        for m in PREAVIS.finditer(texte):
            g = [x for x in m.groups() if x]
            preavis.add(tuple(g[:2]))
        for m in AUTRES.finditer(texte):
            autres.add(texte[m.start(): m.start() + 80])
        toutes += _dates(texte)
    passees = sorted(d for d in seances if d <= (2026, 10, 20))
    return {"seances": max(len(seances), iweb_seances), "preavis": len(preavis), "autres_objets": len(autres),
            "iweb_seances": iweb_seances, "iweb_objets": iweb_objets,
            "recueils_preavis": recueils["preavis"], "recueils_pv": recueils["pv"],
            "depuis": passees[0][0] if passees else "", "derniere_seance": "%04d-%02d-%02d" % passees[-1] if passees else ""}


def niveau(s: dict) -> str:
    if s["iweb_objets"] or (s["preavis"] >= 3 and s["autres_objets"] >= 5 and s["seances"] >= 2):
        return "Objets complets"
    seances = s["seances"] >= 2 or s.get("recueils_pv", 0) >= 1
    preavis = s["preavis"] >= 2 or s.get("recueils_preavis", 0) >= 1
    if seances and preavis:
        return "Séances et préavis"
    if seances:
        return "Séances seules"
    if preavis:
        return "Préavis seuls"
    return "rien"


# Niveau constaté à la main sur les communes de l'échantillon (lecture des pages, voir le .md) : il l'emporte sur
# l'estimation automatique. n° OFS -> (niveau, note).
ECHANTILLON: dict[int, tuple[str, str]] = {
    5892: ("Objets complets", "i-web, modules Séances et Objets ; statut pas tenu"),
    5643: ("Séances et préavis", "i-web, module Séances ; préavis en recueil"),
    5851: ("Séances et préavis", "i-web, module Séances ; OdJ en texte ; préavis par année"),
    5674: ("Séances seules", "i-web, séances à venir et recueil de PV"),
    5401: ("Objets complets", "Quicksite ancien, bibliothèque typée (préavis, décisions, M/P/I numérotés)"),
    5717: ("Séances et préavis", "Quicksite nouveau, coreapi groupé par séance ; postulats en documents"),
    5798: ("Séances et préavis", "Quicksite nouveau, coreapi ; PV et préavis, dates de séance fausses"),
    5409: ("Objets complets", "Quicksite, module Conseil (comme Montreux) : 567 documents typés et numérotés"),
    5806: ("Séances et préavis", "WebForge, page de séances ; 2025-2026 seulement"),
    5496: ("Séances et préavis", "WebForge, PV et préavis depuis 2021"),
    5472: ("Séances et préavis", "WebForge, PV depuis 2021, préavis 2025"),
    5516: ("Séances et préavis", "COMMUNEapp, PV depuis 2022, préavis depuis 2021"),
    5706: ("Séances et préavis", "COMMUNEapp, convocations, PV, préavis et décisions"),
    5803: ("Séances et préavis", "COMMUNEapp, OdJ et préavis depuis 2024"),
    5635: ("Séances et préavis", "imedia, OdJ depuis 2007, préavis par séance ; réponses aux interpellations"),
    5518: ("Objets complets", "imedia, préavis, postulats et motions avec rapports ; PDF interdits par robots"),
    5403: ("Séances seules", "imedia, PV depuis 2016 ; PDF interdits par robots"),
    5464: ("Séances et préavis", "OIOI, page par année : séance, points, préavis, postulats"),
    5412: ("Séances et préavis", "OIOI, PV par séance, préavis par législature"),
    5426: ("rien", "OIOI, un PDF compilé par année"),
    5422: ("Objets complets", "Webcommunes, OdJ/PV, préavis datés, motions et postulats"),
    5648: ("Objets complets", "Webcommunes, motions/postulats/interpellations avec auteur et statut en texte"),
    5911: ("Séances et préavis", "Webcommunes, archives par séance"),
    5804: ("Séances seules", "Hekl@, 10 derniers PV"),
    5622: ("Séances seules", "Hekl@, prochaine séance seulement"),
}

# Villes sur mesure lues à la main (n° OFS -> commune, habitants, technique, niveau, note).
VILLES: dict[int, tuple[str, int, str, str, str]] = {
    5886: ("Montreux", 26955, "module Conseil de Quicksite (conseilmontreux.ch)", "Objets complets",
           "séances depuis 2006, points d'OdJ liés aux Objets, auteur ; pas de statut"),
    5724: ("Nyon", 23351, "Nuxt (iomedia)", "Objets complets",
           "séances 2008-2026 (état planifiée/tenue), Objets par séance, date de dépôt, décisions"),
    5591: ("Renens", 21541, "Nuxt (iomedia)", "Objets complets",
           "50 séances 2020-2026, 1 060 documents, statut (Accepté, Répondu) ; menu en JS, entrée par le sitemap"),
    5890: ("Vevey", 20142, "Drupal + module Conseil de Quicksite (conseil.vevey.ch)", "Objets complets",
           "documents filtrés par type et auteur, codes 2026/P12 ; robots restrictif sur conseil.vevey.ch"),
    5590: ("Pully", 19538, "Umbraco", "Objets complets",
           "une page de 3 Mo, 1 364 PDF, Objets numérotés 2018-2026 avec auteur·e, statut en texte libre"),
    5642: ("Morges", 17701, "Symfony (iomedia)", "Objets complets",
           "8 types d'Objets par année 2004-2026, n° et date ; séances : page de dates"),
    5721: ("Gland", 13987, "TYPO3", "Objets complets",
           "page par séance, Objets avec auteur·e et statut (Traité, Refusé)"),
    5889: ("La Tour-de-Peilz", 12812, "PHP maison (Equateur)", "Objets complets",
           "préavis Nr./année, motions/postulats/interpellations avec auteur·e, parti et statut en texte"),
    5589: ("Prilly", 12758, "TYPO3 (WNG)", "Séances et préavis",
           "page par année : OdJ, préavis, rapports ; chemins de PDF très réguliers"),
}


def classer(robot: Robot, chemin: Path) -> list[dict]:
    """Toutes les pages HTML en cache d'un site comptent : ce sont celles que les passes (et la lecture à la main de
    l'échantillon) ont choisies, à part la page d'accueil et les mentions légales, sans effet sur les comptages."""
    par_hote: dict[str, list[str]] = {}
    for f in sorted((robot.cache / "rep").glob("*.json")):
        r = json.loads(f.read_text())
        if r.get("statut") == 200 and "html" in r.get("entetes", {}).get("content-type", ""):
            par_hote.setdefault(_hote(r["url"]), []).append(r["url"])
    lignes = []
    for l in communes_des_plateformes(chemin):
        hote = _hote(l["url_finale"] or l["site"])
        pages = [p[1] for p in (page_de(robot, u) for u in par_hote.get(hote, [])) if p]
        s = signaux(pages)
        auto = niveau(s)
        main = ECHANTILLON.get(int(l["ofs"]))
        lignes.append({"ofs": l["ofs"], "commune": l["commune"], "habitants": l["habitants"], "conseil": l["conseil"],
                       "plateforme": l["plateforme_corrigee"], "mesure": "échantillon" if main else "balayage",
                       "pages_lues": len(pages), **s, "niveau_auto": auto, "niveau": main[0] if main else auto,
                       "note": main[1] if main else ""})
    for ofs, (commune, hab, techno, niv, note) in VILLES.items():
        vide = {k: "" for k in ("pages_lues", "seances", "preavis", "autres_objets", "iweb_seances", "iweb_objets",
                                "recueils_preavis", "recueils_pv", "depuis", "derniere_seance", "niveau_auto")}
        lignes.append({"ofs": ofs, "commune": commune, "habitants": hab, "conseil": "conseil communal",
                       "plateforme": "sur mesure : " + techno, "mesure": "échantillon", **vide, "niveau": niv,
                       "note": note})
    return lignes


# --- Noms de particuliers : repérage, sans jamais les écrire ---------------------------------------------

CIVILITE = re.compile(r"\b(M\.|MM\.|Mme|Mmes|Mlle|Monsieur|Madame)\s+((?:[A-ZÀ-Ý][\w'’-]+\s*){1,4})")
ELU = re.compile(r"(?i)conseill[eè]re?s?|syndi(?:c|que)|municipa(?:l|le|ux)|consorts|interpell|postulat|motion|"
                 r"question|r[ée]solution|\brapp\.|pr[ée]sident|secr[ée]taire|d[ée]put[ée]|groupe|parti|huissi|"
                 r"scrutat|commission|vice|d[ée]l[ée]gu")
SUJETS_PRIVES = re.compile(r"(?i)succession|naturalisation|bourgeoisie|en faveur de|propri[ée]taire|"
                           r"p[ée]tition de|vente (?:à|a) |achat (?:à|a) |servitude|droit de superficie")


def particuliers(robot: Robot, urls: list[str]) -> list[dict]:
    """Les mentions « civilité + nom » hors contexte d'élu·e (fenêtre de 80 caractères avant), et les titres qui
    portent sur une affaire privée. Le nom est remplacé par [X] : rien de nominatif ne sort d'ici."""
    vus, out = set(), []
    for u in urls:
        p = page_de(robot, u)
        if not p:
            continue
        texte = texte_brut(p[1])
        for m in CIVILITE.finditer(texte):
            avant = texte[max(0, m.start() - 80): m.start()]
            if ELU.search(avant) or ELU.search(texte[m.end(): m.end() + 15]):
                continue
            contexte = (avant[-50:] + " " + m[1] + " [X] " + texte[m.end(): m.end() + 40]).strip()
            cle = (_hote(p[0]), m[2].strip())
            if cle in vus:
                continue
            vus.add(cle)
            out.append({"hote": _hote(p[0]), "contexte": CIVILITE.sub(r"\1 [X] ", contexte),
                        "sujet_prive": bool(SUJETS_PRIVES.search(avant + texte[m.end(): m.end() + 40]))})
    return out


# --- Ligne de commande --------------------------------------------------------------------------------


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--cache", type=Path, required=True)
    a.add_argument("--sites", type=Path, default=ICI / "sites-communaux.csv")
    sous = a.add_subparsers(dest="cmd", required=True)
    g = sous.add_parser("get"); g.add_argument("urls", nargs="+")
    lo = sous.add_parser("lot"); lo.add_argument("fichier", type=Path)
    p = sous.add_parser("pdf"); p.add_argument("url")
    li = sous.add_parser("liens"); li.add_argument("url"); li.add_argument("motif", nargs="?", default="")
    t = sous.add_parser("texte"); t.add_argument("url"); t.add_argument("--max", type=int, default=6000)
    sous.add_parser("entites").add_argument("url")  # tableaux i-web : JSON dans l'attribut data-entities
    for n in ("1", "2", "3"):
        sous.add_parser("balayage-" + n)  # liste d'URL de la passe n (d'après le cache), à donner à `lot`
    sous.add_parser("classer")  # CSV : signaux et niveau estimé par commune, d'après le cache seul
    sous.add_parser("particuliers")  # civilité + nom hors contexte d'élu·e, noms masqués, sur tout le cache
    args = a.parse_args()

    if args.cmd == "particuliers":
        robot = Robot(args.cache, charger_sites(args.sites))
        urls = []
        for f in sorted((args.cache / "rep").glob("*.json")):
            r = json.loads(f.read_text())
            if r.get("statut") == 200 and "html" in r.get("entetes", {}).get("content-type", ""):
                urls.append(r["url"])
        w = csv.DictWriter(sys.stdout, fieldnames=["hote", "sujet_prive", "contexte"], lineterminator="\n")
        w.writeheader()
        w.writerows(particuliers(robot, urls))
        return

    if args.cmd == "balayage-1":
        print("\n".join(balayage_1(args.sites)))
        return
    if args.cmd in ("balayage-2", "balayage-3", "classer"):
        robot = Robot(args.cache, charger_sites(args.sites))
        if args.cmd == "classer":
            lignes = classer(robot, args.sites)
            w = csv.DictWriter(sys.stdout, fieldnames=list(lignes[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(lignes)
        else:
            f = balayage_2 if args.cmd == "balayage-2" else balayage_3
            print("\n".join(f(robot, args.sites)))
        return

    args.cache.mkdir(parents=True, exist_ok=True)
    if args.cmd in ("get", "lot", "pdf"):
        verrou = (args.cache / "verrou").open("w")
        fcntl.flock(verrou, fcntl.LOCK_EX)  # un seul processus à la fois : jamais deux requêtes en parallèle
    robot = Robot(args.cache, charger_sites(args.sites))

    def un(url: str, pdf: bool = False) -> None:
        try:
            r = robot.get(url, pdf=pdf)
            print(f"{r.get('statut') or r.get('erreur')}\t{r.get('entetes', {}).get('content-type', '')[:30]}\t"
                  f"{len(robot.corps(r['finale']))}o\t{r['finale']}" + (f"\t({r['non_lu']})" if r.get("non_lu") else ""),
                  flush=True)
            if pdf and "pdf" in r.get("entetes", {}).get("content-type", "").lower():
                dest = args.cache / "pdf" / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")
                dest.write_bytes(robot.corps(r["finale"]))
                print(json.dumps(couche_texte(dest), ensure_ascii=False))
        except Refus as e:
            print(f"REFUS\t{e}", flush=True)

    if args.cmd == "get":
        for u in args.urls:
            un(u)
    elif args.cmd == "lot":
        for u in [x.strip() for x in args.fichier.read_text().splitlines() if x.strip() and not x.startswith("#")]:
            un(u)
    elif args.cmd == "pdf":
        un(args.url, pdf=True)
    elif args.cmd in ("liens", "texte", "entites"):
        url = args.url.split("#")[0]
        rep = robot.en_cache(url)
        for _ in range(6):  # suit les redirections dans le cache seulement : aucune requête ici
            if rep is None:
                sys.exit("pas en cache : lancer d'abord `get`")
            lieu = rep.get("entetes", {}).get("location")
            if rep.get("statut") not in (301, 302, 303, 307, 308) or not lieu:
                break
            url = urljoin(url, lieu).split("#")[0]
            rep = robot.en_cache(url)
        rep["finale"] = url
        page = robot.decoder(rep)
        if args.cmd == "texte":
            print(texte_brut(page)[: args.max])
        elif args.cmd == "entites":
            for m in re.finditer(r'<table[^>]*\bid="([^"]*)"[^>]*data-entities="([^"]*)"', page):
                donnees = json.loads(html.unescape(m[2]))
                print(f"## {m[1]} : {len(donnees.get('data', []))} lignes")
                for ligne in donnees.get("data", []):
                    cellules = []
                    for k, v in ligne.items():
                        if k.endswith("-sort") or not isinstance(v, str):
                            continue
                        hrefs = re.findall(r'href="([^"]+)"', v)
                        cellules.append(f"{k}={texte_brut(v)}" + (f" <{' '.join(hrefs)}>" if hrefs else ""))
                    print(" | ".join(cellules))
        else:
            vus = set()
            for u, t in liens(page, url):
                if (u, t) in vus or (args.motif and not re.search(args.motif, u + " " + t, re.I)):
                    continue
                vus.add((u, t))
                print(f"{t[:90]}\t{u}")


if __name__ == "__main__":
    main()
