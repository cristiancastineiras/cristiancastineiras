---
title: "uv: gestiona proyectos y entornos de Python con una sola herramienta"
seoTitle: "uv: gestor de proyectos para Python"
description: "Cómo usar uv para crear proyectos, gestionar dependencias con lockfile, instalar versiones de Python, ejecutar scripts con dependencias y simplificar CI y Docker."
date: 2025-12-11
tags: ["Python", "Herramientas", "CI/CD"]
---

Trabajar con Python solía suponer combinar varias herramientas: `pyenv` para la versión, `venv` para el entorno, `pip` para instalar, `pip-tools` o Poetry para el lockfile, y `pipx` para las utilidades. `uv`, escrito en Rust, las sustituye con un solo comando y es muchísimo más rápido.

## Un proyecto nuevo

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

uv init informes
cd informes
uv add httpx pydantic
uv add --dev pytest ruff
uv run python main.py
```

No hay que crear ni activar ningún entorno. `uv run` crea `.venv` si no existe, comprueba que todo coincide con el lockfile y ejecuta el comando.

Esto genera dos archivos:

- **`pyproject.toml`**: las dependencias que has pedido.
- **`uv.lock`**: las versiones exactas de todo, multiplataforma. Va a Git.

```toml
[project]
name = "informes"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "httpx>=0.28",
    "pydantic>=2.10",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "ruff>=0.8",
]
```

## Versiones de Python

```bash
uv python install 3.14
uv python pin 3.14   # crea .python-version
```

uv descarga una compilación independiente, sin depender de lo que tengas en el sistema, y sin afectarlo. Todo el equipo usa la misma versión, y ya no tendrás que explicar cómo instalar `pyenv`.

## Dependencias

```bash
uv add "fastapi>=0.115"       # añade y bloquea
uv remove httpx               # elimina
uv lock --upgrade-package pydantic   # actualiza solo una
uv tree                       # muestra el árbol
```

Para reproducir el entorno en otra máquina:

```bash
uv sync
```

Instala exactamente lo que dice el lockfile, y elimina lo que sobra.

## Scripts con sus dependencias

Es una de sus mejores funciones: un único archivo que declara lo que necesita. Perfecto para automatizaciones, sin necesidad de un proyecto:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = ["httpx"]
# ///
import httpx

respuesta = httpx.get("https://api.github.com/repos/astral-sh/uv")
print(respuesta.json()["stargazers_count"])
```

```bash
chmod +x estrellas.py
./estrellas.py
```

uv crea un entorno temporal en caché. Este formato es el estándar PEP 723, de modo que otras herramientas también lo entienden.

## Herramientas de línea de comandos

```bash
uvx ruff check .           # ejecuta sin instalar
uv tool install pre-commit # instala de forma global y aislada
```

## En CI

```yaml
steps:
  - uses: actions/checkout@v4

  - uses: astral-sh/setup-uv@v6
    with:
      enable-cache: true

  - run: uv sync --locked

  - run: uv run ruff check .

  - run: uv run pytest
```

`--locked` hace que falle si el lockfile no corresponde con `pyproject.toml`, lo que detecta a quienes olvidaron actualizarlo.

## En Docker

```dockerfile
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

WORKDIR /app

# Primero, las dependencias: capa reutilizable
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Después, el código
COPY . .
RUN uv sync --locked --no-dev

USER 1000:1000
CMD ["/app/.venv/bin/python", "-m", "informes"]
```

Sigue el mismo principio de capas que en cualquier Dockerfile: lo que cambia menos va primero.

## Migrar

Desde un `requirements.txt`:

```bash
uv init --bare
uv add -r requirements.txt
```

Si no quieres cambiar tu forma de trabajar, `uv pip` es compatible con `pip`, y te da la velocidad sin más cambios:

```bash
uv pip install -r requirements.txt
```

Revisa que las versiones resueltas son las esperadas, y ejecuta tus pruebas antes de cerrar la migración.

## Algunas salvedades

- **Empresa detrás de un proxy**: configura tu índice interno en `pyproject.toml` o con variables de entorno.
- **Seguridad**: sigue siendo código de terceros. Revisa los cambios en `uv.lock`, y considera la opción `exclude-newer` para evitar versiones publicadas hace muy poco.
- **Proyecto joven**: el desarrollo es muy activo, con cambios frecuentes. Fija la versión en CI para evitar sorpresas.

## Referencias

- [Documentación de uv](https://docs.astral.sh/uv/)
- [PEP 723: metadatos en scripts](https://peps.python.org/pep-0723/)
