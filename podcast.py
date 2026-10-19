#!/usr/bin/env python3
"""
Actualiza los episodios del podcast a partir de Spotify for Creators y YouTube.

Lee los dos feeds, une cada episodio de Spotify con su vídeo de YouTube
(por título, número de episodio y fecha) y guarda el resultado en
contenido/podcast/episodios.json. Ese archivo es el que usa construir.py.

Uso:
  python3 podcast.py                                   # descarga los feeds (GitHub Actions)
  python3 podcast.py --spotify a.xml --youtube b.xml   # con archivos ya descargados

Para ocultar un episodio de la web: pon "oculto": true en su entrada del JSON.
Las entradas existentes nunca se borran: si un episodio desaparece de un feed, se queda.
"""
import argparse
import datetime as dt
import difflib
import html
import json
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent
ALMACEN = RAIZ / "contenido" / "podcast" / "episodios.json"
NAVEGADOR = {"User-Agent": "Mozilla/5.0 (compatible; BolaPadelWeb/1.0; +https://bolapadel.es)"}
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
}
# A partir de aquí la descripción es publicidad o enlaces repetidos: se corta.
CORTES = [
    "usa el código", "sa el código bolapadel", "🔗", "sigue a bola pádel", "sigue a los colaboradores",
    "por cierto… antes de arrancar", "por cierto... antes de arrancar", "🎾 más noticias", "más noticias en",
    "🎾 suscríbete", "¡no olvides suscribirte", "#premierpadel", "#padel", "🎧 escúchalo", "si te gusta, suscríbete",
]
MIN_EPISODIO = 20  # minutos: lo que dura menos es un clip, no un episodio


# ------------------------------------------------------------------ texto
def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def slug(t):
    t = re.sub(r"[^a-z0-9]+", "-", sin_tildes(t).lower()).strip("-")
    return t[:80].rstrip("-") or "episodio"


def numero_episodio(t):
    s = sin_tildes(t).lower()
    m = (re.search(r"#\s*(\d+)", s) or re.search(r"episodio\s*#?\s*(\d+)", s)
         or re.search(r"(\d+)\s*[ºª°o]?\s*episodio", s))
    return int(m.group(1)) if m else None


def titulo_limpio(t):
    t = re.sub(r"\s*\|\s*bola p[aá]del podcast\s*$", "", t.strip(), flags=re.I)
    t = re.sub(r"^\s*bola p[aá]del podcast\s*\|\s*", "", t, flags=re.I)
    t = t.strip().rstrip(".").strip()
    n = numero_episodio(t)
    if n is not None and len(re.sub(r"(?i)bola p[aá]del|podcast|episodio|#|\d+|[ºª°]", "", t).strip()) < 4:
        return f"Episodio {n}"
    return t


def clave(t):
    n = numero_episodio(t)
    if n is not None and titulo_limpio(t).startswith("Episodio "):
        return f"episodio {n}"
    s = sin_tildes(titulo_limpio(t)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def trocear(p, maximo=320):
    """Parte un párrafo muy largo en varios, siempre por el final de una frase."""
    if len(p) <= maximo:
        return [p]
    frases = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])", p)
    trozos, actual = [], ""
    for f in frases:
        if actual and len(actual) + len(f) > maximo:
            trozos.append(actual)
            actual = f
        else:
            actual = f"{actual} {f}".strip()
    if actual:
        trozos.append(actual)
    return trozos


def parrafos(desc, es_html=True):
    """Convierte la descripción en párrafos limpios, sin la parte de publicidad."""
    if es_html:
        desc = re.sub(r"(?i)<br\s*/?>|</p>|</li>", "\n", desc)
        desc = re.sub(r"<[^>]+>", "", desc)
    desc = html.unescape(desc)
    baja = desc.lower()
    corte = min([i for i in (baja.find(c) for c in CORTES) if i >= 0] or [len(desc)])
    desc = desc[:corte]
    # frases pegadas sin espacio: "deporte.Marina" -> "deporte. Marina"; "también:El" -> "también: El"
    desc = re.sub(r"([.!?])(?=[A-ZÁÉÍÓÚÑ¿¡])", r"\1 ", desc)
    desc = re.sub(r"(?<!http)(?<!https):(?=[A-Za-zÁÉÍÓÚÑ¿¡])", ": ", desc)
    salida = []
    for p in desc.split("\n"):
        p = re.sub(r"\s+", " ", p).strip()
        if not p or p.startswith("#") or not re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", p):
            continue
        salida.extend(trocear(p))
    if salida and salida[-1].endswith(":"):
        salida[-1] = re.sub(r"[^.!?]*:$", "", salida[-1]).strip()
        if not salida[-1]:
            salida.pop()
    return salida


# ------------------------------------------------------------------ feeds
def descargar(url):
    req = urllib.request.Request(url, headers=NAVEGADOR)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def leer_spotify(xml):
    raiz = ET.fromstring(xml)
    episodios = []
    for it in raiz.iter("item"):
        g = lambda t: (it.findtext(t, default="", namespaces=NS) or "").strip()  # noqa: E731
        dur = g("itunes:duration")
        partes = [int(x) for x in dur.split(":")] if re.fullmatch(r"[\d:]+", dur or "") else []
        segundos = sum(v * 60 ** i for i, v in enumerate(reversed(partes))) if partes else None
        enc = it.find("enclosure")
        episodios.append({
            "guid": g("guid"),
            "titulo_original": g("title"),
            "fecha": parsedate_to_datetime(g("pubDate")).date().isoformat(),
            "duracion_min": round(segundos / 60) if segundos else None,
            "texto": parrafos(g("description")),
            "audio": enc.get("url") if enc is not None else "",
            "spotify": g("link"),
        })
    return episodios


def leer_youtube(xml):
    raiz = ET.fromstring(xml)
    videos = []
    for e in raiz.findall("atom:entry", NS):
        videos.append({
            "youtube": e.findtext("yt:videoId", namespaces=NS),
            "titulo_original": e.findtext("atom:title", namespaces=NS) or "",
            "fecha": (e.findtext("atom:published", namespaces=NS) or "")[:10],
            "texto": parrafos(e.findtext("media:group/media:description", default="", namespaces=NS) or "", es_html=False),
        })
    return videos


def duracion_youtube(video_id):
    """Minutos del vídeo, leídos de su página. None si no se puede saber."""
    try:
        pagina = descargar(f"https://www.youtube.com/watch?v={video_id}&hl=es")
        m = re.search(r'"lengthSeconds":"(\d+)"', pagina)
        return round(int(m.group(1)) / 60) if m else None
    except Exception:
        return None


# ------------------------------------------------------------------ unión
def dias_entre(a, b):
    try:
        return abs((dt.date.fromisoformat(a) - dt.date.fromisoformat(b)).days)
    except (TypeError, ValueError):
        return 0


def buscar(episodios, item, campo_libre):
    """Busca un episodio existente que sea el mismo que 'item' y aún no tenga 'campo_libre'."""
    k = clave(item["titulo_original"])
    mejor, nota = None, 0.0
    for ep in episodios:
        if ep.get(campo_libre):
            continue
        k2 = clave(ep["titulo_original"])
        r = 1.0 if k == k2 else difflib.SequenceMatcher(None, k, k2).ratio()
        if r >= 0.8 and dias_entre(ep.get("fecha"), item.get("fecha")) <= 10 and r > nota:
            mejor, nota = ep, r
    return mejor


def id_unico(base, usados):
    i, nuevo = 2, base
    while nuevo in usados:
        nuevo, i = f"{base}-{i}", i + 1
    return nuevo


def fusionar(episodios, spotify, youtube, comprobar_duracion=True):
    por_guid = {e["guid"]: e for e in episodios if e.get("guid")}
    por_video = {e["youtube"]: e for e in episodios if e.get("youtube")}
    usados = {e["id"] for e in episodios}
    nuevos = 0

    for s in spotify:
        ep = por_guid.get(s["guid"]) or buscar(episodios, s, "guid")
        if ep is None:
            ep = {"id": id_unico(slug(titulo_limpio(s["titulo_original"])), usados), "youtube": "", "oculto": False}
            usados.add(ep["id"])
            episodios.append(ep)
            nuevos += 1
        ep.update({k: s[k] for k in ("guid", "audio", "spotify")})
        ep["titulo_original"] = s["titulo_original"]
        ep["titulo"] = titulo_limpio(s["titulo_original"])
        ep["fecha"] = min(filter(None, [ep.get("fecha"), s["fecha"]]))
        ep["duracion_min"] = s["duracion_min"] or ep.get("duracion_min")
        if s["texto"]:
            ep["texto"] = s["texto"]
        por_guid[s["guid"]] = ep

    for v in youtube:
        if v["youtube"] in por_video:
            continue
        ep = buscar(episodios, v, "youtube")
        if ep is None:
            minutos = duracion_youtube(v["youtube"]) if comprobar_duracion else v.get("duracion_min")
            if minutos is None or minutos < MIN_EPISODIO:
                continue  # clip o short: no es un episodio
            ep = {"id": id_unico(slug(titulo_limpio(v["titulo_original"])), usados), "guid": "", "audio": "",
                  "spotify": "", "oculto": False, "titulo_original": v["titulo_original"],
                  "titulo": titulo_limpio(v["titulo_original"]), "fecha": v["fecha"], "duracion_min": minutos,
                  "texto": v["texto"]}
            usados.add(ep["id"])
            episodios.append(ep)
            nuevos += 1
        ep["youtube"] = v["youtube"]
        if len(v["texto"]) > len(ep.get("texto") or []):  # YouTube suele tener mejor los saltos de párrafo
            ep["texto"] = v["texto"]
        if not ep.get("fecha"):
            ep["fecha"] = v["fecha"]
        por_video[v["youtube"]] = ep

    episodios.sort(key=lambda e: e.get("fecha") or "", reverse=True)
    return nuevos


def main():
    p = argparse.ArgumentParser(description="Actualiza los episodios del podcast")
    p.add_argument("--spotify", help="archivo RSS de Spotify for Creators ya descargado")
    p.add_argument("--youtube", help="archivo RSS de YouTube ya descargado")
    p.add_argument("--sin-duracion", action="store_true", help="no consultar YouTube para saber la duración")
    a = p.parse_args()

    conf = yaml.safe_load((RAIZ / "sitio.yml").read_text(encoding="utf-8"))["podcast"]
    episodios = json.loads(ALMACEN.read_text(encoding="utf-8")) if ALMACEN.exists() else []

    try:
        xml_s = Path(a.spotify).read_text(encoding="utf-8") if a.spotify else descargar(conf["rss_spotify"])
        spotify = leer_spotify(xml_s)
    except Exception as e:  # un feed caído no debe romper la web
        print("AVISO: no se pudo leer Spotify:", e, file=sys.stderr)
        spotify = []
    try:
        url_yt = f"https://www.youtube.com/feeds/videos.xml?channel_id={conf['youtube_canal_id']}"
        xml_y = Path(a.youtube).read_text(encoding="utf-8") if a.youtube else descargar(url_yt)
        youtube = leer_youtube(xml_y)
    except Exception as e:
        print("AVISO: no se pudo leer YouTube:", e, file=sys.stderr)
        youtube = []

    nuevos = fusionar(episodios, spotify, youtube, comprobar_duracion=not a.sin_duracion)
    ALMACEN.parent.mkdir(parents=True, exist_ok=True)
    ALMACEN.write_text(json.dumps(episodios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Podcast: {len(episodios)} episodios ({nuevos} nuevos) · Spotify {len(spotify)} · YouTube {len(youtube)}")


if __name__ == "__main__":
    main()
