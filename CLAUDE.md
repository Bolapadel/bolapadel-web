# Web de Bola Pádel — instrucciones para Claude

Web de noticias de Bola Pádel (medio de pádel de Luis González). Estática, generada con Python y publicada con GitHub Pages desde la carpeta `docs/` de la rama `main`.

## Regla de oro
Nada se publica sin el OK de Luis. Primero se le enseña la noticia redactada; solo con su visto bueno se hace commit y push.

## Añadir una noticia
1. Luis pasa la noticia como le venga (texto, notas, enlace).
2. Verificar datos (resultados, fechas, rankings) con las herramientas de Padel Analyst o la web. Nunca inventar datos.
3. Crear `contenido/noticias/AAAA-MM-DD-palabras-clave.yml` siguiendo `contenido/_plantilla-noticia.yml`:
   - `es` y `en` completos (el inglés es traducción fiel).
   - Paquete SEO siempre: `slug`, `seo_titulo` (≤60), `seo_descripcion` (120-160), `palabra_clave`.
   - Sin foto propia o con derechos → portada gráfica (`rotulo` corto + `dato`). No usar fotos de terceros.
   - Portada: la última noticia publicada va siempre arriba y la anterior pasa a «Lo último» (decisión de Luis, 20/10). Es automático, no hay que marcar nada. Poner siempre `hora` (HH:MM, hora de publicación) para que las del mismo día se ordenen bien.
4. `python3 construir.py` (avisa si el SEO se sale de rango).
5. Enseñar a Luis el texto. Con su OK: `git add -A && git commit && git push`.

## Fotos
- Luis está autorizado a usar las fotos de prensa de Premier Padel en Greenfly (portal.greenfly.com, canal 2089 → Biblioteca → Galerías). Hay que iniciar sesión con su cuenta: eso lo hace él, nunca Claude.
- Elegir la foto mirando las etiquetas del archivo (nombres de jugadores) y enseñársela a Luis antes de usarla.
- Descarga: abrir `https://portal.greenfly.com/library/media/<ID>/download?galleryId=<galería>` en el navegador integrado (se guarda en ~/Downloads) y pasarla al espacio de trabajo.
- Gráficas oficiales de terceros (p. ej. las de la FEP) solo si Luis lo pide, con el crédito de la entidad. Si son verticales, para la portada se hace una versión 16:9 con la gráfica entera centrada sobre su propio fondo desenfocado y margen abajo para el crédito (ejemplo: noticia del Mundial, 21/10).
- Imágenes dentro del texto: en el `cuerpo`, una línea aparte con `<figure><img src="/img/noticias/archivo.jpg" alt="…" width="…" height="…" loading="lazy"><figcaption>Imagen: …</figcaption></figure>` (ruta desde la raíz, con línea en blanco antes y después).
- Web: lado largo 1600-1750 px, JPEG calidad 72-80, en `estaticos/img/noticias/`. Crédito: «Nombre del fotógrafo / Premier Padel» (sale en el título del archivo en Greenfly). En fotos verticales, ajustar `foco` para no cortar caras.

## Redes (Instagram y TikTok, vía Metricool)
- Decisión de Luis (21/10): cada noticia sale también en Instagram (@bola.padel) y TikTok (@bolapadel_) con una tarjeta (foto + etiqueta + titular + logo), a la mejor hora del día según Metricool.
- Las tarjetas las genera `redes.py` al construir: `docs/img/redes/<slug-es>-ig.jpg` (1080x1350) y `-tt.jpg` (1080x1920, con margen abajo y a la derecha para los botones de TikTok). Fuentes en `herramientas/fuentes/`. Para verlas sin construir: `python3 redes.py` (salen en `herramientas/prueba-redes/`, no se sube).
- Texto para redes: en la noticia, bloque `redes.texto` (ver plantilla). Corto, con la voz de Bola Pádel, sin clickbait, terminando en «… en bolapadel.es» y 3-5 hashtags.
- Se enseña a Luis junto con la noticia (texto web + tarjeta + texto de redes). Publicar en redes necesita su OK, igual que la web.
- Con el OK y la web ya subida: como imagen usar `https://raw.githubusercontent.com/Bolapadel/bolapadel-web/main/docs/img/redes/<slug>-ig.jpg` (disponible nada más hacer push y comprobable con curl; bolapadel.es no se alcanza desde el espacio de trabajo; Metricool copia la imagen a su servidor), pedir a Metricool `getBestTimeToPostByNetwork` (marca 5619697, Europe/Madrid) para instagram y tiktok desde ahora hasta fin del día (si es tarde, el día siguiente) y programar con `createScheduledPost` **dos publicaciones**: una de Instagram (POST, media = tarjeta -ig) y otra de TikTok (media = tarjeta -tt). Apuntar fecha y hora en `redes.instagram` / `redes.tiktok` del YAML.
- Carrusel (si Luis pide varias imágenes en el mismo post, en vez de la tarjeta): preparar las diapositivas en `estaticos/img/redes/<slug>-1-ig.jpg`, `-2-ig.jpg`… (1080x1350) y `-1-tt.jpg`, `-2-tt.jpg`… (1080x1920, imagen con margen para la interfaz de TikTok); al construir se copian a `docs/img/redes/`. En Metricool se pasan todas en `media`, en el orden del carrusel (TikTok: `photoCoverIndex` 0 y un `title`).

## Publicidad
- Decisión de Luis (22/10): en la **portada**, PadelPROShop fijo encima de la noticia principal y Samogrip fijo debajo de «Lo último». En **cada noticia**, PadelPROShop justo después del texto (tras la firma) y Samogrip después del recuadro de la newsletter. **Nunca publicidad en medio del texto** (Luis, 22/10).
- Todo se configura en `sitio.yml` → `publicidad` (`portada_arriba`, `portada_abajo`, `noticias_final`, `noticias_abajo` y la lista `banners` con marca, enlace, imagen 1200x300, imagen_movil 770x300 y alt). Imágenes en `estaticos/img/publicidad/`. Siempre con la etiqueta «Publicidad» y `rel="sponsored"`.
- Las versiones móviles son la parte del banner con el logo y el código, para que se lea. El banner de Samogrip lo rediseñó Claude a partir del de Luis (fondo kraft, cupón BOLAPADEL10).

## Podcast
- Los episodios salen solos: `.github/workflows/podcast.yml` ejecuta `podcast.py` dos veces al día, lee el RSS de Spotify for Creators y el de YouTube (datos en `sitio.yml`), los une por título/número/fecha y guarda `contenido/podcast/episodios.json`. Luego construye y publica.
- Los clips y shorts (< 20 min) no entran. Para ocultar un episodio: `"oculto": true` en el JSON.
- De las descripciones se quita la publicidad y los enlaces a redes (lista `CORTES` en `podcast.py`).
- El vídeo de YouTube solo se carga si el lector pulsa «Ver el episodio» (youtube-nocookie), para no meter cookies.

## Tono editorial
Frases cortas, directo, confesional, estilo Isra Bravo. Nada de clickbait ni lenguaje corporativo. Respeto total a jugadores, representantes y sus entornos. Sin párrafos-bloque. Bola Pádel y Padelkora son marcas separadas: no mezclarlas.

## Estructura
- `sitio.yml` — configuración (URL, dominio, redes, MailerLite, podcast, textos).
- `contenido/noticias/` — una noticia por archivo YAML.
- `plantillas/` — HTML (Jinja2). `estaticos/` — CSS, fuentes, imágenes.
- `construir.py` — genera `docs/`. `--preview` = vista previa con enlaces a index.html y aviso de prueba (no subir a GitHub en ese modo).
- Dependencias: `pip install jinja2 markdown pyyaml pillow`.
