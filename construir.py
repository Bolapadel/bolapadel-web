#!/usr/bin/env python3
"""
Construye la web estática de Bola Pádel.

Lee:   sitio.yml + contenido/noticias/*.yml
Crea:  docs/  (la carpeta que publica GitHub Pages)

Uso:
  python3 construir.py              # web final, con URLs limpias
  python3 construir.py --preview    # vista previa (enlaces a index.html, aviso de prueba)
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import sys
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

try:
    from zoneinfo import ZoneInfo
    ZONA = ZoneInfo("Europe/Madrid")
except Exception:  # sin base de datos de zonas horarias: se calcula a mano (ver momento_publicacion)
    ZONA = None

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "docs"

SECCIONES = {
    "actualidad": {"es": ("actualidad", "Actualidad"), "en": ("news", "News")},
    "opinion": {"es": ("opinion", "Opinión"), "en": ("opinion", "Opinion")},
    "podcast": {"es": ("podcast", "Podcast"), "en": ("podcast", "Podcast")},
}
IDIOMAS = ("es", "en")
PREFIJO = {"es": "", "en": "en/"}

MESES = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}

TEXTOS = {
    "es": {
        "portada": "Portada", "newsletter": "Newsletter", "suscribete": "Suscríbete",
        "lo_ultimo": "Lo último", "por": "Por", "min_lectura": "min de lectura",
        "compartir": "Compartir", "copiar": "Copiar enlace", "copiado": "Enlace copiado",
        "sigue_leyendo": "Sigue leyendo", "ver_todo": "Ver todo",
        "tu_correo": "Tu correo electrónico", "apuntarme": "Apuntarme",
        "nl_titulo": "La newsletter de Bola Pádel",
        "nl_aviso_preview": "Vista previa: aquí irá conectado tu formulario de MailerLite.",
        "nl_pendiente": "Muy pronto podrás suscribirte desde aquí.",
        "pod_titulo": "Bola Pádel Podcast", "pod_ver": "Ver episodios",
        "pod_vacio": "Los episodios aparecerán aquí en cuanto se publiquen.",
        "seccion_vacia": "Todavía no hay nada publicado en esta sección.",
        "preview": "Vista previa · Noticias de prueba con datos reales del circuito. Nada de esto es público todavía.",
        "idioma_otro": "English", "idioma_otro_corto": "EN",
        "etiquetas": "Temas", "volver": "Volver a la portada",
        "no_encontrada_t": "Esta bola se ha ido fuera de la pista",
        "no_encontrada_p": "La página que buscas no existe o ha cambiado de sitio.",
        "derechos": "Todos los derechos reservados.",
        "secciones_desc": {
            "actualidad": "Lo que pasa en el circuito profesional, contado claro.",
            "opinion": "Opinión firmada. Con nombre y apellido.",
            "podcast": None,
        },
        "foto": "Foto", "leer_columna": "Leer la columna", "menu": "Secciones",
        "nl_baja": "Gratis. Te das de baja cuando quieras, con un clic.",
        "nl_ok": "¡Dentro! Ya estás en la lista. Si te llega un correo para confirmar, ábrelo y listo.",
        "nl_error": "No se ha podido completar. Revisa el correo y vuelve a intentarlo en un momento.",
        "nl_enviando": "Apuntando…",
        "nl_legal": "Te llegará un email a la semana con información y opinión.",
        "episodio": "Episodio", "ver_video": "Ver el episodio", "solo_audio": "Solo audio",
        "aviso_youtube": "Al pulsar se carga el reproductor de YouTube.",
        "escuchalo_en": "Escúchalo en", "mas_episodios": "Más episodios", "ultimo_episodio": "Último episodio",
        "todos_episodios": "Todos los episodios", "en_espanol": "", "minutos": "min",
        "publicidad": "Publicidad",
        "codigos_eti": "Colaboración comercial", "codigos_titulo": "Códigos de descuento",
        "codigos_texto": "Ahorra en tus compras de pádel con nuestros colaboradores. Copia el código y úsalo al pagar.",
        "codigos_dto": "de descuento", "copiar_codigo": "Copiar", "codigo_copiado": "Copiado",
    },
    "en": {
        "portada": "Home", "newsletter": "Newsletter", "suscribete": "Subscribe",
        "lo_ultimo": "Latest", "por": "By", "min_lectura": "min read",
        "compartir": "Share", "copiar": "Copy link", "copiado": "Link copied",
        "sigue_leyendo": "Keep reading", "ver_todo": "See all",
        "tu_correo": "Your email address", "apuntarme": "Sign me up",
        "nl_titulo": "The Bola Pádel newsletter",
        "nl_aviso_preview": "Preview: your MailerLite form will be connected here.",
        "nl_pendiente": "You'll be able to subscribe here very soon.",
        "pod_titulo": "Bola Pádel Podcast", "pod_ver": "See episodes",
        "pod_vacio": "Episodes will show up here as soon as they're published.",
        "seccion_vacia": "Nothing published in this section yet.",
        "preview": "Preview · Sample stories built on real tour data. None of this is public yet.",
        "idioma_otro": "Español", "idioma_otro_corto": "ES",
        "etiquetas": "Topics", "volver": "Back to the home page",
        "no_encontrada_t": "That ball went out of the court",
        "no_encontrada_p": "The page you're looking for doesn't exist or has moved.",
        "derechos": "All rights reserved.",
        "secciones_desc": {
            "actualidad": "What happens on the pro tour, told clearly.",
            "opinion": "Signed opinion. Full name included.",
            "podcast": None,
        },
        "foto": "Photo", "leer_columna": "Read the column", "menu": "Sections",
        "nl_baja": "Free. Unsubscribe any time, in one click.",
        "nl_ok": "You're in! If you get a confirmation email, open it and you're done.",
        "nl_error": "Something went wrong. Check your email address and try again in a moment.",
        "nl_enviando": "Signing up…",
        "nl_legal": "One email a week with news and opinion.",
        "episodio": "Episode", "ver_video": "Watch the episode", "solo_audio": "Audio only",
        "aviso_youtube": "Clicking loads the YouTube player.",
        "escuchalo_en": "Listen on", "mas_episodios": "More episodes", "ultimo_episodio": "Latest episode",
        "todos_episodios": "All episodes", "en_espanol": "Episodes are in Spanish.", "minutos": "min",
        "publicidad": "Advertisement",
        "codigos_eti": "Sponsored", "codigos_titulo": "Discount codes",
        "codigos_texto": "Save on your padel gear with our partners. Copy the code and use it at checkout.",
        "codigos_dto": "off", "copiar_codigo": "Copy", "codigo_copiado": "Copied",
    },
}

CAMPOS_IDIOMA = ("slug", "titulo", "entradilla", "seo_titulo", "seo_descripcion", "palabra_clave", "cuerpo")
SLUG_OK = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


# ---------------------------------------------------------------- utilidades
def fecha_larga(fecha, idioma):
    m = MESES[idioma][fecha.month - 1]
    if idioma == "es":
        return f"{fecha.day} de {m} de {fecha.year}"
    return f"{fecha.day} {m} {fecha.year}"


def fecha_corta(fecha, idioma):
    m = MESES[idioma][fecha.month - 1][:3]
    return f"{fecha.day} {m}" if idioma == "es" else f"{fecha.day} {m}"


def url_seccion(seccion, idioma):
    return f"{PREFIJO[idioma]}{SECCIONES[seccion][idioma][0]}/"


def a_html(texto_md):
    html = markdown.markdown(texto_md, extensions=["tables", "smarty", "sane_lists"],
                             extension_configs={"smarty": {"smart_quotes": False}})
    html = html.replace("<table>", '<div class="tabla"><table>').replace("</table>", "</table></div>")
    return html


def minutos_lectura(texto):
    palabras = len(re.findall(r"\w+", texto))
    return max(1, math.ceil(palabras / 200))


# ---------------------------------------------------------------- contenido
def momento_publicacion(fecha, hora):
    """Fecha y hora de publicación en hora de Madrid.
    Solo va en los datos para Google (JSON-LD, sitemaps, RSS, atributos datetime):
    el lector nunca ve la hora (decisión de Luis, 24/10)."""
    h, m = (int(x) for x in hora.split(":"))
    local = dt.datetime.combine(fecha, dt.time(h, m))
    if ZONA:
        return local.replace(tzinfo=ZONA)

    def ultimo_domingo(ano, mes):
        d = dt.date(ano, mes, 31)
        return d - dt.timedelta(days=(d.weekday() + 1) % 7)
    verano = ultimo_domingo(fecha.year, 3) <= fecha < ultimo_domingo(fecha.year, 10)
    return local.replace(tzinfo=dt.timezone(dt.timedelta(hours=2 if verano else 1)))


def cargar_noticias(avisos):
    noticias = []
    for ruta in sorted((RAIZ / "contenido" / "noticias").glob("*.yml")):
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        nombre = ruta.name
        fecha = datos.get("fecha")
        if isinstance(fecha, str):
            fecha = dt.date.fromisoformat(fecha)
        if not isinstance(fecha, dt.date):
            sys.exit(f"[{nombre}] falta 'fecha' (AAAA-MM-DD)")
        seccion = datos.get("seccion")
        if seccion not in SECCIONES:
            sys.exit(f"[{nombre}] 'seccion' debe ser una de: {', '.join(SECCIONES)}")
        portada = datos.get("portada") or {}
        tiene_hora = bool(datos.get("hora"))
        hora = datos.get("hora") or "00:00"
        if isinstance(hora, int):  # YAML lee 18:30 sin comillas como minutos (1110)
            hora = f"{hora // 60:02d}:{hora % 60:02d}"
        hora = str(hora).strip()
        if not re.fullmatch(r"\d{1,2}:\d{2}", hora):
            sys.exit(f"[{nombre}] 'hora' debe ser HH:MM")
        # sin 'hora' (noticias antiguas) no se inventa: solo el día
        momento = momento_publicacion(fecha, hora) if tiene_hora else None
        n = {
            "archivo": nombre, "fecha": fecha, "hora": hora.zfill(5), "seccion": seccion,
            "publicado": momento.isoformat() if momento else fecha.isoformat(),
            "publicado_dt": momento,
            "autor": datos.get("autor") or None,
            "etiquetas": datos.get("etiquetas") or [],
            "portada": {
                "imagen": portada.get("imagen") or "",
                "credito": portada.get("credito") or "",
                "rotulo": portada.get("rotulo") or SECCIONES[seccion]["es"][1],
                "dato": portada.get("dato") or "",
                "foco": portada.get("foco") or "50% 50%",
            },
        }
        for idioma in IDIOMAS:
            bloque = datos.get(idioma) or {}
            for campo in CAMPOS_IDIOMA:
                if not str(bloque.get(campo) or "").strip():
                    sys.exit(f"[{nombre}] falta '{idioma}.{campo}'")
            slug = bloque["slug"].strip()
            if not SLUG_OK.match(slug):
                sys.exit(f"[{nombre}] slug no válido en '{idioma}': usa minúsculas, números y guiones")
            if len(bloque["seo_titulo"]) > 60:
                avisos.append(f"[{nombre}] {idioma}.seo_titulo tiene {len(bloque['seo_titulo'])} caracteres (máx. recomendado 60)")
            ld = len(bloque["seo_descripcion"])
            if not 120 <= ld <= 160:
                avisos.append(f"[{nombre}] {idioma}.seo_descripcion tiene {ld} caracteres (recomendado 120-160)")
            cuerpo = bloque["cuerpo"]
            n[idioma] = {
                **{c: bloque[c].strip() for c in CAMPOS_IDIOMA if c != "cuerpo"},
                "cuerpo_html": a_html(cuerpo),
                "minutos": minutos_lectura(cuerpo),
                "url": f"{url_seccion(seccion, idioma)}{slug}/",
                "seccion_nombre": SECCIONES[seccion][idioma][1],
                "seccion_url": url_seccion(seccion, idioma),
                "fecha_larga": fecha_larga(fecha, idioma),
                "fecha_corta": fecha_corta(fecha, idioma),
            }
        noticias.append(n)
    # más reciente primero: fecha, luego hora de publicación, luego nombre de archivo
    noticias.sort(key=lambda n: (n["fecha"], n["hora"], n["archivo"]), reverse=True)
    vistos = set()
    for n in noticias:
        for idioma in IDIOMAS:
            if n[idioma]["url"] in vistos:
                sys.exit(f"[{n['archivo']}] el slug '{n[idioma]['slug']}' ya existe en {idioma}")
            vistos.add(n[idioma]["url"])
    return noticias


def cargar_episodios():
    ruta = RAIZ / "contenido" / "podcast" / "episodios.json"
    if not ruta.exists():
        return []
    episodios = []
    for e in json.loads(ruta.read_text(encoding="utf-8")):
        if e.get("oculto") or not e.get("fecha"):
            continue
        e = dict(e)
        e["fecha"] = dt.date.fromisoformat(e["fecha"])
        episodios.append(e)
    episodios.sort(key=lambda e: e["fecha"], reverse=True)
    return episodios


# ---------------------------------------------------------------- render
class Constructor:
    def __init__(self, preview):
        self.preview = preview
        self.sitio = yaml.safe_load((RAIZ / "sitio.yml").read_text(encoding="utf-8"))
        self.sitio["url"] = self.sitio["url"].rstrip("/")
        self.env = Environment(loader=FileSystemLoader(RAIZ / "plantillas"),
                               autoescape=select_autoescape(["html"]),
                               trim_blocks=True, lstrip_blocks=True)
        self.avisos = []
        self.noticias = cargar_noticias(self.avisos)
        self.paginas = []  # (ruta, {idioma: url}) para el sitemap
        self.episodios = cargar_episodios()
        # la versión cambia solo si cambia el CSS (así no hay cambios falsos en cada construcción)
        self.version = hashlib.md5((RAIZ / "estaticos" / "css" / "estilos.css").read_bytes()).hexdigest()[:8]

    def rel_factory(self, actual):
        """Devuelve una función que convierte rutas del sitio en enlaces relativos desde 'actual'."""
        base = actual.rstrip("/") or "."

        def rel(destino):
            ancla = ""
            if "#" in destino:
                destino, ancla = destino.split("#", 1)
                ancla = "#" + ancla
            es_carpeta = destino == "" or destino.endswith("/")
            r = os.path.relpath(destino.rstrip("/") or ".", base)
            if es_carpeta:
                r = "" if r == "." else r + "/"
                if self.preview:
                    r += "index.html"
                elif r == "":
                    r = "./"
            return (r + ancla) or "#"
        return rel

    def absoluta(self, ruta):
        return f"{self.sitio['url']}/{ruta}"

    def escribir(self, ruta, plantilla, idioma, alternos, lastmod=None, **ctx):
        """ruta: carpeta de la página ('' = raíz) o archivo .html
        lastmod: fecha (o fecha y hora) de su último cambio, para el sitemap"""
        es_archivo = ruta.endswith(".html")
        carpeta = str(Path(ruta).parent) if es_archivo else ruta.rstrip("/")
        carpeta = "" if carpeta == "." else carpeta
        rel = self.rel_factory(carpeta)
        if ruta == "404.html" and not self.preview:
            # GitHub Pages sirve el 404 desde cualquier ruta: enlaces absolutos
            rel = lambda d: "/" + d  # noqa: E731
        t = TEXTOS[idioma]
        otro = "en" if idioma == "es" else "es"
        fragmento = self.preview and ruta == ""
        html = self.env.get_template(plantilla).render(
            sitio=self.sitio, t=t, idioma=idioma, otro=otro, rel=rel,
            preview=self.preview, fragmento=fragmento, version=self.version,
            prefijo=PREFIJO[idioma],
            secciones=[(k, SECCIONES[k][idioma][1], url_seccion(k, idioma)) for k in SECCIONES],
            textos_sitio=self.sitio["textos"][idioma],
            canonical=self.absoluta(ruta) if not es_archivo else None,
            alternos={k: self.absoluta(v) for k, v in alternos.items()},
            alterno_rel=rel(alternos[otro]) if otro in alternos else rel(PREFIJO[otro]),
            ano=dt.date.today().year,
            **ctx,
        )
        destino = SALIDA / (ruta if es_archivo else f"{ruta}index.html")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(html, encoding="utf-8")
        if not es_archivo:
            self.paginas.append((ruta, alternos, lastmod))

    def construir(self):
        if SALIDA.exists():
            shutil.rmtree(SALIDA)
        shutil.copytree(RAIZ / "estaticos", SALIDA)
        (SALIDA / ".nojekyll").write_text("")
        if self.sitio.get("dominio"):
            (SALIDA / "CNAME").write_text(self.sitio["dominio"].strip() + "\n")

        for idioma in IDIOMAS:
            vista = [self.vista(n, idioma) for n in self.noticias]
            actualidad = [v for v in vista if v["seccion"] != "opinion"]
            # arriba va siempre la última publicada; las demás pasan a «Lo último»
            destacada = actualidad[0] if actualidad else None
            resto = [v for v in actualidad if v is not destacada][:6]
            opinion = [v for v in vista if v["seccion"] == "opinion"][:3]

            episodios = [self.vista_episodio(e, idioma) for e in self.episodios]
            ultimo = {  # último cambio de cada página de sección, para el sitemap
                "actualidad": actualidad[0]["publicado"] if actualidad else None,
                "opinion": opinion[0]["publicado"] if opinion else None,
                "podcast": episodios[0]["fecha"].isoformat() if episodios else None,
            }

            # portada
            self.escribir(PREFIJO[idioma], "portada.html", idioma,
                          {i: PREFIJO[i] for i in IDIOMAS},
                          lastmod=max([x for x in ultimo.values() if x], default=None,
                                      key=lambda x: x[:10]),
                          destacada=destacada, resto=resto, opinion=opinion,
                          ultimo_episodio=episodios[0] if episodios else None,
                          titulo_pagina=None, descripcion=self.sitio["textos"][idioma]["descripcion"])

            # secciones
            for clave in SECCIONES:
                lista = episodios if clave == "podcast" else [v for v in vista if v["seccion"] == clave]
                self.escribir(url_seccion(clave, idioma), "seccion.html", idioma,
                              {i: url_seccion(clave, i) for i in IDIOMAS},
                              lastmod=ultimo.get(clave),
                              clave=clave, nombre=SECCIONES[clave][idioma][1], lista=lista,
                              descripcion_seccion=(TEXTOS[idioma]["secciones_desc"][clave]
                                                   or self.sitio["textos"][idioma]["podcast"]),
                              titulo_pagina=SECCIONES[clave][idioma][1],
                              descripcion=TEXTOS[idioma]["secciones_desc"][clave] or self.sitio["textos"][idioma]["podcast"])

            # newsletter
            self.escribir(f"{PREFIJO[idioma]}newsletter/", "newsletter.html", idioma,
                          {i: f"{PREFIJO[i]}newsletter/" for i in IDIOMAS},
                          titulo_pagina=TEXTOS[idioma]["newsletter"],
                          descripcion=self.sitio["textos"][idioma]["newsletter"])

            # noticias
            for v in vista:
                n = v["_n"]
                relacionadas = [x for x in vista if x is not v][:3]
                self.escribir(v["url"], "noticia.html", idioma,
                              {i: n[i]["url"] for i in IDIOMAS},
                              lastmod=v["publicado"],
                              n=v, relacionadas=relacionadas,
                              titulo_pagina=v["seo_titulo"], descripcion=v["seo_descripcion"],
                              json_ld=self.json_ld(v, idioma))

            # episodios del podcast (solo en español: el podcast es en español)
            if idioma == "es":
                for k, ep in enumerate(episodios):
                    otros = [x for x in episodios if x is not ep][:3]
                    self.escribir(ep["url"], "episodio.html", "es", {"es": ep["url"]},
                                  lastmod=ep["fecha"].isoformat(),
                                  ep=ep, otros=otros, titulo_pagina=ep["titulo"],
                                  descripcion=(ep["entradilla"] or self.sitio["textos"]["es"]["podcast"])[:160],
                                  json_ld=self.json_ld_episodio(ep))

            self.rss(idioma, vista)

        # 404 (solo en español, con enlace a ambas portadas)
        self.escribir("404.html", "404.html", "es", {"es": "", "en": "en/"},
                      titulo_pagina="404", descripcion="")
        self.sitemap()
        self.sitemap_noticias()
        # tarjetas para Instagram y TikTok (docs/img/redes/<slug>-ig.jpg y -tt.jpg)
        import redes
        redes.generar(self.noticias, SALIDA, RAIZ / "estaticos")
        (SALIDA / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {self.absoluta('sitemap.xml')}\n"
                                           f"Sitemap: {self.absoluta('sitemap-noticias.xml')}\n")
        return self

    def vista(self, n, idioma):
        v = dict(n[idioma])
        v.update(seccion=n["seccion"], fecha=n["fecha"], publicado=n["publicado"],
                 etiquetas=n["etiquetas"], portada=n["portada"],
                 autor=n["autor"] or self.sitio["autor_por_defecto"], _n=n)
        return v

    def vista_episodio(self, e, idioma):
        texto = e.get("texto") or []
        entradilla = texto[0] if texto else ""
        if len(entradilla) > 170:
            entradilla = entradilla[:170].rsplit(" ", 1)[0] + "…"
        mini = f"https://i.ytimg.com/vi/{e['youtube']}/mqdefault.jpg" if e.get("youtube") else ""
        minutos = e.get("duracion_min")
        return {
            **e,
            "url": f"podcast/{e['id']}/",
            "seccion": "podcast", "seccion_nombre": SECCIONES["podcast"][idioma][1],
            "seccion_url": url_seccion("podcast", idioma),
            "fecha_larga": fecha_larga(e["fecha"], idioma), "fecha_corta": fecha_corta(e["fecha"], idioma),
            "entradilla": entradilla,
            "duracion": f"{minutos} {TEXTOS[idioma]['minutos']}" if minutos else "",
            "portada": {"imagen": mini, "credito": "", "foco": "50% 50%",
                        "rotulo": e["titulo"] if len(e["titulo"]) <= 14 else TEXTOS[idioma]["episodio"],
                        "dato": fecha_corta(e["fecha"], idioma)},
            "autor": "Bola Pádel Podcast",
        }

    def json_ld_episodio(self, ep):
        datos = {
            "@context": "https://schema.org", "@type": "PodcastEpisode",
            "name": ep["titulo"], "datePublished": ep["fecha"].isoformat(),
            "description": " ".join(ep.get("texto") or [])[:500], "inLanguage": "es",
            "url": self.absoluta(ep["url"]),
            "partOfSeries": {"@type": "PodcastSeries", "name": "Bola Pádel Podcast",
                             "url": self.absoluta(url_seccion("podcast", "es"))},
        }
        if ep.get("duracion_min"):
            datos["timeRequired"] = f"PT{ep['duracion_min']}M"
        if ep.get("audio"):
            datos["associatedMedia"] = {"@type": "MediaObject", "contentUrl": ep["audio"]}
        if ep.get("youtube"):
            datos["video"] = {"@type": "VideoObject", "name": ep["titulo"],
                              "embedUrl": f"https://www.youtube-nocookie.com/embed/{ep['youtube']}",
                              "thumbnailUrl": f"https://i.ytimg.com/vi/{ep['youtube']}/maxresdefault.jpg",
                              "uploadDate": ep["fecha"].isoformat()}
        return json.dumps(datos, ensure_ascii=False)

    def json_ld(self, v, idioma):
        imagen = self.absoluta(v["portada"]["imagen"]) if v["portada"]["imagen"] else self.absoluta("img/compartir.jpg")
        datos = {
            "@context": "https://schema.org",
            "@type": "OpinionNewsArticle" if v["seccion"] == "opinion" else "NewsArticle",
            "headline": v["titulo"],
            "description": v["seo_descripcion"],
            "inLanguage": idioma,
            "datePublished": v["publicado"],
            "dateModified": v["publicado"],
            "author": {"@type": "Person", "name": v["autor"]},
            "publisher": {"@type": "Organization", "name": self.sitio["nombre"],
                          "logo": {"@type": "ImageObject", "url": self.absoluta("img/logo.png")}},
            "image": [imagen],
            "keywords": ", ".join([v["palabra_clave"], *v["etiquetas"]]),
            "mainEntityOfPage": self.absoluta(v["url"]),
        }
        return json.dumps(datos, ensure_ascii=False)

    def rss(self, idioma, vista):
        items = []
        for v in vista[:30]:
            enlace = self.absoluta(v["url"])
            momento = v["_n"]["publicado_dt"]
            if momento:
                fecha = format_datetime(momento)
            else:
                fecha = dt.datetime.combine(v["fecha"], dt.time(9, 0)).strftime("%a, %d %b %Y %H:%M:%S +0000")
            items.append(
                f"<item><title>{xml_escape(v['titulo'])}</title><link>{enlace}</link>"
                f"<guid>{enlace}</guid><pubDate>{fecha}</pubDate>"
                f"<description>{xml_escape(v['entradilla'])}</description></item>")
        canal = (f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
                 f"<title>{xml_escape(self.sitio['nombre'])}</title>"
                 f"<link>{self.absoluta(PREFIJO[idioma])}</link>"
                 f"<description>{xml_escape(self.sitio['textos'][idioma]['descripcion'])}</description>"
                 f"<language>{idioma}</language>{''.join(items)}</channel></rss>\n")
        ruta = SALIDA / PREFIJO[idioma] / "feed.xml"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(canal, encoding="utf-8")

    def sitemap(self):
        filas = []
        for ruta, alternos, lastmod in self.paginas:
            alt = "".join(f'<xhtml:link rel="alternate" hreflang="{i}" href="{self.absoluta(u)}"/>'
                          for i, u in alternos.items())
            mod = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
            filas.append(f"<url><loc>{self.absoluta(ruta)}</loc>{mod}{alt}</url>")
        (SALIDA / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">' + "".join(filas) + "</urlset>\n",
            encoding="utf-8")

    def sitemap_noticias(self):
        """Sitemap de noticias (formato de Google News): las publicadas en las 48 horas
        anteriores a la última noticia. Se calcula sobre la última noticia y no sobre la
        hora de construcción para que la web no cambie sola cada vez que se construye."""
        con_hora = [n for n in self.noticias if n["publicado_dt"]]
        filas = []
        if con_hora:
            ultima = max(n["publicado_dt"] for n in con_hora)
            recientes = [n for n in con_hora if ultima - n["publicado_dt"] <= dt.timedelta(hours=48)]
            for n in recientes:
                for idioma in IDIOMAS:
                    filas.append(
                        f"<url><loc>{self.absoluta(n[idioma]['url'])}</loc><news:news>"
                        f"<news:publication><news:name>{xml_escape(self.sitio['nombre'])}</news:name>"
                        f"<news:language>{idioma}</news:language></news:publication>"
                        f"<news:publication_date>{n['publicado']}</news:publication_date>"
                        f"<news:title>{xml_escape(n[idioma]['titulo'])}</news:title>"
                        f"</news:news></url>")
        (SALIDA / "sitemap-noticias.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">' + "".join(filas) + "</urlset>\n",
            encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Construye la web de Bola Pádel")
    p.add_argument("--preview", action="store_true", help="modo vista previa")
    args = p.parse_args()
    c = Constructor(args.preview).construir()
    total = sum(1 for _ in SALIDA.rglob("*.html"))
    print(f"Web construida en {SALIDA} · {len(c.noticias)} noticias · {total} páginas")
    for a in c.avisos:
        print("AVISO SEO:", a)


if __name__ == "__main__":
    main()
