---
title: "MCP, CLI o API directa: qué necesita de verdad tu agente de programación"
seoTitle: "MCP, CLI o API para agentes"
description: "Cuándo un servidor MCP aporta valor frente a una CLI o una API directa, cuánto contexto consume cada opción y cómo decidir sin añadir complejidad."
date: 2026-09-14
tags: ["MCP", "Agentes", "IA"]
---

Con MCP en todas partes, es tentador conectar a tu agente con diez servidores. Sin embargo, cada herramienta disponible cuesta contexto y añade riesgo. Y muchas veces, ya hay algo que funciona: un agente con acceso a una terminal sabe usar `gh`, `kubectl` o `psql`. La pregunta no es si MCP es bueno, sino qué ganas con él en cada caso.

## Tres formas de dar una capacidad

**Línea de comandos.** El agente ejecuta un programa y lee su salida.

```bash
gh pr list --state open --json number,title,author
```

**API directa.** El código escrito por el agente, o un script tuyo, llama a un servicio.

**Servidor MCP.** Publica herramientas con un esquema, que el cliente presenta al modelo.

```json
{
  "name": "listar_pull_requests",
  "description": "Lista los pull requests abiertos de un repositorio",
  "inputSchema": {
    "type": "object",
    "properties": {
      "repositorio": { "type": "string" }
    },
    "required": ["repositorio"]
  }
}
```

## Cuándo basta con una CLI

Suele ser la mejor opción si:

- ya existe una herramienta madura y documentada;
- el modelo la conoce, y `--help` le permite descubrir el resto;
- la salida se puede filtrar con `--json`, `jq` o `grep`, para traer solo lo necesario;
- quieres que tú y el agente uséis exactamente lo mismo.

Sus ventajas son reales: no gasta contexto hasta que se usa, se puede componer en tuberías, y la autenticación es la que ya tienes configurada. Y si algo falla, lo puedes reproducir copiando el comando.

## Cuándo aporta valor un servidor MCP

- **No hay terminal**: el agente vive en una aplicación web o de escritorio, sin un shell.
- **Autenticación compartida**: OAuth gestionado por usuario, sin repartir tokens en cada máquina, para un equipo que usa un servicio interno.
- **Control centralizado**: quieres aprobar, registrar y limitar qué se puede hacer desde un único punto.
- **Capacidad acotada**: expones solo unas pocas operaciones seguras, en vez de todo lo que permite una CLI completa.
- **Sistemas internos sin CLI**: es más sencillo ofrecer una herramienta bien descrita que documentar una API compleja.
- **Reutilización**: varios clientes, de distintos proveedores, usan lo mismo.

## El coste en contexto

Las definiciones de herramientas ocupan espacio, y pueden sumar decenas de miles de tokens si conectas varios servidores grandes. Eso resta espacio al código y a la conversación, y muchas opciones parecidas pueden empeorar la elección del modelo.

Muchos clientes ya cargan las definiciones bajo demanda, lo que reduce el problema, aunque no elimina la necesidad de elegir. Revisa cuánto consume tu configuración, y desactiva lo que no estés usando en ese proyecto.

Un servidor con 40 herramientas que traducen cada endpoint uno a uno suele ser peor que 5 herramientas que resuelven tareas completas.

```text
Peor:   get_user, get_user_orders, get_order_lines, get_order_status
Mejor:  resumen_pedidos_cliente(cliente_id)
```

Diseña pensando en lo que el agente quiere conseguir, no en cómo está organizada tu API.

## Los resultados también ocupan

Una herramienta que devuelve 5000 líneas de JSON te sale cara en cada llamada. Con una CLI, el agente puede filtrar. En un servidor MCP, el filtrado depende de ti: añade paginación y resultados resumidos, con un parámetro para pedir más detalle.

## Seguridad

Ninguna opción es segura por defecto, aunque los riesgos son diferentes.

- **CLI**: hereda todos tus permisos. Un agente con tu sesión de `kubectl` puede hacer lo que tú puedas. Usa credenciales limitadas, y exige confirmar comandos peligrosos.
- **MCP**: instalar un servidor de terceros es instalar código, y sus descripciones pueden influir en el modelo. Revísalo como cualquier dependencia, y fija su versión.
- **Ambas**: lo que devuelven puede contener instrucciones maliciosas, como un *issue* o un correo escrito por un atacante. Un agente con acceso a datos privados, contenido no fiable y un canal de salida es una combinación especialmente peligrosa. Evita reunir las tres cosas.

## Una forma de decidir

1. **¿Hay una CLI buena y el agente tiene terminal?** Úsala.
2. **¿Es una tarea que repites con un procedimiento concreto?** Escribe un script y una instrucción o *skill* que lo explique.
3. **¿Falta la herramienta, o varias personas necesitan lo mismo con una autenticación común?** Ahí encaja un servidor MCP.
4. **¿Es algo que solo vas a hacer una vez?** Que el agente escriba el código, y listo.

Empieza por lo más sencillo, y añade solo cuando encuentres una limitación real. Cada capacidad nueva es algo más que mantener, que revisar y que puede salir mal.

## Referencias

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Consideraciones de seguridad de MCP](https://modelcontextprotocol.io/specification/latest/basic/security_best_practices)
