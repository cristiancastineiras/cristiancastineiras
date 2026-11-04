---
title: "ADR: documenta las decisiones de arquitectura antes de que nadie las recuerde"
seoTitle: "ADR: decisiones de arquitectura"
description: "Qué es un Architecture Decision Record, una plantilla sencilla para escribirlo junto al código, cuándo merece la pena y cómo evitar que se convierta en burocracia."
date: 2025-03-06
tags: ["Arquitectura", "Documentación"]
---

«¿Por qué usamos esto?» Cuando nadie sabe responder, tienes dos opciones igual de malas: dejarlo tal cual sin entenderlo, por miedo a romper algo, o cambiarlo y descubrir un motivo que se había olvidado. Un *Architecture Decision Record* es un documento breve que evita ese dilema.

## Qué es un ADR

Es un archivo corto que recoge una decisión, su contexto y sus consecuencias. La idea la popularizó Michael Nygard en 2011. No hace falta nada más que Markdown y un directorio en el repositorio:

```text
docs/
└── adr/
    ├── 0001-usar-postgresql.md
    ├── 0002-api-rest-con-openapi.md
    └── 0003-monolito-modular.md
```

## Una plantilla mínima

```markdown
# 3. Usar un monolito modular

Estado: aceptada
Fecha: 2025-03-06

## Contexto

El equipo es de cinco personas. Hay un solo producto, con módulos
de pedidos, facturación y clientes. No hay un equipo de plataforma.

## Decisión

Desplegaremos una única aplicación, dividida en módulos con contratos
explícitos y un esquema de base de datos por módulo.

## Alternativas consideradas

- Microservicios: más autonomía de despliegue, pero un coste de
  operación que no podemos asumir ahora.
- Monolito sin límites: lo más rápido a corto plazo, pero ya hemos
  sufrido sus consecuencias.

## Consecuencias

- Un solo pipeline y un único despliegue.
- Un fallo grave en un módulo afecta a todos.
- Extraer un módulo más adelante será posible, aunque no gratis.
```

Lo importante es que se pueda leer en cinco minutos. Si necesita diez páginas, seguramente es un documento de diseño, que puede ir enlazado.

## El contexto vale más que la decisión

La decisión se puede leer en el código. Lo que no se puede leer es la situación en que se tomó: cuántas personas había, qué plazos y qué se había probado.

Una elección que hoy parece extraña podría haber sido razonable entonces. Y lo más útil: si el contexto cambia, sabrás que esa decisión se puede reconsiderar. «Lo elegimos porque éramos tres» deja de aplicarse cuando sois treinta.

No olvides las alternativas descartadas. Evitan repetir la misma discusión, y permiten saber si una opción se descartó con buen motivo o simplemente no se tuvo en cuenta.

## Cuándo escribir uno

Es una buena señal si la decisión:

- es difícil o costosa de deshacer: base de datos, framework, estilo de comunicación;
- afecta a muchos equipos o a mucho código;
- ha generado una discusión importante;
- se aparta de lo que alguien esperaría encontrar.

No hace falta para cosas fáciles de revertir, como una librería de fechas o la estructura de una carpeta. Si escribes un ADR para cada cosa, nadie querrá escribirlos, y mucho menos leerlos.

## Cómo gestionarlos

**Junto al código.** Un wiki se queda desactualizado y se separa de lo que documenta. En el repositorio, el ADR se revisa como código, en un pull request, y queda vinculado a su commit.

**El pull request como debate.** Propones el ADR, el equipo comenta y, al fusionarlo, queda aceptado. La discusión queda registrada sin necesidad de reuniones adicionales.

**Inmutables.** Si una decisión cambia, no reescribas el anterior. Crea otro nuevo y márcalo:

```markdown
Estado: reemplazada por [ADR 12](0012-migrar-a-eventos.md)
```

Así se conserva la historia completa. Saber por qué algo cambió suele ser tan valioso como saber qué se decidió.

**Numerados.** Facilita las referencias en conversaciones y pull requests.

## Que no se conviertan en burocracia

Lo que más daño hace es exigir un proceso pesado de aprobación. Si proponer un ADR requiere tres comités, la gente tomará las decisiones sin escribir nada. Mantén una plantilla corta y una aprobación sencilla. Y puedes escribirlos también a posteriori: documentar una decisión de hace dos años, con lo que se recuerda, es mejor que no tener nada.

## Empezar hoy

No hace falta documentar todo el pasado. Escribe un primer ADR con la próxima decisión importante, y añade algunos sobre lo que más gente pregunta. Después, cuando alguien plantee en una revisión «¿por qué esto es así?», podrás responderle con un enlace.

Y sirven también para las herramientas de IA: un agente que lee tus ADR entiende por qué las cosas son como son, y es menos probable que proponga deshacer una decisión que ya se había evaluado.

## Referencias

- [Documenting Architecture Decisions, de Michael Nygard](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR en GitHub](https://adr.github.io/)
