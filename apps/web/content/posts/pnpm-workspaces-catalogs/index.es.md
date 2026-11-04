---
title: "Catálogos de pnpm: una sola versión de cada dependencia en tu monorepo"
seoTitle: "Catálogos de pnpm en un monorepo"
description: "Cómo usar workspaces y catálogos de pnpm para alinear versiones entre paquetes, evitar copias duplicadas de React y simplificar las actualizaciones."
date: 2025-06-19
tags: ["pnpm", "Monorepo", "Node.js"]
---

En un monorepo con diez paquetes, cada `package.json` declara sus versiones de React, TypeScript o Vite. Con el tiempo se desalinean, y aparecen tipos incompatibles o dos copias de React en el mismo bundle, con el clásico error de hooks no válidos.

Los catálogos de pnpm definen cada versión en un único lugar.

## Definir un catálogo

```yaml
# pnpm-workspace.yaml
packages:
  - "apps/*"
  - "packages/*"

catalog:
  react: ^19.1.0
  react-dom: ^19.1.0
  typescript: ~5.8.3
  vite: ^6.3.0
  vitest: ^3.1.0
```

## Usarlo

```json
{
  "name": "@empresa/web",
  "dependencies": {
    "@empresa/ui": "workspace:*",
    "react": "catalog:",
    "react-dom": "catalog:"
  },
  "devDependencies": {
    "typescript": "catalog:",
    "vite": "catalog:"
  }
}
```

Actualizar React en todos los paquetes se convierte en cambiar una línea, y el diff del pull request lo refleja con claridad.

Al publicar un paquete, pnpm sustituye `catalog:` por la versión real, igual que hace con `workspace:*`.

## Catálogos con nombre

A veces tienes que convivir con dos versiones mayores durante una migración:

```yaml
catalogs:
  react18:
    react: ^18.3.1
    react-dom: ^18.3.1
  react19:
    react: ^19.1.0
    react-dom: ^19.1.0
```

```json
{
  "dependencies": {
    "react": "catalog:react18"
  }
}
```

Migras un paquete cambiando `react18` por `react19`, y al terminar eliminas el catálogo temporal. Que la excepción sea explícita ayuda a que no se quede para siempre.

## Imponer el uso

Por defecto, nada impide que alguien añada una versión suelta. Se puede forzar:

```yaml
catalogMode: strict
```

Con `strict`, `pnpm add` solo permite versiones del catálogo. `prefer` usa el catálogo si la dependencia está presente, y `manual` es el comportamiento predeterminado. Esta opción requiere una versión reciente de pnpm, así que compruébala en la documentación de la tuya.

## Dependencias entre paquetes

Para los paquetes internos, usa siempre el protocolo `workspace`:

```json
{
  "dependencies": {
    "@empresa/ui": "workspace:*"
  }
}
```

Garantiza que se usa la copia local, y falla si el paquete no existe en el workspace. Nunca descargará una versión del registro por accidente.

## Dependencias entre pares

Un paquete de componentes debe declarar React como `peerDependency`:

```json
{
  "name": "@empresa/ui",
  "peerDependencies": {
    "react": "^19.0.0"
  },
  "devDependencies": {
    "react": "catalog:"
  }
}
```

Si lo declaras como dependencia normal, cada aplicación podría acabar con su propia copia.

## Comprobar que no hay duplicados

```bash
pnpm why react
pnpm list react --recursive --depth 0
```

Si aparecen varias versiones de una dependencia transitiva, `pnpm dedupe` intenta consolidarlas. Para forzar una versión, por ejemplo por un parche de seguridad, usa `overrides`:

```yaml
overrides:
  "lodash@<4.17.21": "^4.17.21"
```

Cada `override` merece un comentario con el motivo, y eliminarlo cuando deje de ser necesario. Si no, acaba bloqueando actualizaciones sin que nadie recuerde por qué.

## Comandos del workspace

```bash
# Instalar en un paquete concreto
pnpm add zod --filter @empresa/web

# Ejecutar en un paquete y sus dependencias
pnpm --filter "@empresa/web..." build

# Herramientas del repositorio en la raíz
pnpm add -Dw turbo
```

En CI, instala siempre con el lockfile congelado:

```bash
pnpm install --frozen-lockfile
```

Es el comportamiento predeterminado en un entorno de CI, pero hacerlo explícito no cuesta nada, y falla si alguien olvidó actualizar el `pnpm-lock.yaml`.

## Y con Renovate o Dependabot

Las herramientas de actualización entienden los catálogos, y modifican `pnpm-workspace.yaml`. Revisa que tu versión lo soporte. Actualizar en un solo sitio significa también que un pull request actualiza todo el repositorio a la vez. Es más fácil de revisar, aunque todos los paquetes se verán afectados por un mismo cambio, así que necesitas un buen CI.

## Referencias

- [Catálogos de pnpm](https://pnpm.io/catalogs)
- [Workspaces de pnpm](https://pnpm.io/workspaces)
