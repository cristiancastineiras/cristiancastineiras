---
title: "git bisect: encuentra el commit que rompió algo en minutos"
seoTitle: "git bisect: encontrar un bug con Git"
description: "Cómo usar git bisect para localizar el commit que introdujo un error, cómo automatizarlo con una prueba y qué hacer con commits que no compilan."
date: 2025-05-08
tags: ["Git", "Productividad", "Testing"]
---

Algo funcionaba el mes pasado y ahora no. Hay 400 commits de por medio. Puedes leerlos uno por uno, o dejar que Git haga una búsqueda binaria: con 400 commits, bastan unas 9 comprobaciones para encontrar el culpable.

## Uso básico

```bash
git bisect start
git bisect bad                 # el commit actual falla
git bisect good v2.3.0         # esta versión funcionaba
```

Git se sitúa en un commit intermedio. Lo pruebas y le dices el resultado:

```bash
git bisect good    # funciona aquí
# o
git bisect bad     # también falla aquí
```

Repite hasta que Git te indique el primer commit con el problema:

```text
a1b2c3d is the first bad commit
commit a1b2c3d
Author: ...
    Refactoriza el cálculo de impuestos
```

Después, vuelve al punto inicial:

```bash
git bisect reset
```

## Automatizarlo

Aquí está lo mejor. Si puedes comprobar el fallo con un comando, Git lo ejecuta por ti:

```bash
git bisect start HEAD v2.3.0
git bisect run ./comprobar.sh
```

El script debe devolver:

- **0** si el commit es bueno;
- **1 a 127** si es malo, excepto 125;
- **125** si no se puede probar: Git lo salta.

Un ejemplo para .NET:

```bash
#!/bin/sh
# comprobar.sh

# Si no compila, no podemos saber nada de este commit
dotnet build -c Release > /dev/null 2>&1 || exit 125

dotnet test -c Release --no-build \
  --filter "FullyQualifiedName~CalculoImpuestosTests.Aplica_iva_reducido"
```

Ve a tomar un café. Al volver, tendrás el commit exacto.

## El script debe quedar fuera del control de versiones

Como Git cambia de commit, un script dentro del repositorio puede desaparecer o cambiar. Guárdalo fuera, o en un archivo sin seguimiento. Lo mismo ocurre con una prueba nueva que hayas escrito para reproducir el error: los commits antiguos no la tienen.

```bash
#!/bin/sh
# La prueba vive fuera del repositorio y se copia en cada paso
cp /tmp/ReproducirErrorTests.cs tests/ReproducirErrorTests.cs
dotnet test --filter ReproducirErrorTests
resultado=$?
rm tests/ReproducirErrorTests.cs
exit $resultado
```

Limpia lo que hayas copiado antes de terminar: Git se negará a cambiar de commit si hay archivos en conflicto.

## Commits que no se pueden probar

Si un commit no compila, o no se puede evaluar:

```bash
git bisect skip
```

Git elige otro cercano. Si hay muchos, al final te dará un rango de posibles culpables, en vez de uno solo. Por eso es tan valioso que cada commit de la rama principal compile y pase sus pruebas. Una estrategia de *squash* al fusionar lo facilita.

## Cuando no es un error

`bisect` sirve para cualquier cambio de comportamiento, y puedes renombrar sus términos para no confundirte:

```bash
git bisect start --term-new=lento --term-old=rapido
git bisect lento HEAD
git bisect rapido v2.3.0
```

Un ejemplo: encontrar qué commit empeoró el tiempo de respuesta o aumentó el tamaño del bundle:

```bash
#!/bin/sh
pnpm build > /dev/null 2>&1 || exit 125
tamano=$(stat -c%s dist/assets/index-*.js)
[ "$tamano" -lt 500000 ]
```

## Historias con merges

En un historial con muchos merges, puedes centrarte solo en los puntos de integración de la rama principal, lo que acelera mucho el proceso:

```bash
git bisect start --first-parent
```

Te dirá qué pull request lo introdujo. A partir de ahí, puedes revisarlo o buscar dentro de esa rama.

## Dependencias y entorno

Al saltar a un commit antiguo, las dependencias pueden ser otras. Incluye la restauración en tu script: `dotnet restore` o `pnpm install --frozen-lockfile`. Si el problema depende de la base de datos o de datos concretos, lo mejor es usar contenedores, para que cada paso parta de cero. Y si el fallo es intermitente, una mala respuesta durante la búsqueda enviará a Git en la dirección equivocada; repite la prueba varias veces en cada paso.

## Revisar lo que has hecho

```bash
git bisect log       # lo que has marcado hasta ahora
git bisect replay archivo.log  # repetir la sesión
```

Si te equivocas al marcar un paso, guarda el log, corrige la línea errónea y usa `replay` para seguir desde ahí.

## Después de encontrarlo

No basta con revertir. Una vez localizado el commit:

1. léelo para entender *por qué* lo rompió;
2. escribe una prueba que reproduzca el fallo, si no la tienes;
3. corrige y añade esa prueba para que no se repita.

## Referencias

- [git-bisect](https://git-scm.com/docs/git-bisect)
