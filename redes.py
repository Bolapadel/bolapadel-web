"""Tarjetas para redes sociales (Instagram y TikTok) de cada noticia.

construir.py las genera en docs/img/redes/ con cada construcción:
  <slug>-ig.jpg  1080x1350 (post de Instagram, 4:5)
  <slug>-tt.jpg  1080x1920 (foto de TikTok, 9:16, con márgenes para los botones de la app)

Así quedan publicadas en https://bolapadel.es/img/redes/... y Metricool puede usarlas.
Uso suelto, para ver una tarjeta:  python3 redes.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

RAIZ = Path(__file__).resolve().parent
FUENTES = RAIZ / "herramientas" / "fuentes"

AZUL = (25, 82, 149)
LIMA = (155, 185, 41)
LIMA_CLARO = (207, 226, 122)
SOBRE_LIMA = (15, 27, 45)
NOCHE = (10, 26, 48)
PORTADA_A = (30, 92, 163)
PORTADA_B = (16, 57, 107)
BLANCO = (255, 255, 255)

FORMATOS = {
    # ancho, alto, margen lateral, margen inferior, margen derecho, alto zona logo
    "ig": dict(w=1080, h=1350, lado=72, abajo=72, derecha=72, arriba=64, max_lineas=5),
    "tt": dict(w=1080, h=1920, lado=72, abajo=430, derecha=170, arriba=150, max_lineas=6),
}


def _fuente(nombre, tam):
    return ImageFont.truetype(str(FUENTES / f"{nombre}.ttf"), tam)


def _foco(foco):
    try:
        x, y = (float(p.strip().rstrip("%")) / 100 for p in foco.split())
        return x, y
    except Exception:
        return 0.5, 0.5


def _recortar(img, w, h, foco):
    """Recorte tipo object-fit: cover, respetando el foco (x% y%)."""
    fx, fy = _foco(foco)
    escala = max(w / img.width, h / img.height)
    nw, nh = round(img.width * escala), round(img.height * escala)
    img = img.resize((nw, nh), Image.LANCZOS)
    x = round((nw - w) * fx)
    y = round((nh - h) * fy)
    return img.crop((x, y, x + w, y + h))


def _degradado(w, h, desde, hasta, color, alfa_max, curva=1.6):
    """Capa RGBA transparente arriba y oscura abajo, entre las filas desde/hasta."""
    capa = Image.new("RGBA", (w, h), color + (0,))
    px = Image.new("L", (1, h), 0)
    for y in range(h):
        if y <= desde:
            a = 0
        elif y >= hasta:
            a = alfa_max
        else:
            t = (y - desde) / (hasta - desde)
            a = round(alfa_max * (t ** (1 / curva)))
        px.putpixel((0, y), a)
    capa.putalpha(px.resize((w, h)))
    return capa


def _fondo_grafico(w, h):
    """Portada sin foto: degradado azul con la costura de la bola."""
    fondo = Image.new("RGB", (w, h), PORTADA_B)
    d = ImageDraw.Draw(fondo)
    for y in range(h):
        t = y / h
        c = tuple(round(PORTADA_A[i] * (1 - t) + PORTADA_B[i] * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c)
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    grosor = round(w / 90)
    dc.arc([-w * 0.55, -h * 0.30, w * 1.55, h * 0.55], 200, 340, fill=(255, 255, 255, 46), width=grosor)
    dc.arc([-w * 0.55, h * 0.62, w * 1.55, h * 1.55], 20, 160, fill=(255, 255, 255, 46), width=grosor)
    return Image.alpha_composite(fondo.convert("RGBA"), capa)


def _partir(texto, fuente, ancho, draw):
    palabras = texto.split()
    lineas, actual = [], ""
    for p in palabras:
        prueba = f"{actual} {p}".strip()
        if draw.textlength(prueba, font=fuente) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def _ajustar_titular(texto, ancho, max_lineas, draw, grande=104, minimo=64):
    tam = grande
    while tam >= minimo:
        f = _fuente("SairaCondensed-ExtraBold", tam)
        lineas = _partir(texto, f, ancho, draw)
        if len(lineas) <= max_lineas and all(draw.textlength(l, font=f) <= ancho for l in lineas):
            return f, lineas, tam
        tam -= 4
    f = _fuente("SairaCondensed-ExtraBold", minimo)
    return f, _partir(texto, f, ancho, draw)[:max_lineas], minimo


def tarjeta(n, formato, raiz_imagenes, idioma="es"):
    """Devuelve la tarjeta (Image RGB) de una noticia ya cargada por construir.py."""
    cfg = FORMATOS[formato]
    w, h = cfg["w"], cfg["h"]
    portada = n["portada"]
    v = n[idioma]

    if portada.get("imagen") and not portada["imagen"].startswith("http"):
        foto = Image.open(raiz_imagenes / portada["imagen"]).convert("RGB")
        foco = portada.get("foco") or "50% 50%"
        if formato == "tt":
            # TikTok: la foto arriba y el texto sobre fondo oscuro, para no tapar caras
            alto_foto = 1240
            base = Image.new("RGBA", (w, h), NOCHE + (255,))
            base.paste(_recortar(foto, w, alto_foto, foco), (0, 0))
            base = Image.alpha_composite(base, _degradado(w, h, alto_foto - 520, alto_foto, NOCHE, 255, curva=1.3))
        else:
            base = _recortar(foto, w, h, foco).convert("RGBA")
            base = Image.alpha_composite(base, _degradado(w, h, round(h * 0.34), round(h * 0.86), NOCHE, 238))
        # sombra suave arriba para que el logo se lea sobre cualquier foto
        sombra = Image.new("RGBA", (w, 300), NOCHE + (0,))
        mascara = Image.linear_gradient("L").rotate(180).resize((w, 300)).point(lambda a: round(a * 0.45))
        sombra.putalpha(mascara)
        base.alpha_composite(sombra, (0, 0))
        con_foto = True
    else:
        base = _fondo_grafico(w, h)
        con_foto = False

    d = ImageDraw.Draw(base)
    lado, derecha = cfg["lado"], cfg["derecha"]
    ancho = w - lado - derecha

    # logo arriba a la izquierda, con una sombra suave
    logo = Image.open(raiz_imagenes / "img" / "logo.png").convert("RGBA")
    tam_logo = 150
    logo = logo.resize((tam_logo, tam_logo), Image.LANCZOS)
    sombra_logo = Image.new("RGBA", (tam_logo + 40, tam_logo + 40), (0, 0, 0, 0))
    sombra_logo.paste((0, 0, 0, 110), (20, 20), logo.split()[3])
    sombra_logo = sombra_logo.filter(ImageFilter.GaussianBlur(10))
    base.alpha_composite(sombra_logo, (lado - 20, cfg["arriba"] - 14))
    base.alpha_composite(logo, (lado, cfg["arriba"]))

    # pie: web + crédito de la foto
    f_web = _fuente("Saira-SemiBold", 34)
    f_cred = _fuente("Saira-Medium", 22)
    y_pie = h - cfg["abajo"] - 34
    d.text((lado, y_pie), "bolapadel.es", font=f_web, fill=LIMA_CLARO)
    if con_foto and portada.get("credito"):
        cred = ("Foto: " if idioma == "es" else "Photo: ") + portada["credito"]
        while d.textlength(cred, font=f_cred) > ancho - d.textlength("bolapadel.es", font=f_web) - 40 and f_cred.size > 16:
            f_cred = _fuente("Saira-Medium", f_cred.size - 1)
        d.text((w - derecha - d.textlength(cred, font=f_cred), y_pie + 10), cred,
               font=f_cred, fill=(255, 255, 255, 190))

    # línea lima sobre el pie
    y_linea = y_pie - 30
    d.rectangle([lado, y_linea, lado + 96, y_linea + 6], fill=LIMA)

    # titular, de abajo arriba
    f_tit, lineas, tam = _ajustar_titular(v["titulo"], ancho, cfg["max_lineas"], d)
    interlinea = round(tam * 1.02)
    y_tit = y_linea - 34 - interlinea * len(lineas)
    for i, linea in enumerate(lineas):
        d.text((lado, y_tit + i * interlinea), linea, font=f_tit, fill=BLANCO)

    # etiqueta: sección · rótulo
    seccion = v["seccion_nombre"]
    # en inglés, el rótulo traducido (portada.rotulo_en); si no lo hay, solo la sección
    rotulo = ((portada.get("rotulo") if idioma == "es" else portada.get(f"rotulo_{idioma}")) or "").strip()
    etiqueta = seccion if not rotulo or rotulo.lower() == seccion.lower() else f"{seccion} · {rotulo}"
    etiqueta = etiqueta.upper()
    f_eti = _fuente("SairaCondensed-Bold", 34)
    ancho_eti = d.textlength(etiqueta, font=f_eti)
    y_eti = y_tit - 34 - 52
    d.rounded_rectangle([lado, y_eti, lado + ancho_eti + 36, y_eti + 52], radius=6, fill=LIMA)
    d.text((lado + 18, y_eti + 5), etiqueta, font=f_eti, fill=SOBRE_LIMA)

    # sin foto: el dato grande en el centro
    dato = (portada.get(f"dato_{idioma}") if idioma != "es" else None) or portada.get("dato")
    if not con_foto and dato:
        f_dato = _fuente("SairaCondensed-ExtraBold", 72)
        d.text((lado, round(h * 0.30)), dato, font=f_dato, fill=LIMA_CLARO)

    return base.convert("RGB")


def generar(noticias, salida, raiz_imagenes, idiomas=("es", "en")):
    """Escribe las tarjetas de todas las noticias en <salida>/img/redes/:
    <slug-es>-ig.jpg / -tt.jpg (español) y <slug-en>-ig.jpg / -tt.jpg (inglés).
    En redes van en carrusel: primero la española y después la inglesa (Luis, 30/10)."""
    carpeta = salida / "img" / "redes"
    carpeta.mkdir(parents=True, exist_ok=True)
    for n in noticias:
        for idioma in idiomas:
            slug = n[idioma]["slug"]
            for formato in FORMATOS:
                img = tarjeta(n, formato, raiz_imagenes, idioma)
                img.save(carpeta / f"{slug}-{formato}.jpg", "JPEG", quality=86, optimize=True, progressive=True)
    return carpeta


if __name__ == "__main__":
    import construir
    avisos = []
    ns = construir.cargar_noticias(avisos)
    destino = RAIZ / "herramientas" / "prueba-redes"
    destino.mkdir(parents=True, exist_ok=True)
    for n in ns:
        for idioma in ("es", "en"):
            for formato in FORMATOS:
                tarjeta(n, formato, RAIZ / "estaticos", idioma).save(destino / f"{n[idioma]['slug']}-{formato}.jpg", quality=86)
    print("Tarjetas de prueba en", destino)
