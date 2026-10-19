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
   - `destacada: true` solo en una noticia (la que va arriba en la portada); quitársela a la anterior.
4. `python3 construir.py` (avisa si el SEO se sale de rango).
5. Enseñar a Luis el texto. Con su OK: `git add -A && git commit && git push`.

## Fotos
- Luis está autorizado a usar las fotos de prensa de Premier Padel en Greenfly (portal.greenfly.com, canal 2089 → Biblioteca → Galerías). Hay que iniciar sesión con su cuenta: eso lo hace él, nunca Claude.
- Elegir la foto mirando las etiquetas del archivo (nombres de jugadores) y enseñársela a Luis antes de usarla.
- Descarga: abrir `https://portal.greenfly.com/library/media/<ID>/download?galleryId=<galería>` en el navegador integrado (se guarda en ~/Downloads) y pasarla al espacio de trabajo.
- Web: lado largo 1600-1750 px, JPEG calidad 72-80, en `estaticos/img/noticias/`. Crédito: «Nombre del fotógrafo / Premier Padel» (sale en el título del archivo en Greenfly). En fotos verticales, ajustar `foco` para no cortar caras.

## Tono editorial
Frases cortas, directo, confesional, estilo Isra Bravo. Nada de clickbait ni lenguaje corporativo. Respeto total a jugadores, representantes y sus entornos. Sin párrafos-bloque. Bola Pádel y Padelkora son marcas separadas: no mezclarlas.

## Estructura
- `sitio.yml` — configuración (URL, dominio, redes, MailerLite, podcast, textos).
- `contenido/noticias/` — una noticia por archivo YAML.
- `plantillas/` — HTML (Jinja2). `estaticos/` — CSS, fuentes, imágenes.
- `construir.py` — genera `docs/`. `--preview` = vista previa con enlaces a index.html y aviso de prueba (no subir a GitHub en ese modo).
- Dependencias: `pip install jinja2 markdown pyyaml`.
