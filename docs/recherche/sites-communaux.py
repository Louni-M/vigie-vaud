"""Recensement des sites des communes vaudoises : plateforme, conseil, robots.txt (issue #118).

Deux étapes, séparées pour pouvoir affiner l'analyse sans refaire de requêtes :

    python3 docs/recherche/sites-communaux.py collecte --cache /chemin/cache
    python3 docs/recherche/sites-communaux.py analyse  --cache /chemin/cache > docs/recherche/sites-communaux.csv

`collecte` lit l'annuaire de l'UCV (site officiel et type de conseil de chaque commune), puis, pour chaque site,
`robots.txt` et la page d'accueil : deux requêtes par site, au plus une par seconde et par réseau /24 (ADR-0006).
Les réponses brutes restent dans le cache, hors du dépôt. `analyse` relit le cache et écrit le CSV.

Bibliothèque standard seulement (Python 3.11 ou plus).
"""

from __future__ import annotations

import argparse
import csv
import gzip
import html
import json
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
import urllib.robotparser
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

UA = "VigieVaud-recherche/0.1 (+https://github.com/Louni-M/vigie-vaud)"
UCV_LISTE = "https://www.ucv.ch/annuaire/recherche-par-localite"
RACINE = Path(__file__).resolve().parents[2]
COMMUNES = RACINE / "web" / "static" / "communes.json"
DELAI = 1.0  # secondes entre deux requêtes au même réseau /24

# Sites que l'annuaire de l'UCV ne donne pas ou donne faux, vérifiés à la main (n° OFS -> URL).
CORRECTIONS_SITE: dict[int, str] = {}

# Type de conseil : l'annuaire de l'UCV fait foi, sauf contradiction vérifiée à la main (n° OFS -> conseil, raison).
CORRECTIONS_CONSEIL: dict[int, tuple[str, str]] = {
    5905: ("conseil général", "UCV : « Conseil Communal : 69 » ; le site ne parle que du Conseil général"),
}


# --- HTTP poli ----------------------------------------------------------------------------------------

_derniere: dict[str, float] = defaultdict(float)
_verrous: dict[str, threading.Lock] = defaultdict(threading.Lock)
_verrou_global = threading.Lock()


_ips: dict[str, str] = {}


def _attendre(hote: str) -> None:
    """Le délai vaut par réseau /24, pas par nom d'hôte : une plateforme qui héberge des dizaines de communes sur
    quelques serveurs voisins les voit comme un seul site. i-web a coupé l'accès TCP de toute sa plage
    (195.65.10.0/24) pendant une demi-heure après une rafale à une requête par seconde et par nom d'hôte."""
    if hote not in _ips:
        try:
            _ips[hote] = socket.gethostbyname(hote).rsplit(".", 1)[0]
        except OSError:
            _ips[hote] = hote
    cle = _ips[hote]
    with _verrou_global:
        verrou = _verrous[cle]
    with verrou:
        reste = _derniere[cle] + DELAI - time.monotonic()
        if reste > 0:
            time.sleep(reste)
        _derniere[cle] = time.monotonic()


class _Redirection(urllib.request.HTTPRedirectHandler):
    """Chaque saut de redirection respecte aussi le délai par réseau."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _attendre(urlsplit(newurl).hostname or "")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_ouvreur = urllib.request.build_opener(_Redirection())


_sans_verification = urllib.request.build_opener(
    _Redirection(), urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))


def obtenir(url: str, timeout: float = 30) -> dict:
    """GET poli. Rend {url, statut, entetes, texte} ou {url, erreur}.

    Un certificat TLS invalide est noté (`tls_invalide`) et la page relue sans vérification : on ne fait que lire
    une page publique pour en tirer l'empreinte, et un certificat mal posé est en soi un fait du recensement."""
    _attendre(urlsplit(url).hostname or "")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip",
                                               "Accept-Language": "fr-CH,fr;q=0.9"})
    tls_invalide = None
    for ouvreur in (_ouvreur, _sans_verification):
        try:
            with ouvreur.open(req, timeout=timeout) as r:
                corps, statut, entetes, finale = r.read(3_000_000), r.status, dict(r.headers), r.geturl()
            break
        except urllib.error.HTTPError as e:
            corps, statut, entetes, finale = e.read(3_000_000), e.code, dict(e.headers or {}), e.geturl() or url
            break
        except Exception as e:  # DNS, TLS, délai…
            if "CERTIFICATE_VERIFY_FAILED" in str(e) and tls_invalide is None:
                tls_invalide = str(e)
                _attendre(urlsplit(url).hostname or "")
                continue
            return {"url": url, "erreur": f"{type(e).__name__}: {e}", "tls_invalide": tls_invalide}
    entetes = {k.lower(): v for k, v in entetes.items()}  # certains serveurs écrivent leurs en-têtes en minuscules
    if entetes.get("content-encoding", "").lower() == "gzip" or corps[:2] == b"\x1f\x8b":
        try:
            corps = gzip.decompress(corps)
        except OSError:
            pass
    return {"url": url, "finale": finale, "statut": statut, "entetes": entetes, "texte": _decoder(corps, entetes),
            "tls_invalide": tls_invalide}


def _decoder(corps: bytes, entetes: dict) -> str:
    m = re.search(r"charset=([\w-]+)", entetes.get("content-type", ""), re.I) or \
        re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", corps[:4000], re.I)
    enc = m[1].decode() if m and isinstance(m[1], bytes) else (m[1] if m else "utf-8")
    try:
        return corps.decode(enc, errors="replace")
    except LookupError:
        return corps.decode("utf-8", errors="replace")


# --- Collecte -----------------------------------------------------------------------------------------


def _texte(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def fiche_ucv(page: str) -> dict:
    nom = _texte(re.search(r"<h1>(.*?)</h1>", page, re.S)[1])
    ofs = int(re.search(r"No OFS:\s*</div>\s*</div>\s*<div[^>]*>\s*(\d+)", page)[1])
    bloc = re.search(r'<div class="col-md-4 col-sm-4 col-xs-6">(.*?)<div class="col-md-5', page, re.S)[1]
    site = next((h for h in re.findall(r'href="(https?://[^"]+)"', bloc)), None)
    texte = _texte(page)
    conseil = re.search(r"Conseil (Général|Communal)\s*:\s*(\d*)", texte, re.I)
    return {
        "nom": nom, "ofs": ofs, "site": site,
        "conseil": f"conseil {conseil[1].lower()}" if conseil else "",
        "membres": int(conseil[2]) if conseil and conseil[2] else None,
    }


def _a_refaire(ancien: dict) -> bool:
    """Un site en échec, ou lu avec une version du script qui ne décompressait pas tout (texte illisible)."""
    return any("erreur" in r or r.get("texte", "").count("\ufffd") > 50 for r in (ancien["accueil"], ancien["robots"]))


def collecte(cache: Path, relancer: bool = False, paralleles: int = 8, timeout: float = 30) -> None:
    """Remplit le cache. `relancer` refait les sites en échec (délai, TLS…) ; les autres restent tels quels."""
    (cache / "ucv").mkdir(parents=True, exist_ok=True)
    (cache / "sites").mkdir(parents=True, exist_ok=True)
    liste = obtenir(UCV_LISTE, timeout=120)
    liens = list(dict.fromkeys(re.findall(r'href="(/annuaire/recherche-par-localite/commune/[^"]+)"', liste["texte"])))
    print(f"UCV : {len(liens)} communes", file=sys.stderr)
    fiches = []
    for lien in liens:
        chemin = cache / "ucv" / (re.sub(r"[^\w-]+", "_", unquote(lien.rsplit("/", 1)[1])) + ".html")
        if not chemin.exists():
            r = obtenir(urljoin(UCV_LISTE, lien), timeout=120)
            if "texte" not in r or r["statut"] != 200:
                print(f"UCV : échec {lien} {r.get('erreur') or r.get('statut')}", file=sys.stderr)
                continue
            chemin.write_text(r["texte"], encoding="utf-8")
        fiches.append(fiche_ucv(chemin.read_text(encoding="utf-8")))
    (cache / "ucv.json").write_text(json.dumps(fiches, ensure_ascii=False, indent=1), encoding="utf-8")

    def un_site(f: dict) -> None:
        sortie = cache / "sites" / f"{f['ofs']}.json"
        if sortie.exists():
            ancien = json.loads(sortie.read_text(encoding="utf-8"))
            if not (relancer and _a_refaire(ancien)):
                return
        site = CORRECTIONS_SITE.get(f["ofs"]) or f["site"]
        if not site:
            return
        p = urlsplit(site)
        robots = obtenir(f"{p.scheme}://{p.netloc}/robots.txt", timeout)
        accueil = obtenir(site, timeout)
        sortie.write_text(json.dumps({
            "ofs": f["ofs"], "site": site, "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "robots": robots, "accueil": accueil}, ensure_ascii=False), encoding="utf-8")
        print(f"{f['ofs']} {site} {accueil.get('statut') or accueil.get('erreur')}", file=sys.stderr)

    # Plusieurs hôtes en parallèle ; le délai par réseau /24 est tenu par obtenir().
    with ThreadPoolExecutor(max_workers=paralleles) as pool:
        list(pool.map(un_site, fiches))


# --- Analyse ------------------------------------------------------------------------------------------

# Plateformes communales : un produit vendu à plusieurs communes, avec la même structure de pages d'un site à
# l'autre (un scraper par plateforme). Ordre = priorité ; motif cherché dans les en-têtes et la page d'accueil.
PLATEFORMES: list[tuple[str, str, str]] = [
    ("i-web", "Innovative Web AG (Wilen b. Wollerau)", r"stats\.i-web\.ch|class=\"icms-|i-web\.ch"),
    ("Quicksite", "eAdmin Solutions SA (Bussigny)", r"CMS - Quicksite|eadmin-solutions\.ch|lngStatQSSession"),
    ("WebForge", "WebForge (Lausanne)", r"content='WebForge|webforge\.ch"),
    ("COMMUNEapp WEB", "Commune Agence", r"/front/agencedudev/"),
    ("Webcommunes", "WNG agence digitale (Lausanne)", r"Webcommunes"),
    ("imedia Communes", "imedia.ch (Lausanne)", r"/templates/(orion|tx_next|admairiev2)/"),
    ("OIOI web", "OFISA Informatique", r"web-prod\.o-i\.ch|ch\.OI\.OFISA"),
    ("Hekl@", "Designis", r"Hekl@|hekla\.ch"),
]
# Réseau d'i-web (RIPE : IWB-NET, Innovative Web AG) : sert à attribuer les sites qui nous ont coupé l'accès.
RESEAU_IWEB = "195.65.10."

# CMS génériques et constructeurs de sites : (nom, motif, type).
CMS: list[tuple[str, str, str]] = [
    ("WordPress", r"/wp-content/|/wp-includes/|content=\"WordPress", "CMS générique"),
    ("TYPO3", r"/typo3conf/|/typo3temp/|TYPO3 CMS|/_assets/[0-9a-f]{32}/", "CMS générique"),
    ("Drupal", r"content=\"Drupal|drupal-settings-json|/sites/default/files/", "CMS générique"),
    ("Joomla", r"/media/jui/|/components/com_|content=\"Joomla|/media/templates/site/|/media/gantry5/|"
               r"/templates/[\w-]+/(css|js|images|custom|assets|fonts)/", "CMS générique"),
    ("October CMS", r"october_session", "CMS générique"),
    ("Craft CMS", r"x-powered-by: Craft CMS|/cpresources/", "CMS générique"),
    ("Umbraco", r"/umbraco/|umbraco", "CMS générique"),
    ("Magnolia", r"/\.resources/|magnolia", "CMS générique"),
    ("Odoo", r"content=\"Odoo", "CMS générique"),
    ("Contao", r"content=\"Contao|/assets/contao/", "CMS générique"),
    ("Lochness CMS", r"Lochness CMS", "CMS générique"),
    ("Obtic City2Net", r"Obtic City2Net", "CMS générique"),
    ("Yabrab", r"cdn\.yabrab\.ch", "CMS générique"),
    ("Wix", r"Wix\.com Website Builder|wixstatic\.com|routage sur WIX", "constructeur de site"),
    ("Infomaniak Site Creator", r"Infomaniak Site Creator", "constructeur de site"),
    ("Google Sites", r"server: ESF|sites\.google\.com|www\.gstatic\.com/_/atari", "constructeur de site"),
    ("Weebly", r"weebly", "constructeur de site"),
    ("Mobirise", r"content=\"Mobirise", "constructeur de site"),
    ("Squarespace", r"static1\.squarespace\.com", "constructeur de site"),
    ("Hostpoint", r"hosting-page-builder", "constructeur de site"),
    ("Gatsby", r"content=\"Gatsby", "code propre"),
    ("Nuxt", r"/_nuxt/", "code propre"),
    ("Symfony (Webpack Encore)", r"/build/runtime\.[0-9a-f]+\.js", "code propre"),
]

# Noms des prestataires repérés par le domaine de leur lien de pied de page.
PRESTATAIRES = {
    "wng.ch": "WNG agence digitale", "webcommunes.ch": "WNG agence digitale", "imedia.ch": "imedia.ch",
    "eadmin-solutions.ch": "eAdmin Solutions SA", "quicksite.ch": "eAdmin Solutions SA", "webforge.ch": "WebForge",
    "communeagence.ch": "Commune Agence", "designis.ch": "Designis", "hekla.ch": "Designis",
    "nashdesign.ch": "Nash design", "troisdeuxun.ch": "troisdeuxun", "cobalt-it.ch": "Cobalt IT",
    "webpixel.ch": "WebPixel", "lemansites.ch": "LemanSites", "graphi-cite.ch": "Graphi-Cité",
    "artisan-du-web.ch": "Artisan du Web", "inetis.ch": "inetis", "trisinformatique.com": "Tris Informatique",
    "boomerang.ch": "Boomerang", "hawaii.do": "Hawaii Interactive",
}
# Formule de crédit dans le texte qui précède le lien, ou dans les attributs du lien lui-même.
CREDIT = re.compile(r"r[ée]alis[ée]e? (par|avec)|r[ée]alisation|cr[ée]ation|cr[ée]é (avec .{0,3} )?par|"
                    r"conception|design(ed)? (and developed )?(by|par)|webdesign|design ?:|d[ée]veloppement ?:|"
                    r"powered|propuls|d[ée]velopp[ée] (et h[ée]berg[ée] )?(en suisse )?par|webmaster|made (with|by)|"
                    r"site (web|internet) par|agence web", re.I)
ATTRIBUT = re.compile(r"copyright|powered|cr[ée]dit|r[ée]alis", re.I)
HORS_CREDIT = re.compile(r"facebook|instagram|twitter|linkedin|youtube|google|x\.com|vd\.ch|admin\.ch|apple|tiktok|"
                         r"whatsapp|maps|swisstopo|meteo|cookie|sbb|cff|vimeo|w3\.org|openstreetmap|bsky|mastodon|"
                         r"wordpress\.org|communeapp\.ch|ucv\.ch|localcities|tourisme|energiestadt|citedelenergie|"
                         r"^ch\.ch$|easyvote|infomaniak\.com|tapni\.com", re.I)
LIEN = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S | re.I)


def _base(hote: str) -> str:
    return ".".join(hote.lower().split(".")[-2:])


def prestataire(texte: str, hote: str) -> str:
    """Le prestataire cité en pied de page (« réalisé par… », « powered by… »), d'après le domaine du lien."""
    queue = texte[int(len(texte) * 0.6):]
    for m in LIEN.finditer(queue):
        h = re.search(r"href\s*=\s*[\"'](https?://[^\"']+)", m[1])
        if not h:
            continue
        domaine = _base(urlsplit(html.unescape(h[1])).hostname or "")
        if not domaine or domaine == _base(hote) or HORS_CREDIT.search(domaine):
            continue
        avant = queue[max(0, m.start() - 300):m.start()]
        attributs = " ".join(re.findall(r"(?:title|alt)=[\"']([^\"']*)", m[0]))
        texte_lien = _texte(avant)[-60:] + " " + _texte(m[2]) + " " + attributs
        if domaine in PRESTATAIRES or CREDIT.search(texte_lien) or ATTRIBUT.search(m[1] + avant[-120:]):
            return PRESTATAIRES.get(domaine, domaine)
    m = re.search(r"(?:site (?:internet |web )?(?:r[ée]alis[ée]|cr[ée][ée]|d[ée]velopp[ée])|"
                  r"r[ée]alisation(?: du site)?|conception|cr[ée]ation(?: du site)?(?: internet| web)?|made with love)"
                  r"\s*(?:avec \S+ )?(?:par|by|:)?\s*([A-Z][\w.-]+(?: [A-Z][\w-]+)?)", _texte(queue[-8000:]))
    return m[1] if m else ""


def page_conseil(texte: str, base: str) -> tuple[str, str]:
    """Le meilleur lien de la page d'accueil vers la page du conseil, et ce qu'il nomme (communal ou général)."""
    meilleur: tuple[int, str, str] | None = None
    for m in LIEN.finditer(texte):
        h = re.search(r"href\s*=\s*[\"']([^\"'#]+)", m[1])
        if not h or h[1].lower().startswith(("mailto:", "tel:", "javascript:")) or ".pdf" in h[1].lower():
            continue
        href, libelle = html.unescape(h[1]).strip(), _texte(m[2])
        if re.fullmatch(r"(le )?conseils? (communal|g[ée]n[ée]ral)", libelle, re.I):
            score = 3
        elif re.search(r"conseils? (communal|g[ée]n[ée]ral)", libelle, re.I):
            score = 2
        elif re.search(r"conseil[-_ ]?(communal|g(e|%C3%A9|é)n(e|%C3%A9|é)ral)", href, re.I):
            score = 1
        else:
            continue
        if not meilleur or score > meilleur[0]:
            meilleur = (score, urljoin(base, href), libelle + " " + href)
    if not meilleur:
        return "", ""
    nom = re.search(r"conseil[-_ ]?(communal|g(?:e|%C3%A9|é)n(?:e|%C3%A9|é)ral)", meilleur[2], re.I)
    genre = "" if not nom else ("conseil communal" if nom[1].lower() == "communal" else "conseil général")
    return meilleur[1], genre


def lire_robots(r: dict, url: str) -> tuple[str, str, str]:
    """(état du robots.txt, sort de l'URL donnée, crawl-delay)."""
    texte = r.get("texte") or ""
    if "erreur" in r:
        return "injoignable", "", ""
    if r.get("statut") != 200 or re.search(r"<html|<!doctype", texte[:500], re.I):
        return "absent", "autorisée" if url else "", ""
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(texte.splitlines())
    racine = urlsplit(url or r["url"])
    tout_interdit = not rp.can_fetch(UA, f"{racine.scheme}://{racine.netloc}/")
    regles = [ligne for ligne in texte.splitlines() if re.match(r"\s*disallow\s*:\s*\S", ligne, re.I)]
    etat = "interdit tout" if tout_interdit else ("restrictions" if regles else "sans restriction")
    delai = rp.crawl_delay(UA)
    return etat, ("autorisée" if rp.can_fetch(UA, url) else "interdite") if url else "", str(delai or "")


def classer(accueil: dict, ip: str) -> dict:
    texte = accueil.get("texte") or ""
    entetes = "\n".join(f"{k}: {v}" for k, v in (accueil.get("entetes") or {}).items())
    tout = entetes + "\n" + texte
    hote = urlsplit(accueil.get("finale") or accueil["url"]).hostname or ""
    gens = re.findall(r"<meta[^>]+name=[\"']generator[\"'][^>]*content=[\"']([^\"']+)", texte, re.I)
    res = {"plateforme": "", "type": "", "cms": "", "prestataire": prestataire(texte, hote), "indices": ""}
    for nom, presta, motif in PLATEFORMES:
        if m := re.search(motif, tout, re.I):
            res.update(plateforme=nom, type="plateforme communale", prestataire=presta, indices=m[0][:60])
            break
    else:
        if "texte" not in accueil and ip.startswith(RESEAU_IWEB):
            res.update(plateforme="i-web", type="plateforme communale", prestataire=PLATEFORMES[0][1],
                       indices=f"adresse IP {ip} (IWB-NET) ; accès coupé")
            return res
    for nom, motif, genre in CMS:
        if m := re.search(motif, tout, re.I):
            res["cms"] = nom
            if not res["type"]:
                res.update(type=genre, indices=m[0][:60])
            break
    if res["plateforme"] in ("Webcommunes", "imedia Communes"):
        res["cms"] = "TYPO3" if res["plateforme"] == "Webcommunes" else "Joomla"
    if not res["type"]:
        if "texte" not in accueil or (accueil.get("statut") or 0) >= 400:
            res["type"] = "injoignable"
            res["indices"] = (accueil.get("erreur") or f"HTTP {accueil.get('statut')}")[:80]
        elif res["prestataire"]:
            res.update(type="code propre", indices="pas de CMS reconnu ; prestataire en pied de page")
        else:
            res.update(type="non identifié", indices="; ".join(gens)[:60])
    if not res["plateforme"]:
        res["plateforme"] = res["cms"] or ("sur mesure" if res["type"] == "code propre" else res["type"])
    return res


COLONNES = ["ofs", "commune", "habitants", "conseil", "membres", "conseil_ucv", "conseil_selon_site", "site",
            "url_finale", "ip", "plateforme", "type", "cms", "prestataire", "indices", "page_conseil", "robots",
            "robots_page_conseil", "crawl_delay", "tls_invalide", "date"]


def analyse(cache: Path, sortie) -> None:
    habitants = {c["bfs"]: c["habitants"] for c in json.loads(COMMUNES.read_text(encoding="utf-8"))}
    fiches = json.loads((cache / "ucv.json").read_text(encoding="utf-8"))
    w = csv.DictWriter(sortie, COLONNES, lineterminator="\n")
    w.writeheader()
    for f in sorted(fiches, key=lambda f: f["ofs"]):
        d = json.loads((cache / "sites" / f"{f['ofs']}.json").read_text(encoding="utf-8"))
        a, r = d["accueil"], d["robots"]
        hote = urlsplit(a.get("finale") or d["site"]).hostname or ""
        try:
            ip = socket.gethostbyname(hote)
        except OSError:
            ip = ""
        c = classer(a, ip)
        page, genre = page_conseil(a.get("texte") or "", a.get("finale") or d["site"])
        etat, sort, delai = lire_robots(r, page)
        conseil = CORRECTIONS_CONSEIL.get(f["ofs"], (f["conseil"], ""))[0]
        w.writerow({
            "ofs": f["ofs"], "commune": f["nom"], "habitants": habitants.get(f["ofs"], ""), "conseil": conseil,
            "conseil_ucv": f["conseil"],
            "membres": f["membres"] or "", "conseil_selon_site": genre, "site": d["site"],
            "url_finale": a.get("finale", ""), "ip": ip, **c, "page_conseil": page, "robots": etat,
            "robots_page_conseil": sort, "crawl_delay": delai,
            "tls_invalide": "oui" if (a.get("tls_invalide") or r.get("tls_invalide")) else "",
            "date": d["date"][:10],
        })


def main() -> None:
    global DELAI
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("etape", choices=["collecte", "analyse"])
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--relancer", action="store_true", help="refaire les sites en échec")
    ap.add_argument("--paralleles", type=int, default=8, help="hôtes lus en même temps")
    ap.add_argument("--delai", type=float, default=DELAI, help="secondes entre deux requêtes au même réseau /24")
    ap.add_argument("--timeout", type=float, default=30)
    a = ap.parse_args()
    DELAI = a.delai
    if a.etape == "collecte":
        collecte(a.cache, a.relancer, a.paralleles, a.timeout)
    else:
        analyse(a.cache, sys.stdout)


if __name__ == "__main__":
    main()
