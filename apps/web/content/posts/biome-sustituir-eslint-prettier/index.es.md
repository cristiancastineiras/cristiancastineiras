---
title: "Biome: linter y formateador en una sola herramienta, ¿merece la pena cambiar?"
seoTitle: "Biome frente a ESLint y Prettier"
description: "Qué ofrece Biome frente a ESLint y Prettier, cómo migrar la configuración en un monorepo y en qué casos conviene mantener ESLint por sus plugins específicos."
date: 2025-11-20
tags: ["TypeScript", "Herramientas", "Monorepo"]
---

La configuración habitual de un proyecto JavaScript implica ESLint, Prettier, varios plugins y un paquete para evitar que los dos primeros se peleen. Biome reúne el linter y el formateador en un único binario escrito en Rust, sin apenas dependencias. Veamos si el cambio compensa.

## Qué aporta

- **Velocidad**: al estar escrito en Rust y procesar archivos en paralelo, es mucho más rápido que ESLint y Prettier juntos, algo que se nota en repositorios grandes y en los ganchos de Git.
- **Una dependencia**: menos versiones que alinear y menos superficie para la cadena de suministro.
- **Un único archivo de configuración**, que no necesita plugins para TypeScript ni JSX.
- **Compatibilidad**: su formato es muy parecido al de Prettier.

## Empezar

```bash
pnpm add -D -E @biomejs/biome
pnpm biome init
```

El `-E` fija la versión exacta. Es lo recomendado, porque un cambio de versión del formateador puede tocar muchos archivos, y debe ser una decisión consciente.

Una configuración mínima:

```json
{
  "formatter": {
    "indentStyle": "space",
    "lineWidth": 100
  },
  "linter": {
    "rules": {
      "recommended": true
    }
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "double"
    }
  },
  "vcs": {
    "enabled": true,
    "clientKind": "git",
    "useIgnoreFile": true
  }
}
```

Con `useIgnoreFile`, respeta tu `.gitignore`, de modo que no analizará `dist` ni otros archivos generados.

```json
{
  "scripts": {
    "check": "biome check .",
    "check:fix": "biome check --write ."
  }
}
```

`biome check` ejecuta el linter, el formateador y la organización de importaciones en un solo comando.

## Migrar desde ESLint y Prettier

Biome puede leer tu configuración actual:

```bash
pnpm biome migrate eslint --write
pnpm biome migrate prettier --write
```

Traduce las reglas que tienen equivalencia, y te dirá cuáles no. Después:

1. aplica el formato en un commit aislado, sin ningún cambio funcional;
2. añade ese commit a `.git-blame-ignore-revs`, para no ensuciar el historial;
3. elimina las dependencias antiguas y sus archivos de configuración;
4. actualiza CI y la configuración del editor.

```text
# .git-blame-ignore-revs
a1b2c3d4e5f6
```

## En CI

```yaml
- run: pnpm biome ci .
```

`biome ci` es la versión de solo lectura, pensada para integración continua. Falla si algo no cumple las reglas, sin modificar nada.

## En un monorepo

Coloca la configuración en la raíz del repositorio, con ajustes específicos por paquete si hacen falta. Un archivo anidado puede heredar de la raíz:

```json
{
  "extends": "//",
  "linter": {
    "rules": {
      "suspicious": {
        "noConsole": "off"
      }
    }
  }
}
```

La sintaxis `"extends": "//"` corresponde a la raíz, disponible desde Biome 2.

## Cuándo seguir con ESLint

La principal limitación es el ecosistema de plugins. Revisa si dependes de:

- **Reglas basadas en tipos muy concretas**, como algunas de `typescript-eslint`. Biome 2 incluye reglas con información de tipos, como `noFloatingPromises`, aunque su cobertura es menor.
- **Plugins específicos**, como reglas de TanStack Query, de Storybook o de Testing Library.
- **Reglas propias** escritas para tu organización. Biome admite plugins GritQL, pero la API es muy diferente.

Una opción intermedia es válida: Biome para formatear y para la mayoría de las reglas, y ESLint solo con los pocos plugins que no se pueden sustituir. Pierdes parte de la simplicidad, pero mantienes lo que te importa.

## Mi criterio

En un proyecto nuevo, empezaría con Biome. En uno existente, solo si los tiempos de lint son un problema real o la configuración de ESLint es difícil de mantener, y después de comprobar que no pierdes reglas importantes. Cambiar de herramienta no aporta mucho por sí solo.

## Referencias

- [Biome](https://biomejs.dev/)
- [Migrar desde ESLint y Prettier](https://biomejs.dev/guides/migrate-eslint-prettier/)
