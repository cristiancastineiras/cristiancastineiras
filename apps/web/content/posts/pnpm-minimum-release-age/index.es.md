---
title: "minimumReleaseAge en pnpm: protege tu proyecto de paquetes comprometidos"
seoTitle: "pnpm minimumReleaseAge"
description: "Los ataques a la cadena de suministro de npm suelen detectarse en horas. Cómo esperar antes de instalar versiones nuevas con pnpm y otras medidas que refuerzan tu proyecto."
date: 2025-10-02
tags: ["pnpm", "Seguridad", "Node.js"]
---

Septiembre de 2025 dejó claro lo frágil que es la cadena de suministro de npm: varios paquetes muy usados publicaron versiones maliciosas tras el robo de cuentas de sus mantenedores, y un gusano llegó a propagarse por sí mismo entre paquetes. Hubo un patrón común: la mayoría se detectó y retiró en pocas horas o días.

Eso permite una defensa muy simple: no instalar lo que acaba de publicarse.

## La configuración

pnpm incorporó esta opción en la versión 10.16:

```yaml
# pnpm-workspace.yaml
minimumReleaseAge: 4320
```

El valor se expresa en minutos, y 4320 son tres días. pnpm ignorará las versiones publicadas hace menos de ese tiempo al resolver dependencias.

Si necesitas una excepción, por ejemplo un parche de seguridad urgente o un paquete de tu propia organización:

```yaml
minimumReleaseAgeExclude:
  - "@empresa/*"
  - webpack
```

La contrapartida es que los parches llegan más tarde. Por eso conviene una excepción explícita para las correcciones críticas, y un proceso para aplicarla.

## El lockfile: la primera línea de defensa

Sin lockfile, cada instalación puede resolver versiones distintas. Compruébalo en CI:

```bash
pnpm install --frozen-lockfile
```

Si alguien introduce una versión nueva, se verá en el diff del `pnpm-lock.yaml`. Revisa también esos cambios, porque un lockfile modificado de forma maliciosa puede apuntar a otra URL. Herramientas como `lockfile-lint` lo pueden comprobar.

## Los scripts de instalación

Muchos ataques se ejecutan en `postinstall`. pnpm 10 no ejecuta los scripts de las dependencias por defecto. Debes autorizarlos uno a uno:

```yaml
onlyBuiltDependencies:
  - esbuild
  - "@swc/core"
```

El comando `pnpm approve-builds` te ayuda a revisar lo pendiente. Es una de las mejores razones para usar pnpm 10: una dependencia nueva no ejecuta código en tu máquina solo por instalarse.

Con npm, se puede conseguir algo similar con `ignore-scripts=true` en el `.npmrc`, aunque algunos paquetes necesitarán pasos adicionales.

## Credenciales: reducir el daño

El objetivo de los últimos ataques fue robar tokens. Si tus dependencias ejecutan código en CI, solo tienen acceso a lo que el trabajo les ofrezca:

- no expongas secretos en los pasos que no los necesitan;
- separa la instalación y la compilación del despliegue, con permisos distintos;
- usa tokens de vida corta, con OIDC, en vez de secretos estáticos;
- en local, no guardes credenciales de nube en variables de entorno permanentes.

```yaml
# Secreto solo en el paso que lo necesita
- run: pnpm install --frozen-lockfile
- run: pnpm build
- run: ./desplegar.sh
  env:
    TOKEN: ${{ secrets.TOKEN }}
```

## Publicar con seguridad

Si publicas paquetes:

- activa la autenticación multifactor resistente al phishing;
- usa *trusted publishing* con OIDC en lugar de tokens de larga duración;
- publica con procedencia verificable (`--provenance`).

Esto protege también a quienes dependen de ti.

## Auditar sin sobrevalorarlo

```bash
pnpm audit --prod
```

`audit` solo encuentra vulnerabilidades conocidas y publicadas. No detecta un paquete malicioso recién subido, y además genera ruido con dependencias de desarrollo que nunca llegan a producción. Es útil, pero no sustituye al resto de medidas.

## Menos dependencias, menos riesgo

Cada dependencia, y las suyas, es código de un tercero con acceso a tu entorno. Antes de instalar algo para ahorrarte unas pocas líneas, pregúntate si realmente compensa. Los navegadores y Node.js ya incluyen mucho de lo que antes requería un paquete: `fetch`, `structuredClone`, `crypto.randomUUID` o el formato de fechas con `Intl`.

## Una configuración de partida

```yaml
minimumReleaseAge: 4320
onlyBuiltDependencies:
  - esbuild
```

Dos líneas y un `--frozen-lockfile` en CI: un coste mínimo para una mejora considerable. No te protegen de todo, porque un ataque puede tardar más en detectarse, pero eliminan una parte importante del riesgo.

## Referencias

- [Configuración de pnpm](https://pnpm.io/settings)
- [Mitigar ataques a la cadena de suministro con pnpm](https://pnpm.io/supply-chain-security)
