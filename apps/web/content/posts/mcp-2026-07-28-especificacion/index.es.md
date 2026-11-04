---
title: "MCP 2026-07-28: el protocolo sin sesiones y qué cambia en tus servidores"
seoTitle: "MCP 2026-07-28: qué cambia"
description: "Qué cambia en la especificación 2026-07-28 de Model Context Protocol: núcleo sin estado, peticiones de varias rondas, autorización y cómo migrar un servidor."
date: 2026-08-17
tags: ["MCP", "Agentes", "IA"]
---

Model Context Protocol nació como una forma sencilla de conectar herramientas con asistentes, y al principio era habitual ejecutar los servidores en la misma máquina. Cuando se desplegaron detrás de balanceadores, las sesiones con estado se convirtieron en un problema. La especificación 2026-07-28 ataca justo eso, y es la mayor revisión del protocolo hasta ahora.

## Un núcleo sin estado

Hasta ahora, cliente y servidor iniciaban una sesión con `initialize`, y el identificador `Mcp-Session-Id` debía acompañar cada petición. Eso exigía sesiones persistentes en el balanceador, o almacenar el estado de forma compartida.

Ahora, ese intercambio se retira. Cada petición lleva en `_meta` la versión del protocolo, la identidad del cliente y sus capacidades, de modo que cualquier instancia puede atenderla.

```text
Antes:  initialize → initialized → petición (con sesión) → ...
Ahora:  petición autosuficiente, a cualquier réplica
```

Para descubrir qué ofrece un servidor existe un RPC específico, y una versión no compatible devuelve un error concreto (`UnsupportedProtocolVersionError`).

La consecuencia práctica: un servidor MCP se parece mucho más a una API HTTP normal. Se escala de forma horizontal, y se puede desplegar en un entorno sin servidor.

## Peticiones de varias rondas

Antes, un servidor podía enviar sus propias peticiones al cliente durante una llamada: pedir datos al usuario o una generación al modelo. Eso obligaba a mantener un canal abierto y estado en memoria.

Ahora, el servidor devuelve un resultado que indica lo que necesita (`InputRequiredResult`), y el cliente vuelve a enviar la petición original con esas respuestas:

```text
1. Cliente: tools/call eliminar_proyecto
2. Servidor: InputRequiredResult → "confirmación requerida"
3. El cliente pregunta al usuario
4. Cliente: tools/call eliminar_proyecto + inputResponses
5. Servidor: resultado
```

Es un flujo que recuerda más a una petición HTTP con reintento que a un canal bidireccional. Como la petición repetida llega a una instancia cualquiera, el servidor no puede guardar en memoria lo que tenía a medias.

## Otros cambios relevantes

- **Suscripciones**: `subscriptions/listen` sustituye a `resources/subscribe`, `resources/unsubscribe` y al endpoint GET.
- **Cabeceras de enrutado**: `MCP-Protocol-Version`, `Mcp-Method` y `Mcp-Name` permiten a un gateway enrutar sin analizar el cuerpo de la petición.
- **Caché**: las respuestas de listas incluyen `ttlMs` y `cacheScope`.
- **Extensiones**: hay un marco formal para añadir funciones sin esperar a una nueva versión del núcleo.
- **Obsoletos**: *roots*, *sampling* y *logging* siguen funcionando, pero van de salida.

## Autorización

Quizá el cambio con más impacto para los equipos de seguridad. Se añade la validación del emisor de la RFC 9207, y el registro de clientes pasa de *Dynamic Client Registration* a documentos de metadatos del cliente (CIMD): el identificador del cliente es una URL con sus metadatos. El registro dinámico sigue funcionando por ahora, aunque se retirará.

Si tu servidor usa OAuth, revisa estos flujos con el proveedor de identidad antes de actualizar.

## Qué hacer si tienes un servidor

Los SDK oficiales de TypeScript, Python, Go y C# ya lo soportan, con Rust en beta, así que buena parte del trabajo recae en ellos. Lo que suele quedar en tu código:

1. **Busca estado en memoria asociado a la sesión.** Es lo que deja de funcionar: cachés por sesión, conexiones abiertas para un cliente o datos entre llamadas.
2. **Mueve ese estado.** Haz que cada herramienta reciba lo que necesita en la llamada, o guarda los datos de forma externa, indexados por algo como un recurso o una tarea.
3. **Adapta las solicitudes al usuario** al nuevo flujo de varias rondas.
4. **Mantén ambas versiones** durante la transición, si tus clientes no se actualizan al mismo tiempo. Un cliente antiguo seguirá iniciando sesión.
5. **Revisa la infraestructura.** Quizá ya puedas eliminar las sesiones persistentes del balanceador.
6. **Prueba la autorización** de principio a fin con el nuevo flujo.

Antes de reescribir nada, consulta qué versiones soportan tus clientes y cuál es la política de tu SDK.

## Si estás empezando

Para un servidor que se ejecuta en local por `stdio`, muchos de estos cambios apenas se notarán. Empieza con el SDK de tu lenguaje, usa la última versión de la especificación y diseña las herramientas sin estado desde el principio.

La seguridad no cambia en lo esencial. Un servidor MCP da a un modelo la capacidad de actuar: aplica mínimos permisos, valida cada entrada y pide confirmación para lo destructivo. Y trata el contenido devuelto por una herramienta como no fiable, porque puede contener instrucciones dirigidas al modelo.

## Referencias

- [La especificación 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- [Especificación de MCP](https://modelcontextprotocol.io/specification)
