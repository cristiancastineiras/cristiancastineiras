---
title: "Instrucciones para agentes de IA: qué poner en AGENTS.md o CLAUDE.md y qué no"
seoTitle: "Escribir AGENTS.md o CLAUDE.md"
description: "Cómo escribir instrucciones útiles para agentes de programación: comandos, convenciones y restricciones, qué debe quedar fuera y cómo mantenerlas sin que crezcan sin control."
date: 2026-05-28
tags: ["Agentes", "IA", "Productividad"]
---

Un archivo de instrucciones se carga en cada sesión con tu agente de programación, por lo que es probablemente el texto de mayor influencia en tu repositorio. Sin embargo, suele terminar como una larga lista de buenas intenciones que el agente puede ignorar, y que consume contexto sin aportar nada.

## Cuál es su función

Debe decir lo que el agente no puede averiguar por sí mismo leyendo el código, o que le costaría mucho averiguar. Y nada más. Una buena prueba, línea por línea: si la quitara, ¿cometería un error el agente? Si no, sobra.

## Lo que sí funciona

**Comandos exactos.** Evitan intentos fallidos, y es lo más valioso:

```markdown
## Comandos

- Pruebas: `pnpm test --filter @empresa/web`
- Una sola prueba: `pnpm vitest run ruta/al/archivo.test.ts`
- Comprobación completa antes de terminar: `pnpm check`
- Migraciones: `dotnet ef migrations add Nombre -p src/Datos -s src/Api`
```

**Lo que no se deduce del código.**

```markdown
## A tener en cuenta

- `packages/api-client` se genera. No lo edites a mano: ejecuta `pnpm gen:api`.
- Las pruebas de integración necesitan Docker en marcha.
- `LegacyImporter` tiene errores conocidos de los que dependen clientes.
  No los corrijas sin preguntar.
```

**Restricciones concretas.**

```markdown
## Reglas

- Las consultas SQL siempre con parámetros, nunca concatenando.
- No añadas dependencias sin preguntar.
- No hagas commit ni push salvo que se te pida.
```

**Mapa breve de la estructura**, si no es evidente. Con unas líneas basta. No describas cada carpeta.

## Lo que sobra

- **Consejos genéricos**: «escribe código limpio» o «sigue las buenas prácticas» no cambian nada.
- **Lo que un linter puede imponer**: el estilo es mejor comprobarlo con una herramienta, que no se olvida y no gasta contexto.
- **Descripciones que el código ya da**: se quedan obsoletas, y entonces son peores que no tener nada.
- **Documentación larga**: enlaza y explica cuándo leerla.

```markdown
## Más información

- Antes de tocar la autenticación, lee `docs/autenticacion.md`.
- Las decisiones de arquitectura están en `docs/adr/`.
```

Así, el contenido solo se carga cuando hace falta.

## Sé específico

Una instrucción ambigua se interpreta de cualquier manera:

```markdown
<!-- Vago -->
Asegúrate de que las pruebas funcionan.

<!-- Concreto -->
Antes de dar una tarea por terminada, ejecuta `pnpm check` y corrige
todos los fallos. Si no puedes corregir uno, dilo explícitamente.
```

Explicar el motivo también ayuda. «No uses el proveedor en memoria en las pruebas» se cumple mejor si añades: «ha ocultado errores de SQL en el pasado». Un modelo puede aplicar el motivo a casos que no previste.

## Lo que debe ser obligatorio no puede ser una instrucción

Un texto es una petición, no una garantía. Un agente puede olvidarlo, sobre todo en una sesión larga. Si algo debe cumplirse siempre, ponlo en un lugar que no dependa de la buena voluntad:

| Necesidad | Mejor mecanismo |
|---|---|
| Formato y estilo | Linter y formateador |
| No romper las pruebas | CI obligatoria |
| No tocar ciertos archivos | Permisos o CODEOWNERS |
| Ejecutar algo siempre tras editar | Hooks del agente |
| Evitar secretos en commits | Análisis en pre-commit y en CI |

## Un archivo o varios

`AGENTS.md` se ha convertido en una convención común, y muchas herramientas lo leen. Otras tienen su propio archivo, como `CLAUDE.md`. Si tu equipo usa varias, no copies el contenido. Mantén una fuente, y haz que las demás la importen o la enlacen, según lo que admita cada herramienta.

En un monorepo, una instrucción general en la raíz y otras más específicas en cada paquete evitan cargar contexto que no se necesita.

## Mantenerlo

Trátalo como código: en el repositorio y revisado en cada pull request. Algunos hábitos ayudan:

- **Añade por experiencia.** Cuando el agente se equivoque en algo y sea probable que lo repita, añade una línea. No antes.
- **Elimina con frecuencia.** Si una regla ya no hace falta, o la cubre una herramienta, fuera.
- **Mantenlo corto.** Si el archivo es muy largo, las reglas importantes se pierden entre las demás.
- **Pruébalo.** Haz una tarea real desde una sesión limpia, y observa qué falla.

Una lista muy larga no da más control. Un archivo breve, en el que cada línea evita un error real, funciona bastante mejor.

## Empezar

Si tu herramienta tiene un comando de inicialización, úsalo para obtener un borrador, y luego elimina todo lo genérico. Te quedarás con lo importante: los comandos para compilar y probar, las trampas de tu repositorio y las pocas reglas que de verdad te importan.

## Referencias

- [AGENTS.md](https://agents.md/)
- [Buenas prácticas de Claude Code](https://www.anthropic.com/engineering/claude-code-best-practices)
