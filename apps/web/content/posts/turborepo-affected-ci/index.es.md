---
title: "Turborepo en CI: ejecutar solo lo afectado y aprovechar la caché"
seoTitle: "Turborepo en CI: solo lo afectado"
description: "Cómo reducir el tiempo de CI en un monorepo con Turborepo: dependencias entre tareas, --affected, caché local y remota, y los errores que producen falsos aciertos."
date: 2025-12-22
tags: ["Turborepo", "Monorepo", "CI/CD"]
---

El tiempo de CI de un monorepo crece con cada paquete si todo se ejecuta siempre. Turborepo resuelve esto con dos ideas: si una tarea tiene las mismas entradas que antes, reutiliza el resultado; y si un paquete no se ve afectado por un cambio, ni siquiera lo considera.

## Definir las tareas

```json
{
  "$schema": "https://turborepo.com/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "lint": {},
    "typecheck": {
      "dependsOn": ["^build"]
    },
    "test": {
      "dependsOn": ["^build"]
    }
  }
}
```

`^build` significa que primero se compilan las dependencias del paquete. Sin `outputs`, la caché de una compilación solo restauraría los logs, no los archivos generados, y el paso siguiente fallaría. Es uno de los errores más comunes.

## Solo lo afectado

`--affected` compara con la rama principal, y ejecuta las tareas de los paquetes cambiados y de los que dependen de ellos:

```bash
pnpm turbo run lint typecheck test build --affected
```

Requiere historial suficiente de Git para poder comparar:

```yaml
name: CI

on:
  pull_request:

jobs:
  verificar:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: pnpm/action-setup@v4

      - uses: actions/setup-node@v4
        with:
          node-version-file: ".nvmrc"
          cache: pnpm

      - run: pnpm install --frozen-lockfile

      - run: pnpm turbo run lint typecheck test build --affected
```

En GitHub Actions, Turborepo detecta la rama de base del pull request. Sin el `fetch-depth: 0`, no podría calcularlo, y ejecutaría todo como medida de seguridad.

## Caché remota

La caché local no ayuda mucho en CI, porque cada ejecución arranca en una máquina limpia. Con una caché remota, se comparten resultados entre ejecuciones y con los desarrolladores:

```yaml
env:
  TURBO_TOKEN: ${{ secrets.TURBO_TOKEN }}
  TURBO_TEAM: ${{ vars.TURBO_TEAM }}
```

Puedes usar la de Vercel, o alojar la tuya con la API abierta que documenta Turborepo. Si solo necesitas algo sencillo, también puedes guardar `.turbo/cache` con `actions/cache`, aunque es menos eficaz.

Si el resultado de una tarea puede contener datos sensibles, ten en cuenta que quedará almacenado ahí. Revisa qué declaras en `outputs`.

## Evitar falsos aciertos

Una caché que sirve un resultado incorrecto es peor que no tenerla. La causa típica son las variables de entorno que Turborepo no conoce:

```json
{
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"],
      "env": ["VITE_API_URL"]
    }
  }
}
```

Si `VITE_API_URL` afecta al resultado y no está en `env`, una compilación de preproducción podría reutilizarse en producción, con la URL equivocada. Declara todas estas variables. El modo estricto, el predeterminado, filtra las que no se declaran, lo que ayuda a detectar esos fallos.

También puedes añadir archivos globales, como una configuración común:

```json
{
  "globalDependencies": ["tsconfig.base.json"]
}
```

## Afinar las entradas

Por defecto, cualquier archivo del paquete bajo control de versiones invalida la tarea. Cambiar un `README` no debería ejecutar las pruebas otra vez:

```json
{
  "tasks": {
    "test": {
      "dependsOn": ["^build"],
      "inputs": ["$TURBO_DEFAULT$", "!**/*.md"]
    }
  }
}
```

`$TURBO_DEFAULT$` mantiene el comportamiento habitual, y solo excluye lo indicado. Con exclusiones demasiado amplias, corres el riesgo de que un cambio relevante no invalide la caché.

## Diagnosticar

```bash
# Qué se ejecutaría y por qué
pnpm turbo run build --dry-run

# Análisis de la ejecución
pnpm turbo run build --summarize
```

Si una caché nunca acierta, compara dos resúmenes para saber qué cambia. Puede ser un archivo generado en cada ejecución, una fecha en la compilación o una variable de entorno diferente.

## Cuidado con `--affected`

Lo que está fuera del grafo de paquetes no lo detecta bien. Si el cambio está en un archivo de la raíz, en una imagen de Docker o en un archivo compartido sin declarar, puede que no se ejecute nada que deba ejecutarse. Por eso, conviene una ejecución completa en la rama principal, para asegurarse de que todo sigue bien.

## Referencias

- [Configurar tareas en Turborepo](https://turborepo.com/docs/crafting-your-repository/configuring-tasks)
- [Ejecutar en CI](https://turborepo.com/docs/crafting-your-repository/constructing-ci)
- [Almacenamiento en caché remoto](https://turborepo.com/docs/core-concepts/remote-caching)
