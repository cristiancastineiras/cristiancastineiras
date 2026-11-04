---
title: "GitHub Actions para .NET: caché de NuGet, matrices y pipelines más rápidos"
seoTitle: "GitHub Actions para proyectos .NET"
description: "Un workflow de CI para .NET con caché de NuGet, restauración bloqueada, matrices de sistemas, cobertura de pruebas y consejos para reducir el tiempo de cada ejecución."
date: 2025-02-27
tags: [".NET", "GitHub Actions", "CI/CD"]
---

Un pipeline lento se acaba ignorando: la gente deja de esperar el resultado o agrupa varios cambios en un solo pull request. Con pocos ajustes se puede tener un workflow de .NET rápido y fiable.

## Un workflow de partida

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-24.04
    env:
      DOTNET_NOLOGO: true
      DOTNET_CLI_TELEMETRY_OPTOUT: true
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-dotnet@v4
        with:
          global-json-file: global.json
          cache: true
          cache-dependency-path: "**/packages.lock.json"

      - run: dotnet restore --locked-mode

      - run: dotnet build --no-restore -c Release

      - run: dotnet test --no-build -c Release --logger "trx;LogFileName=resultados.trx"
```

Algunos detalles que merecen atención:

- **`permissions: contents: read`**: el token solo tiene permisos de lectura.
- **`concurrency`**: si haces otro push, cancela la ejecución anterior de esa rama. Ahorra minutos.
- **`global-json-file`**: CI y los desarrolladores usan el mismo SDK.
- **`--no-restore` y `--no-build`**: no repiten trabajo ya hecho.

## Caché de NuGet y lockfile

La caché de `setup-dotnet` necesita un archivo de bloqueo para calcular su clave. Actívalo en `Directory.Build.props`:

```xml
<Project>
  <PropertyGroup>
    <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>
  </PropertyGroup>
</Project>
```

Genera un `packages.lock.json` en cada proyecto, que debes guardar en Git. `--locked-mode` hace que la restauración falle si no coincide con lo declarado, algo que ayuda con la reproducibilidad y también con la seguridad.

## Matrices solo donde aporten

Una matriz multiplica el consumo. Ejecutar en tres sistemas operativos cada pull request solo tiene sentido si tu código los soporta y pueden fallar de forma diferente, como una herramienta de línea de comandos:

```yaml
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu-24.04, windows-2022, macos-14]
runs-on: ${{ matrix.os }}
```

`fail-fast: false` permite ver todos los fallos en lugar de cancelar los demás al primero. Para una API que se despliega en Linux, con ejecutar en Linux suele ser suficiente. Si quieres cubrir más, deja la matriz completa para la rama principal o una ejecución nocturna.

## Resultados y cobertura

Publica los resultados como artefacto, también cuando las pruebas fallen:

```yaml
- run: dotnet test --no-build -c Release --collect:"XPlat Code Coverage" --results-directory ./resultados

- uses: actions/upload-artifact@v4
  if: ${{ !cancelled() }}
  with:
    name: resultados-pruebas
    path: ./resultados
```

La cobertura es útil para encontrar zonas sin probar. Como objetivo numérico, suele generar pruebas sin valor.

## Reducir el tiempo

Antes de optimizar, mira dónde se va el tiempo: la interfaz de Actions muestra la duración de cada paso.

1. **Separa lo rápido**: formato y compilación primero. Si falla algo básico, no tiene sentido esperar a las pruebas de integración.
2. **Filtra por rutas**: si solo cambia la documentación, no compiles nada.
3. **Ejecuta las pruebas en paralelo**: xUnit paraleliza por colección, y puedes dividir las pesadas en varios jobs.
4. **Compila en un único job y reutiliza** el resultado mediante artefactos.

```yaml
on:
  pull_request:
    paths-ignore:
      - "docs/**"
      - "**/*.md"
```

Cuidado con `paths-ignore` y las comprobaciones requeridas: si un workflow no se ejecuta, una comprobación obligatoria podría quedarse pendiente y bloquear el pull request.

## Formato en CI

```yaml
- run: dotnet format --verify-no-changes --no-restore
```

Falla si hay algo que corregir, de modo que las revisiones no tengan que ocuparse del estilo. Puede ser lento en soluciones grandes, así que quizá lo prefieras en un job aparte.

## Avisos como errores

Solo en CI, para no molestar durante el desarrollo:

```yaml
- run: dotnet build --no-restore -c Release -warnaserror
```

## Fijar versiones

`ubuntu-latest` cambia sin avisar, y un día tu pipeline falla sin que hayas tocado nada. Prefiero `ubuntu-24.04` para controlar cuándo hacer el cambio. Y para las acciones, considera fijarlas a un SHA, sobre todo si son de terceros.

## Referencias

- [Compilar y probar .NET en GitHub Actions](https://docs.github.com/actions/use-cases-and-examples/building-and-testing/building-and-testing-net)
- [actions/setup-dotnet](https://github.com/actions/setup-dotnet)
