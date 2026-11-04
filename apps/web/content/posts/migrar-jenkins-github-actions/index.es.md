---
title: "Migrar de Jenkins a GitHub Actions: qué cambia y qué conviene planificar"
seoTitle: "Migrar de Jenkins a GitHub Actions"
description: "Cómo planificar una migración de Jenkins a GitHub Actions: equivalencias entre conceptos, ejecutores propios, credenciales y una estrategia por fases sin grandes cortes."
date: 2026-09-21
tags: ["Jenkins", "GitHub Actions", "CI/CD"]
---

Migrar de Jenkins a GitHub Actions no consiste en traducir sintaxis. Hay que decidir qué se mantiene, qué se elimina y dónde se ejecuta el trabajo. Y también merece la pena preguntarse si hay un motivo de peso: un Jenkins bien mantenido no es un problema por sí mismo.

## Antes de nada: ¿por qué migrar?

Razones que suelen justificarlo:

- el código ya está en GitHub, y quieres integrar el CI en los pull requests;
- mantener el controlador, los plugins y los agentes requiere demasiado tiempo;
- quieres que cada equipo sea autónomo con sus workflows.

Razones para pensárselo:

- despliegues en redes internas o con hardware especial, que requerirán ejecutores propios igualmente;
- bibliotecas compartidas muy elaboradas;
- restricciones de cumplimiento sobre dónde se ejecuta el código.

## Equivalencias

| Jenkins | GitHub Actions |
|---|---|
| `Jenkinsfile` | `.github/workflows/*.yml` |
| Agente | Ejecutor (*runner*) |
| Stage | Job, o grupo de pasos |
| `parallel` | Jobs independientes o `matrix` |
| Shared Library | Workflows reutilizables y acciones compuestas |
| Credentials | Secrets, variables y OIDC |
| `input` | Entornos con revisores |
| `when { branch 'main' }` | `if:` o filtro en `on:` |
| Plugin | Acción |

La mayor diferencia conceptual es que los jobs no comparten sistema de archivos. Cada job empieza en un ejecutor limpio, por lo que los archivos entre jobs deben pasarse por artefactos.

## Una traducción

```groovy
pipeline {
    agent { docker { image 'mcr.microsoft.com/dotnet/sdk:10.0' } }
    stages {
        stage('Compilar') {
            steps { sh 'dotnet build -c Release' }
        }
        stage('Probar') {
            steps { sh 'dotnet test -c Release --no-build' }
        }
    }
}
```

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-24.04
    container: mcr.microsoft.com/dotnet/sdk:10.0
    steps:
      - uses: actions/checkout@v4
      - run: dotnet build -c Release
      - run: dotnet test -c Release --no-build
```

GitHub incluye un *importador de Actions* que puede automatizar la parte mecánica y dar una primera idea del esfuerzo. Úsalo como punto de partida, no como resultado definitivo: un pipeline convertido suele conservar hábitos que ya no tienen sentido.

## Bibliotecas compartidas

Un flujo completo se convierte en un workflow reutilizable:

```yaml
# empresa/ci/.github/workflows/dotnet.yml
on:
  workflow_call:
    inputs:
      dotnet-version:
        type: string
        default: "10.0.x"

jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: ${{ inputs.dotnet-version }}
      - run: dotnet test -c Release
```

```yaml
jobs:
  ci:
    uses: empresa/ci/.github/workflows/dotnet.yml@v2
```

Los pasos que se repiten, sin ser un flujo completo, encajan en acciones compuestas. Aprovecha para simplificar: es posible que parte de esa biblioteca exista solo por los límites de Jenkins.

## Agentes y red

Lo más complicado suele ser el acceso. Si tus pipelines despliegan en servidores internos, un ejecutor alojado por GitHub no llegará hasta ellos. Tienes dos opciones:

- **Ejecutores propios**, dentro de tu red. Usa efímeros, un trabajo por máquina. Actions Runner Controller permite levantarlos en Kubernetes. No los uses con pull requests de forks, porque ejecutarían código de cualquiera dentro de tu red.
- **Empujar desde fuera**, con OIDC hacia la nube, si es lo que hay al otro lado.

## Credenciales

Es una oportunidad para limpiar. Haz inventario de las credenciales de Jenkins, elimina las que nadie use, y pasa a OIDC las que se puedan. Las credenciales de Jenkins están cifradas y no se pueden copiar sin más, de modo que muchas tendrán que rotarse. Hazlo aprovechando la migración.

## Lo que se suele olvidar

- **Disparadores programados**: `cron` en GitHub es en UTC, y puede sufrir retrasos.
- **Paso de artefactos**: Jenkins suele conservar archivos en un disco compartido.
- **Notificaciones**: correo, Slack o Teams, y a quién llegan los fallos.
- **Consumo**: los ejecutores alojados se cobran por tiempo en repositorios privados, y una matriz puede disparar la factura.
- **Límites**: tiempo por trabajo, concurrencia y tamaño de cachés.
- **Auditoría**: dónde queda registrado quién aprobó un despliegue.
- **Seguridad**: revisa [cómo proteger tus workflows]({{< relref "/posts/github-actions-seguridad-sha" >}}) desde el principio. Las acciones de terceros son el equivalente a los plugins.

## Una migración por fases

1. **Inventario**: trabajos, dependencias y cuáles se siguen usando. Muchos se pueden eliminar.
2. **Piloto**: un proyecto representativo, ni el más fácil ni el más crítico.
3. **Ejecución en paralelo**: ambos sistemas durante un tiempo, comparando resultados, solo en lo que no despliega.
4. **Cambio de los despliegues**, proyecto a proyecto, con vuelta atrás posible.
5. **Apagar**: deja Jenkins en modo de solo lectura, y mantenlo unas semanas antes de retirarlo.

No olvides la última parte. Dos sistemas de CI a largo plazo son más costosos que cualquiera de ellos. Guarda también el historial que necesites por requisitos de auditoría antes de apagarlo.

## Referencias

- [Migrar de Jenkins a GitHub Actions](https://docs.github.com/actions/migrating-to-github-actions/manually-migrating-to-github-actions/migrating-from-jenkins-to-github-actions)
- [Workflows reutilizables](https://docs.github.com/actions/sharing-automations/reusing-workflows)
- [Actions Runner Controller](https://docs.github.com/actions/hosting-your-own-runners/managing-self-hosted-runners-with-actions-runner-controller)
