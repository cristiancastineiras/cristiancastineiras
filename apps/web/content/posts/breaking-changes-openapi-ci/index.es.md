---
title: "Detectar cambios incompatibles de OpenAPI en CI antes de romper un cliente"
seoTitle: "Breaking changes de OpenAPI en CI"
description: "Cómo versionar el contrato OpenAPI y bloquear en GitHub Actions los pull requests que rompen a los consumidores de la API, con oasdiff y una excepción explícita."
date: 2026-05-11
tags: ["OpenAPI", "CI/CD", "GitHub Actions"]
---

Renombrar una propiedad en un DTO de C# parece un cambio pequeño. El backend compila, sus pruebas pasan y el pull request se aprueba, pero un cliente empieza a fallar cuando llega a producción.

Si la API publica un contrato OpenAPI, esa rotura se puede detectar mecánicamente en el pull request.

## La pieza previa: el contrato en el repositorio

Lo primero es tener el documento generado y versionado. En [la guía sobre OpenAPI nativo]({{< relref "/posts/openapi-nativo-scalar-aspnet-core" >}}) se explica cómo exportarlo al compilar. La idea es esta:

```text
src/Api/
└── openapi/
    └── Api.json
```

Con el archivo en Git, cualquier cambio en el contrato aparece en el diff. Eso ayuda al revisor, pero no basta: hay que distinguir qué cambios son realmente incompatibles.

## Comprobar que el contrato está al día

Si alguien cambia el código y no regenera el documento, la comparación no sirve. Primero:

```yaml
- name: Generar contrato
  run: dotnet build src/Api -c Release

- name: Contrato actualizado
  run: git diff --exit-code src/Api/openapi/Api.json
```

## Comparar con oasdiff

`oasdiff` compara dos especificaciones e identifica los cambios que rompen compatibilidad. La referencia es la rama principal:

```yaml
name: Contrato de API

on:
  pull_request:
    paths:
      - "src/Api/**"

permissions:
  contents: read

jobs:
  breaking:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Obtener el contrato base
        run: git show "origin/${GITHUB_BASE_REF}:src/Api/openapi/Api.json" > base.json

      - name: Buscar cambios incompatibles
        run: |
          docker run --rm -v "$PWD:/w" -w /w tufin/oasdiff \
            breaking base.json src/Api/openapi/Api.json --fail-on ERR
```

Con `--fail-on ERR`, el job falla si encuentra algo clasificado como incompatible, como quitar un endpoint o hacer obligatorio un parámetro. En una instalación real fijaría la imagen a una versión concreta en vez de usar la predeterminada.

## Cuando el cambio es intencionado

A veces romper es la decisión correcta. No conviene desactivar la comprobación; la excepción debe quedar registrada. Una forma sencilla es una etiqueta en el pull request:

```yaml
- name: Buscar cambios incompatibles
  if: ${{ !contains(github.event.pull_request.labels.*.name, 'breaking-change-aprobado') }}
  run: |
    docker run --rm -v "$PWD:/w" -w /w tufin/oasdiff \
      breaking base.json src/Api/openapi/Api.json --fail-on ERR
```

Quien aplique la etiqueta asume la decisión, y queda constancia. El resto del proceso sigue siendo el de siempre: avisar a los consumidores, ofrecer un periodo de migración o publicar una versión nueva.

## Qué no detecta

La herramienta solo ve lo que describe el contrato. No detecta:

- cambios de comportamiento con el mismo esquema, como un campo que antes nunca era nulo y ahora a veces lo es sin que el documento lo declare;
- validaciones o reglas de negocio más estrictas;
- errores en la propia especificación.

Por eso el resultado es tan bueno como el documento. Merece la pena declarar los tipos y los códigos de respuesta, y usar las anotaciones de nulabilidad. Si quieres ir más lejos con varios consumidores, las pruebas de contrato los representan mejor.

## Qué aporta al frontend

Si tu frontend genera un cliente a partir de este contrato, ya tienes una segunda red: al regenerarlo, TypeScript señala los usos incompatibles. La primera avisa a los consumidores que no están en tu repositorio; la segunda guía el arreglo de los que sí lo están.

## Referencias

- [oasdiff](https://github.com/oasdiff/oasdiff)
- [Especificación OpenAPI](https://spec.openapis.org/oas/latest.html)
