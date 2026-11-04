---
title: "Pruebas como barandilla: cómo dejar que un agente de IA trabaje sin vigilarlo"
seoTitle: "Pruebas para agentes de IA"
description: "Cómo preparar un repositorio para agentes de programación: comprobaciones rápidas, un comando único, pruebas primero y medidas para que no debiliten los controles."
date: 2026-09-07
tags: ["Agentes", "IA", "Testing"]
---

Si un agente solo recibe la orden de hacer un cambio, terminará cuando crea que ha terminado. Si puede comprobarlo por sí mismo, seguirá intentándolo hasta que funcione de verdad. Esta es, probablemente, la mejora más grande que puedes hacer en tu forma de trabajar con agentes, y no tiene nada que ver con el modelo.

## Por qué funciona

Un agente escribe código sin saber si es correcto. Una comprobación que pueda ejecutar se convierte en información: lee el error, corrige y vuelve a probar. Sin ella, tú eres el bucle de retroalimentación, y cada iteración necesita tu tiempo.

Cuanto más rápida y fiable sea esa comprobación, mejor funciona todo.

## Un único comando

Dale una sola cosa que ejecutar:

```json
{
  "scripts": {
    "check": "biome check . && tsc --noEmit && vitest run"
  }
}
```

Y documéntalo en las instrucciones del proyecto:

```markdown
Antes de dar una tarea por terminada, ejecuta `pnpm check` y corrige
los fallos. Si no consigues corregir uno, dilo en lugar de ocultarlo.
```

Con .NET:

```bash
dotnet format --verify-no-changes && dotnet build -warnaserror && dotnet test
```

## Comprobaciones rápidas y útiles

Un agente ejecuta pruebas muchas veces. Si tardan 20 minutos, las evitará, o se quedará esperando.

- **Selección**: ofrece formas de ejecutar solo lo relacionado, como `vitest related` o un filtro por proyecto.
- **Errores claros**: «expected 121, got 100 en calcularIva» sirve. «Test failed» no. Lo que ayuda a una persona también ayuda al agente.
- **Sin inestabilidad**: una prueba intermitente enseña a ignorar fallos, o lleva al agente a perseguir un problema que no existe.
- **Salida reducida**: mil líneas de logs ocupan contexto. Con un reporter conciso, muestra solo lo relevante.
- **Tipos estrictos**: son las comprobaciones más rápidas, y detectan muchos errores típicos, como métodos que no existen.

## Pruebas primero

Con un agente, TDD se vuelve mucho más barato. Un flujo que funciona bien:

1. Pídele que escriba una prueba que describa el comportamiento o reproduzca el error.
2. Comprueba que falla, y por la razón correcta.
3. Revisa tú esa prueba: ahí está la especificación.
4. Pídele que escriba el código hasta que pase, sin tocar la prueba.

```text
Escribe una prueba que reproduzca este fallo: al aplicar un descuento
del 100 %, el total es negativo. Ejecútala y confirma que falla.
No corrijas todavía el código.
```

Revisar una prueba de diez líneas es mucho más fácil que revisar la implementación, y te da una garantía duradera. Para corregir un error, esto evita que el agente lo dé por resuelto sin haberlo reproducido.

## Cuando se debilitan los controles

Aquí hay un riesgo real: un agente al que se le pide que todo salga en verde puede conseguirlo de la peor manera. Puede borrar una prueba, marcarla como omitida, relajar una aserción o añadir un `@ts-ignore`.

Por eso, no bastan las instrucciones. Añade controles en lugares que no pueda cambiar con la misma facilidad:

- **CI como autoridad**: el agente puede saltarse un gancho local, pero no el pipeline de la rama protegida.
- **Revisión de los cambios en pruebas**: mira con más atención cualquier diff en `*.test.*` o en la configuración.
- **Configuración protegida**: usa `CODEOWNERS` para que `tsconfig`, las reglas de linter y los pipelines requieran tu aprobación.
- **Detectar supresiones**: una comprobación simple que avise si aumenta su número.

```bash
#!/bin/sh
# Falla si este cambio añade supresiones sin justificar
base=$(git merge-base origin/main HEAD)
nuevas=$(git diff "$base" -- '*.ts' '*.tsx' \
  | grep -E '^\+.*(@ts-ignore|eslint-disable|\.skip\()' \
  | wc -l)

if [ "$nuevas" -gt 0 ]; then
  echo "Se han añadido $nuevas supresiones. Revísalas."
  exit 1
fi
```

## Ganchos del agente

Muchas herramientas permiten ejecutar comandos en eventos concretos, como después de editar un archivo o antes de terminar. A diferencia de una instrucción, un gancho siempre se ejecuta. Son útiles para formatear lo editado, o para bloquear operaciones como escribir en archivos generados o ejecutar comandos peligrosos.

No los llenes de procesos lentos, porque se ejecutan continuamente. Lo rápido se hace en cada edición, y la comprobación completa, al terminar.

## Lo que las pruebas no cubren

Pasar las pruebas no significa que el trabajo esté bien hecho: el código puede ser correcto, y aun así demasiado complicado, inseguro o simplemente no lo que querías. Y las pruebas solo verifican lo que alguien pensó en comprobar.

Para interfaces, dale formas de ver el resultado: pruebas con Playwright o capturas de pantalla, que pueda comparar. Sin eso, no sabe si el botón ha quedado fuera de la pantalla.

Tu revisión sigue siendo necesaria. Lo que cambia es dónde pones la atención: menos en si compila y funciona, y más en si es lo que hacía falta.

## Por dónde empezar

Si tu repositorio apenas tiene pruebas, no necesitas cubrirlo todo. Pide al agente pruebas de caracterización de la zona que vas a tocar. Revísalas, y úsalas para hacer el cambio. El código mejora justo donde estás trabajando, y cada tarea deja la red de seguridad un poco mejor que antes.

## Referencias

- [Buenas prácticas de Claude Code](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Vitest: filtrar pruebas](https://vitest.dev/guide/filtering)
