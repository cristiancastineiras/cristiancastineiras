---
title: "Internacionalizar una aplicación React con i18next sin dejar deuda técnica"
seoTitle: "i18n en React con react-i18next"
description: "Cómo organizar traducciones con react-i18next: claves con tipos, plurales, carga diferida por idioma, formato de fechas y los errores que más cuesta corregir después."
date: 2025-08-28
tags: ["React", "i18n", "TypeScript"]
---

Traducir una aplicación parece una tarea de buscar y reemplazar textos. Lo complicado son los plurales, el orden de las palabras, las fechas, los textos que crecen un 40 % y las claves que nadie sabe si se siguen usando. Unas pocas decisiones al principio evitan mucho trabajo.

## Configuración

```bash
pnpm add i18next react-i18next i18next-resources-to-backend
```

```ts
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import resourcesToBackend from "i18next-resources-to-backend";

i18n
  .use(initReactI18next)
  .use(
    resourcesToBackend(
      (idioma: string, espacio: string) =>
        import(`./locales/${idioma}/${espacio}.json`),
    ),
  )
  .init({
    fallbackLng: "es",
    supportedLngs: ["es", "en", "eu"],
    defaultNS: "comun",
    interpolation: { escapeValue: false },
  });
```

`escapeValue: false` es correcto en React, que ya escapa los valores. Con `import()` dinámico, solo se descarga el idioma que se necesita.

## Organizar por funcionalidad

Un único archivo enorme acaba siendo inmanejable, y se descarga completo:

```text
locales/
├── es/
│   ├── comun.json
│   ├── pedidos.json
│   └── clientes.json
└── en/
    ├── comun.json
    ├── pedidos.json
    └── clientes.json
```

```tsx
function ListaPedidos() {
  const { t } = useTranslation("pedidos");
  return <h1>{t("titulo")}</h1>;
}
```

## Claves con tipos

Sin esto, una errata en una clave solo se descubre en ejecución. Con una declaración de tipos, TypeScript la detecta:

```ts
// i18next.d.ts
import "i18next";
import type comun from "./locales/es/comun.json";
import type pedidos from "./locales/es/pedidos.json";

declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "comun";
    resources: {
      comun: typeof comun;
      pedidos: typeof pedidos;
    };
  }
}
```

## Plurales: nunca a mano

Cada idioma tiene sus reglas. Algunos tienen dos formas; otros, más. Por eso no se debe resolver con un `if`:

```json
{
  "resultados_one": "{{count}} resultado",
  "resultados_other": "{{count}} resultados"
}
```

```tsx
t("resultados", { count: total });
```

i18next elige el sufijo adecuado con `Intl.PluralRules`, de modo que cada idioma solo declara las formas que necesita.

## No construir frases por partes

Es el error más caro de corregir, ya que el orden de las palabras cambia entre idiomas:

```tsx
// Mal: no se puede reordenar al traducir
<p>{t("bienvenida")} {nombre}, {t("tienes")} {total} {t("mensajes")}</p>
```

```json
{
  "resumen_one": "Hola {{nombre}}, tienes {{count}} mensaje",
  "resumen_other": "Hola {{nombre}}, tienes {{count}} mensajes"
}
```

Cuando la frase contiene un enlace o una negrita, usa el componente `Trans`:

```tsx
<Trans i18nKey="aceptar" components={{ enlace: <a href="/terminos" /> }} />
```

```json
{
  "aceptar": "Acepto los <enlace>términos y condiciones</enlace>"
}
```

## Fechas y números

No guardes el formato en las traducciones. Usa `Intl`, en el idioma activo:

```tsx
const { i18n } = useTranslation();

const fecha = new Intl.DateTimeFormat(i18n.language, {
  dateStyle: "long",
}).format(new Date(pedido.fecha));
```

## Atributos del documento

Actualiza `lang` al cambiar de idioma: los lectores de pantalla lo usan para elegir la pronunciación, y los navegadores para traducir o dividir palabras.

```ts
i18n.on("languageChanged", (idioma) => {
  document.documentElement.lang = idioma;
});
```

## Maquetación flexible

Los textos en alemán o en euskera pueden ser mucho más largos que en español. Evita los anchos fijos en botones y menús. Para los idiomas que se escriben de derecha a izquierda, usa propiedades lógicas de CSS, como `margin-inline-start`, en vez de `margin-left`. Si las adoptas desde el principio, no cuesta nada, y añadir ese soporte después es costoso.

## Mantener las traducciones

- **Claves sin usar y claves que faltan**: `i18next-parser` u otras herramientas extraen las claves del código y lo detectan. Añádelo a CI.
- **Pseudolocalización**: un idioma falso con textos alargados y acentuados revela lo que sigue sin traducir y lo que se rompe.
- **Contexto para quien traduce**: «Cerrar» puede referirse a una ventana o a una cuenta. Las claves descriptivas y los comentarios evitan errores.

## Referencias

- [react-i18next](https://react.i18next.com/)
- [Plurales en i18next](https://www.i18next.com/translation-function/plurals)
