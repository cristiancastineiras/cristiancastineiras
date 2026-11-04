---
title: "SEO técnico para un blog de desarrollo: datos estructurados, canonical y validación en CI"
seoTitle: "SEO técnico para un blog de desarrollo"
description: "Lo que de verdad importa en el SEO técnico de un blog: JSON-LD de BlogPosting, URLs canónicas, sitemap, RSS y cómo validarlo automáticamente en cada despliegue."
date: 2026-09-28
tags: ["SEO técnico", "Hugo", "CI/CD"]
---

Ninguna configuración técnica va a posicionar un artículo que no aporte nada. Lo que sí puede hacer es impedir que uno bueno aparezca, o que los buscadores entiendan quién lo ha escrito. Por suerte, en un blog estático esto se resuelve una sola vez en las plantillas, y se puede comprobar automáticamente.

## Lo básico que no puede fallar

Cada página debería tener:

- un `<title>` único y descriptivo;
- una `meta description` propia;
- un único `h1`;
- `lang` correcto en la etiqueta `html`;
- una URL canónica.

```html
<html lang="es">
<head>
  <title>Leer EXPLAIN ANALYZE en PostgreSQL | Mi blog</title>
  <meta name="description" content="Cómo interpretar nodos, costes y estimaciones...">
  <link rel="canonical" href="https://ejemplo.com/posts/explain-analyze/">
</head>
```

La descripción no influye de forma directa en el ranking, pero sí en que alguien haga clic, si el buscador decide mostrarla.

## URL canónica

La misma página puede ser accesible de varias maneras: con y sin barra final, con parámetros de seguimiento, o en otro dominio si republicas en una plataforma externa. La etiqueta `canonical` indica cuál es la principal, de modo que las señales no se reparten.

Si publicas el artículo también en otro sitio, intenta que la copia apunte a tu URL original.

## Datos estructurados

JSON-LD describe el contenido de forma explícita. Para un artículo, basta con el tipo `BlogPosting`:

```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "Leer EXPLAIN ANALYZE en PostgreSQL",
  "description": "Cómo interpretar nodos, costes y estimaciones.",
  "datePublished": "2026-09-28",
  "dateModified": "2026-09-28",
  "author": {
    "@type": "Person",
    "name": "Tu nombre",
    "url": "https://ejemplo.com/"
  },
  "mainEntityOfPage": "https://ejemplo.com/posts/explain-analyze/"
}
```

El autor con una URL que lo identifique ayuda a conectar tu trabajo con tu perfil. Además, estos datos deben coincidir con lo visible en la página. Google no recompensa el marcado que describe algo que el usuario no ve, y puede penalizarlo.

En Hugo, se puede generar con una plantilla y `jsonify`, para evitar problemas al escapar comillas:

```html
<script type="application/ld+json">
{{ dict
    "@context" "https://schema.org"
    "@type" "BlogPosting"
    "headline" .Title
    "datePublished" (.Date.Format "2006-01-02")
    "dateModified" (.Lastmod.Format "2006-01-02")
  | jsonify | safeJS }}
</script>
```

Compruébalo con la [prueba de resultados enriquecidos](https://search.google.com/test/rich-results) y con el [validador de Schema.org](https://validator.schema.org/).

## Fechas

`dateModified` debe cambiar cuando el contenido cambie de verdad. Actualizar la fecha sin tocar nada no aporta ninguna ventaja, y los buscadores lo saben comparar. En Hugo, con `enableGitInfo`, la fecha puede salir del último commit de cada archivo. Para que funcione en CI, hace falta clonar el historial completo con `fetch-depth: 0`, ya que de lo contrario todas las páginas tendrán la misma fecha.

## Sitemap y RSS

El sitemap ayuda a descubrir páginas. Solo debe contener URLs canónicas e indexables, y Hugo lo genera automáticamente. Declárala en `robots.txt`:

```text
User-agent: *
Allow: /

Sitemap: https://ejemplo.com/sitemap.xml
```

Mantén también el feed RSS. Sigue siendo la forma en que muchos desarrolladores siguen blogs, además de un medio para que tu contenido llegue a los lectores sin depender de un algoritmo.

## Validarlo en CI

Es fácil romper estas cosas al cambiar una plantilla, y no se nota hasta semanas más tarde. Un script que analice el HTML generado cuesta poco, y lo comprueba en cada despliegue:

```python
from html.parser import HTMLParser
from pathlib import Path

class Pagina(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1 = 0
        self.canonicas = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicas.append(attrs.get("href"))

for ruta in Path("public").rglob("*.html"):
    pagina = Pagina()
    pagina.feed(ruta.read_text(encoding="utf-8"))
    assert pagina.h1 == 1, f"Debe haber un h1: {ruta}"
    assert len(pagina.canonicas) == 1, f"Debe haber una canónica: {ruta}"
```

Puedes ampliarlo con títulos duplicados, enlaces rotos internos, imágenes sin `alt` y coherencia entre sitemap y páginas. Sin dependencias, y falla antes de publicar.

## Rendimiento y accesibilidad

Un sitio estático ya parte con ventaja. Cuida las imágenes con `width`, `height` y `srcset`, para evitar saltos y descargas grandes. Y usa HTML semántico, que ayuda a lectores de pantalla y a buscadores.

## Lo que más importa

Lo técnico es solo la base. Después de eso, lo que importa es lo que escribes: contar algo con experiencia propia, resolver un problema concreto y hacerlo mejor que lo que ya existe. Google es explícito en que penaliza publicar muchas páginas con poco valor añadido, sea cual sea la forma de producirlas, y que valora los contenidos que demuestran experiencia real. Mide con Search Console qué busca la gente y qué artículos funcionan, y dedica tu esfuerzo a mejorar esos.

## Referencias

- [Datos estructurados de artículos](https://developers.google.com/search/docs/appearance/structured-data/article)
- [Guía de contenido útil de Google](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Consolidar URLs duplicadas](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
