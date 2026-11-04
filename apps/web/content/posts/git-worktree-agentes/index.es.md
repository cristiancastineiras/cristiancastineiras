---
title: "git worktree: varias ramas a la vez, también para agentes de IA"
seoTitle: "git worktree para varias tareas a la vez"
description: "Cómo usar git worktree para trabajar en varias ramas a la vez sin clonar ni hacer stash, y cómo aprovecharlo para aislar agentes de programación en paralelo."
date: 2026-02-05
tags: ["Git", "Productividad", "Agentes"]
---

Estás a mitad de una funcionalidad, y llega un error urgente. Las opciones habituales son `git stash`, un commit temporal o clonar otra vez el repositorio. `git worktree` ofrece algo mejor: varios directorios de trabajo a partir de un mismo repositorio, cada uno en su rama.

## Uso básico

```bash
# Crea un directorio con una rama nueva
git worktree add ../proyecto-arreglo -b arreglo/login

# O con una rama que ya existe
git worktree add ../proyecto-revision feature/pagos
```

Ahora tienes dos carpetas, cada una con su rama. Ambas comparten un mismo `.git`, por lo que los commits y las ramas de una están disponibles en la otra de forma inmediata, sin hacer ningún `fetch` ni `push`.

```bash
git worktree list
```

Cuando termines:

```bash
git worktree remove ../proyecto-arreglo
```

## Frente a clonar

- **Menos espacio**: el historial solo existe una vez.
- **Sincronía**: una rama creada en uno se ve en los demás.
- **Una única configuración** del repositorio y de sus remotos.

Una restricción útil: la misma rama no puede estar activa en dos worktrees a la vez. Te evita confusiones, porque un commit en una carpeta dejaría a la otra desfasada sin que lo notes.

## Lo que no se comparte

Cada worktree es un directorio limpio. Lo que no está bajo control de versiones no aparece en él:

- `node_modules` y `bin/obj`;
- archivos `.env` y secretos locales;
- bases de datos locales;
- cachés de compilación.

Eso significa que hay que instalar dependencias en cada uno. pnpm es especialmente adecuado, porque reutiliza un almacén global de paquetes, de forma que la instalación es rápida y apenas ocupa espacio:

```bash
cd ../proyecto-arreglo
pnpm install --frozen-lockfile
cp ../proyecto/.env .env
```

## Los puertos

Si dos copias arrancan a la vez, chocan por los puertos. Vite busca automáticamente el siguiente disponible, a menos que lo fijes. ASP.NET Core se puede configurar con variables de entorno, por lo que puedes darle a cada copia su propio puerto:

```bash
ASPNETCORE_URLS=http://localhost:5101 dotnet run
```

Si usas Docker Compose, el nombre del proyecto viene de la carpeta, de manera que los contenedores no se pisan, aunque los puertos publicados sí. Puedes definirlos por variable de entorno en un `.env` local:

```yaml
services:
  db:
    image: postgres:18
    ports:
      - "${DB_PUERTO:-5432}:5432"
```

## Agentes de programación en paralelo

Aquí es donde `worktree` ha cobrado una nueva importancia. Un agente que trabaja en una tarea modifica archivos, compila y ejecuta pruebas. Dos agentes en el mismo directorio se pisarían, y uno también podría interferir contigo.

Con un worktree por tarea, el problema desaparece:

```bash
git worktree add ../tareas/validacion -b agente/validacion
git worktree add ../tareas/rendimiento -b agente/rendimiento
```

Cada agente tiene su rama y su carpeta. Tú puedes seguir trabajando en la tuya. Al terminar, revisas cada rama como cualquier pull request, y si algo no te convence, la eliminas sin que afecte al resto.

Algunos consejos, para que esto funcione de verdad:

- **Tareas independientes**: si dos agentes tocan los mismos archivos, tendrás conflictos al integrar. Divide por módulos.
- **Revisa**: en paralelo, la limitación suele ser tu capacidad de revisión. Tres ramas a la vez no sirven de nada si no puedes leerlas bien.
- **Comprobación automática**: que cada agente ejecute pruebas y linter antes de darse por terminado.
- **Pocas a la vez**: empieza con dos, y sube si el resultado compensa.

Hay herramientas de agentes que ya crean y limpian worktrees automáticamente. Conviene entender lo que hacen por debajo para saber qué ocurre si algo se queda a medias.

## Mantener limpio

Si borras una carpeta a mano, Git sigue registrándola:

```bash
git worktree prune
```

Y si quieres quitar las ramas ya fusionadas:

```bash
git branch --merged main | grep -v "main" | xargs -r git branch -d
```

## Revisar pull requests

Otro uso práctico: revisar el pull request de otra persona sin interrumpir tu trabajo. Crea un worktree, ejecuta la aplicación y pruébala de verdad, lo que suele revelar mucho más que leer el diff:

```bash
git fetch origin pull/123/head:pr-123
git worktree add ../revision-123 pr-123
```

## Referencias

- [git-worktree](https://git-scm.com/docs/git-worktree)
