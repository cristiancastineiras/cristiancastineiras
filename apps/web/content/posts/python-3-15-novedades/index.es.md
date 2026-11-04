---
title: "Python 3.15: lazy imports, frozendict y otras novedades prácticas"
seoTitle: "Novedades de Python 3.15"
description: "Lo más útil de Python 3.15: importaciones diferidas con lazy, frozendict, UTF-8 por defecto, desempaquetado en comprensiones, Tachyon y qué comprobar antes de actualizar."
date: 2026-10-22
tags: ["Python"]
---

Python 3.15 se publicó el 9 de octubre de 2026. Trae varias novedades que resuelven molestias reales, y un cambio de comportamiento que conviene revisar antes de actualizar. Esto es lo que yo miraría primero.

## Importaciones diferidas

Muchas herramientas tardan en arrancar porque importan módulos que quizá ni van a usar. La solución habitual era mover los `import` dentro de las funciones. El PEP 810 añade una forma explícita:

```python
lazy import json
lazy from pathlib import Path

print("Arrancando...")  # json y pathlib aún no se han importado

datos = json.loads('{"clave": "valor"}')  # aquí se importa json
ruta = Path(".")                          # aquí se importa pathlib
```

El módulo se carga la primera vez que se usa. Algunos límites:

- `lazy` solo se permite a nivel de módulo;
- `lazy from modulo import *` es un error de sintaxis;
- un error de importación aparecerá al usar el módulo, no al arrancar.

Si tu código debe seguir funcionando en versiones anteriores, hay otra forma, que estas ignoran sin más:

```python
__lazy_modules__ = ["json", "pathlib"]

import json   # diferido en 3.15
import os     # normal
```

También se puede activar de forma global con `-X lazy_imports=all`, aunque yo lo probaría con cuidado, porque hay módulos que dependen de ejecutar código al importarse. Mide con `python -X importtime` dónde se va el tiempo y empieza por ahí.

## `frozendict`

Era una ausencia llamativa: ya existían `frozenset` y `tuple`, pero no un diccionario inmutable:

```python
>>> a = frozendict(x=1, y=2)
>>> a["z"] = 3
TypeError: 'frozendict' object does not support item assignment
>>> b = frozendict(y=2, x=1)
>>> hash(a) == hash(b)
True
```

Es hashable si sus valores lo son, de modo que puede usarse como clave de otro diccionario o en un `set`, y sirve para configuraciones o valores por defecto seguros.

Una advertencia: no es subclase de `dict`. El código que comprueba `isinstance(x, dict)` no lo reconocerá. La documentación recomienda usar `collections.abc.Mapping`, algo que ya era buena práctica.

## UTF-8 por defecto

Este es el cambio con más posibilidades de afectar a código existente. Con el PEP 686, `open()` usa UTF-8 si no se indica otra codificación, en lugar de deducirla del sistema:

```python
with open("datos.txt") as archivo:  # UTF-8 en todas las plataformas
    contenido = archivo.read()
```

Es una mejora enorme para código multiplataforma, ya que muchos errores en Windows venían de ahí. Pero si tienes archivos en `cp1252` que se leían sin indicar la codificación, ahora fallarán, o mostrarán caracteres erróneos.

Para volver temporalmente al comportamiento anterior, usa `PYTHONUTF8=0` o `-X utf8=0`. La solución duradera es indicar siempre `encoding=`, y `python -X warn_default_encoding` ayuda a encontrar los casos que faltan, también en versiones anteriores.

## Desempaquetado en comprensiones

Aplanar una lista de listas requería recordar el orden de los `for`:

```python
listas = [[1, 2], [3, 4], [5]]

[x for lista in listas for x in lista]   # antes
[*lista for lista in listas]             # ahora

diccionarios = [{"a": 1}, {"b": 2}, {"a": 3}]
{**d for d in diccionarios}              # {'a': 3, 'b': 2}
```

## `sentinel`

El tipo integrado `sentinel` (PEP 661) crea valores únicos, para distinguir cuándo no se ha pasado un argumento en los casos en que `None` ya es un valor válido. Sustituye al habitual `_FALTA = object()`, y además tiene una representación legible y se comporta bien con las herramientas de tipos.

## Tachyon: perfilado sin modificar nada

El nuevo paquete `profiling` incluye un perfilador estadístico de alta frecuencia, que se puede conectar a un proceso en ejecución sin reiniciarlo. Muestrea desde fuera, con un coste muy pequeño, lo que lo hace apto para investigar problemas en producción.

Puede generar gráficos de llama y otros formatos, y dispone de modos para analizar tiempo real, CPU, GIL o excepciones. El módulo antiguo `profile`, escrito solo en Python, queda obsoleto y está previsto retirarlo en 3.17.

## JIT y ejecución sin GIL

El compilador JIT cubre muchas más operaciones que en 3.14, aunque sigue siendo experimental y está desactivado por defecto. La versión sin GIL avanza, y ahora ofrece una ABI estable (`abi3t`), que permitirá a las extensiones en C publicar un único paquete para esa variante, una vez que las herramientas de compilación lo soporten.

## Antes de actualizar

1. Revisa que tus dependencias publiquen paquetes para 3.15, sobre todo las que tengan extensiones nativas.
2. Ejecuta tus pruebas con `-X warn_default_encoding` en tu versión actual.
3. Añade 3.15 a la matriz de CI, sin hacerla obligatoria todavía.
4. Lee la sección de la documentación sobre lo eliminado y los cambios de comportamiento.
5. Espera a una o dos versiones de corrección si no necesitas nada con urgencia.

Con `uv`, probarlo es muy sencillo:

```bash
uv python install 3.15
uv run --python 3.15 pytest
```

## Referencias

- [Novedades de Python 3.15](https://docs.python.org/3/whatsnew/3.15.html)
- [PEP 810: importaciones diferidas explícitas](https://peps.python.org/pep-0810/)
- [PEP 686: UTF-8 por defecto](https://peps.python.org/pep-0686/)
