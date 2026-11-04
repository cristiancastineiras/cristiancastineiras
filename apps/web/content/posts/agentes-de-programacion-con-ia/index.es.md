---
title: "Agentes de programación con IA en 2027: skills, comandos, plugins y hooks explicados"
seoTitle: "Agentes de IA en 2027: guía"
description: "Un modelo mental para entender reglas, comandos, skills, subagentes, MCP, hooks y plugins: qué controla cada pieza, quién la activa y cuándo es solo ruido."
date: 2026-11-03
tags: ["IA", "Agentes", "MCP", "Productividad"]
---

Si programas a las puertas de 2027, la pregunta ya no es si la IA puede escribir código. Puede. La pregunta es cómo organizar todo lo que ha aparecido a su alrededor: reglas, comandos, skills, subagentes, MCP, hooks, plugins…

Cada pocas semanas llega algo nuevo con su propio vocabulario, y casi todas las explicaciones saltan directamente a la configuración sin contar por qué existe cada pieza. Lo pruebas. Algunas cosas parecen magia durante un rato. Poco después, la configuración se vuelve frágil y difícil de razonar.

El problema no es que estas piezas sean malas. Es que casi nunca se explican como partes de un mismo sistema.

Yo pasé por esa confusión. Este post es el modelo mental que me habría gustado tener: sirve para cualquier herramienta (Claude Code, Codex, Cursor, Copilot…) y te ayuda a distinguir cuándo una pieza resuelve un problema real y cuándo solo añade ruido.

## Modelo mental central

Un agente de programación repite este bucle una y otra vez:

1. **Carga el contexto persistente**: lo que debe saber siempre.
2. **Interpreta la intención**: qué le estás pidiendo ahora.
3. **Planifica**: elige cómo resolverlo.
4. **Actúa**: lee, edita, ejecuta.
5. **Observa** el resultado: tests, errores, el navegador…
6. **Itera** hasta terminar.

Cada pieza existe para controlar un paso concreto de ese bucle:

- Las **reglas** fijan las restricciones.
- Los **comandos** lanzan la intención.
- Los **skills** aportan el método.
- Los **subagentes** acotan quién actúa y con qué contexto.
- **MCP** conecta al agente con el mundo para actuar y observar.
- Los **hooks** garantizan que algo ocurra en puntos fijos del bucle, decida lo que decida el modelo.
- Los **plugins** no controlan ningún paso: empaquetan todo lo anterior para compartirlo.

{{< note >}}
Si dos piezas intentan controlar el mismo paso, aparece la confusión. Casi todos los problemas de configuración que he visto vienen de ahí.
{{< /note >}}

Hay un segundo eje que hoy importa tanto como el primero: **el contexto es un presupuesto**. Cada pieza entra en la ventana de contexto del modelo en un momento distinto, y eso decide cuánto cuesta y cuánto escala. Lo verás en cada sección.

### El ejemplo que usaremos

Tienes una API de tareas en producción. Ayer usaste un agente para añadir un endpoint y hoy quieres añadir más funciones. Hay dos cosas que no se negocian:

- El comportamiento existente no puede cambiar.
- Los tests tienen que seguir pasando.

## Reglas

Las reglas existen para separar las restricciones de la ejecución. Sin esa separación acabas repitiendo las mismas restricciones en cada prompt, y el comportamiento del agente cambia en cuanto cambia la tarea.

### Qué son en la práctica

Restricciones persistentes, escritas en Markdown, que el agente carga al empezar cada sesión, sea cual sea la tarea. Describen lo que siempre debe ser cierto. Definen límites, no acciones.

Cada herramienta tenía su propio archivo (`CLAUDE.md`, las reglas de Cursor, las instrucciones de Copilot), pero `AGENTS.md` se ha convertido en el formato común que lee casi cualquier agente. Suelen funcionar por capas: unas globales, otras del repositorio y otras de una carpeta concreta.

### Para qué sirven

Para proteger invariantes, las cosas que no quieres renegociar en cada tarea:

- límites de arquitectura
- dependencias permitidas
- estructura de carpetas
- convenciones de código y de tests
- compatibilidad hacia atrás

Si algo es una invariante, va en las reglas.

### Ejemplo

Para la API de tareas:

```markdown
# AGENTS.md

## Restricciones
- La validación vive en la capa de dominio (`src/domain/`), nunca en los controladores.
- No añadas dependencias nuevas.
- Reutiliza los helpers de `tests/helpers/`.
- No cambies el comportamiento público de la API sin una instrucción explícita.

## Cómo trabajar aquí
- Tests: `npm test`
- Lint: `npm run lint`
```

Con esto en su sitio, los prompts pueden ser cortos y hablar solo de intención.

### Malentendido común

Tratar las reglas como entrenamiento de comportamiento:

- «Escribe código limpio.»
- «Piensa bien antes de programar.»
- «Refactoriza cuando corresponda.»

Eso no son restricciones: obligan a interpretar. **Si una regla necesita juicio para aplicarse, no es una regla.** Es un skill o es trabajo de revisión humana.

Y cuidado con el tamaño: las reglas se cargan *siempre*, así que cada línea se paga en cada conversación. Un `AGENTS.md` de 500 líneas no es más seguro; es más ruido.

## Comandos

Los comandos expresan intención de ejecución. Responden a una sola pregunta: ¿qué tiene que hacer el agente ahora?

### Qué son en la práctica

Una instrucción con nombre que invocas tú, normalmente con `/nombre`, guardada como un Markdown que puede recibir parámetros. Hace una sola cosa y se ejecuta en el contexto actual.

### Para qué sirven

- lanzar un cambio concreto
- disparar un flujo de trabajo conocido
- mantener la interacción rápida y directa

Funcionan mejor cuando la intención está clara.

### Ejemplo

```markdown
---
description: Añade un endpoint a la API de tareas
argument-hint: <método> <ruta>
---

Añade el endpoint $ARGUMENTS con su validación de entrada y sus tests.
```

Escribes `/nuevo-endpoint POST /tasks/:id/archive` y listo. Fíjate en lo que **no** dice: ni dónde va la validación ni cómo se organizan los tests. Eso ya lo cubren las reglas y los skills.

### Malentendido común

Cargar los comandos de política. Un comando que explica cómo estructurar el código, dónde vive la lógica y qué compromisos valorar está compensando reglas o skills que faltan.

Si un comando no para de crecer, es la señal de que el problema ya no es solo de ejecución.

## Skills

Los skills separan el método de la ejecución: capturan *cómo* resuelves una clase de problemas que se repite.

### Qué son en la práctica

Una carpeta con un `SKILL.md` (instrucciones con un nombre y una descripción) y, si hace falta, scripts, plantillas o documentación de apoyo. Lo que empezó en Claude Code es hoy un formato abierto, Agent Skills, que leen varias herramientas.

La clave está en cómo entran en el contexto. Al empezar, el agente solo ve el nombre y la descripción de cada skill; el resto se carga cuando el modelo reconoce que la tarea encaja. Por eso puedes tener decenas de skills sin pagar su coste en cada conversación. Y por eso **la descripción es la parte más importante**: es lo que decide si el skill se activa.

### Para qué sirven

- capturar patrones de ingeniería repetibles
- dejar de repetir el mismo prompt
- dar consistencia entre tareas
- escribir una vez las prácticas de tu dominio y reutilizarlas en todas partes
- ejecutar scripts o herramientas como parte de un método conocido

Sacan el método de los comandos y dejan los comandos centrados en la intención.

### Ejemplo

```markdown
---
name: validacion-de-entrada
description: Cómo añadir o cambiar la validación de entrada en la API de tareas. Úsalo al crear endpoints o al modificar los datos que reciben.
---

# Validación de entrada

1. Define el esquema en `src/domain/schemas/`, uno por recurso.
2. Devuelve los errores como `422` con `{ field, message }`.
3. Cubre en tests: campo ausente, tipo incorrecto, valores límite y campos desconocidos.
```

Cuando el comando pide un endpoint nuevo, el modelo reconoce la tarea y aplica este método.

### Malentendido común

Crear skills demasiado pronto. Si algo no se repite, no merece un skill. Y una descripción vaga («ayuda con la API») hace que el skill se active cuando no toca, o que no se active nunca.

Un matiz de 2027: en muchas herramientas, comandos y skills ya comparten formato. Los dos son un Markdown con *frontmatter*. La diferencia no está en el archivo, sino en **quién lo dispara**: el comando lo lanzas tú; el skill lo elige el modelo.

## Subagentes

Los subagentes limitan quién actúa en una tarea: acotan explícitamente el alcance, el contexto y las herramientas.

### Qué son en la práctica

Un agente con una responsabilidad concreta, sus propias instrucciones y su propia ventana de contexto, definido normalmente como un Markdown con metadatos. El agente principal decide cuándo delegar; el subagente trabaja aparte y devuelve solo el resultado.

### Para qué sirven

- controlar el radio de impacto de un cambio
- separar responsabilidades
- evitar cambios cruzados que nadie pidió
- mantener limpio el contexto principal: la exploración ruidosa (leer cincuenta archivos, revisar logs) ocurre en otra ventana y vuelve resumida

### Ejemplo

```markdown
---
name: tests
description: Actualiza y amplía los tests después de un cambio en la lógica de dominio.
tools: Read, Edit, Bash
---

Solo modificas archivos dentro de `tests/`. Si un test falla por un bug en el código,
no lo arreglas: lo explicas en tu respuesta.
```

Un subagente toca solo la validación y este otro, solo los tests. Cada uno trabaja dentro de su alcance.

### Malentendido común

Venderlos como paralelismo. Rara vez se introducen para ir más rápido: se introducen porque un único agente con demasiadas responsabilidades se vuelve impredecible.

Su valor real es el aislamiento: limitar qué puede cambiar, dónde y por qué. La velocidad es un efecto secundario, no el objetivo. Además, delegar tiene un coste: el subagente arranca sin tu contexto y hay que explicarle la tarea. Para cambios pequeños, delegar suele ser más lento que hacerlo directamente.

## MCP

MCP (*Model Context Protocol*) es el estándar abierto para conectar agentes con herramientas, datos y sistemas externos. Nació en Anthropic a finales de 2024, hoy está bajo el paraguas de la Linux Foundation y lo soportan prácticamente todos los agentes.

Se usa cuando el modelo necesita información del mundo real en lugar de adivinarla, o cuando tiene que actuar sobre otro sistema.

### Qué es en la práctica

Un servidor MCP expone herramientas que el agente puede llamar: un navegador, tu base de datos, el gestor de incidencias, la documentación de una librería. El modelo las usa para observar resultados que no puede deducir solo a partir del texto.

### Para qué sirve

- validar suposiciones
- leer errores y salidas reales
- consultar sistemas externos
- actuar fuera del repositorio

### Ejemplo

- abrir la app en un navegador y comprobar que el endpoint nuevo responde
- inspeccionar por qué falla un test de integración
- consultar en la base de datos de staging cómo son los datos reales
- leer la incidencia que originó el cambio

### Malentendido común

Tratar MCP como inteligencia. No mejora el razonamiento: mejora el *feedback*.

Dos matices más. Cada servidor añade definiciones de herramientas al contexto, así que conectar veinte «por si acaso» empeora al agente. Algunas herramientas ya las cargan bajo demanda, pero el criterio sigue siendo el mismo: conecta lo que uses. Y lo que devuelve un servidor es contenido externo: una página web o una incidencia pueden traer instrucciones escritas por cualquiera. Trata los servidores MCP como dependencias y dales solo los permisos justos.

## Hooks

Los hooks separan la aplicación de una política del razonamiento. Se ejecutan fuera del bucle del modelo y se disparan en puntos fijos, decida lo que decida el LLM.

**Una regla es una petición. Un hook es una garantía.**

### Qué son en la práctica

Un comando determinista (un script, un formateador, tu suite de tests) asociado a un evento del ciclo del agente: antes de usar una herramienta, después de editar un archivo, al terminar la tarea…

### Para qué sirven

- imponer políticas
- formatear código
- pasar tests y linters
- bloquear cambios inseguros

### Ejemplo

En Claude Code se configuran así (otras herramientas tienen equivalentes con otro formato):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "./scripts/proteger-migraciones.sh" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "npm run format" }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "./scripts/tests-en-verde.sh" }]
      }
    ]
  }
}
```

- **Antes de editar**, un script bloquea cualquier cambio en `db/migrations/`.
- **Después de editar**, el formateador deja el código como debe.
- **Al terminar**, un script pasa los tests y, si fallan, el agente no puede darse por terminado. Comprueba `stop_hook_active` en la entrada para no entrar en bucle.

El bloqueo es así de simple:

```bash
#!/usr/bin/env bash
# proteger-migraciones.sh: el hook recibe la llamada a la herramienta en JSON por stdin.
ruta=$(jq -r '.tool_input.file_path')
if [[ "$ruta" == *"/db/migrations/"* ]]; then
  echo "db/migrations/ está protegido: crea una migración nueva." >&2
  exit 2  # bloquea la acción y devuelve el mensaje al agente
fi
```

### Malentendido común

Meter lógica de decisión en los hooks. Si un hook necesita razonar, no es un hook: es un skill o un subagente.

Y recuerda que un hook es código que se ejecuta en tu máquina, con tus permisos, cada vez que se dispara. Revísalo como revisarías un script de CI.

## Plugins

Los plugins no añaden una capa de control nueva: **empaquetan** las que ya tienes. Existen para distribuir.

### Qué son en la práctica

Un paquete versionado que agrupa comandos, skills, subagentes, hooks y servidores MCP, y que se instala de una vez desde un *marketplace*, ya sea el de tu equipo o uno público. Claude Code fue de los primeros en adoptarlos, y otras herramientas tienen mecanismos parecidos.

### Para qué sirven

- compartir la configuración de agentes de tu equipo
- llevar el mismo método a varios repositorios
- versionar y actualizar todo junto

### Ejemplo

Tu equipo mantiene varias APIs como la de tareas. En lugar de copiar archivos entre repositorios, publicáis un plugin `api-backend` con el comando `/nuevo-endpoint`, el skill de validación, el subagente de tests y el hook de migraciones. Cada repositorio lo instala y conserva sus propias reglas en su `AGENTS.md`, porque las invariantes son de cada proyecto.

### Malentendido común

Instalar plugins como quien colecciona extensiones. Cada uno suma descripciones de skills y herramientas al contexto, y sus hooks ejecutan código en tu máquina. Un plugin es una dependencia: instala pocos, léelos y sabe qué traen.

## Cómo encajan juntos

| Pieza | Qué controla | Quién la activa | Cuándo entra en el contexto |
| --- | --- | --- | --- |
| Reglas | Restricciones | Nadie: siempre están | Siempre |
| Comandos | La intención de ahora | Tú | Al invocarlo |
| Skills | El método | El modelo | La descripción, siempre; el resto, cuando encaja |
| Subagentes | Alcance y responsabilidad | El agente principal | En su propia ventana; vuelve el resumen |
| MCP | Observación y acción externa | El modelo | Las definiciones de herramientas; los resultados, al llamarlas |
| Hooks | Garantías | Eventos del ciclo | No pasan por el modelo; solo su mensaje, si bloquean |
| Plugins | Distribución | Tú, al instalarlo | Lo que traiga dentro |

No empiezas con todo esto. Cada capa aparece cuando aparece un problema concreto:

- ¿Repites las mismas restricciones en cada prompt? → **reglas**.
- ¿Escribes una y otra vez la misma petición? → **comando**.
- ¿Explicas una y otra vez *cómo* hacer algo? → **skill**.
- ¿El agente toca lo que no debe, o el contexto se llena de ruido? → **subagente**.
- ¿El agente adivina cosas que podría comprobar? → **MCP**.
- ¿Algo tiene que cumplirse siempre, sin excepciones? → **hook**.
- ¿Copias la misma configuración entre repositorios? → **plugin**.

## Cierre

Los agentes de programación no son asistentes: son sistemas de ejecución con capas de control explícitas.

No deciden qué es importante, qué es seguro ni qué debería cambiar. Ejecutan dentro de la estructura que les das, y fallan de forma predecible cuando esa estructura falta.

Cuando entiendes en qué paso del bucle actúa cada pieza, quién la activa y cuánto contexto cuesta, las herramientas nuevas dejan de abrumar y empiezan a parecer piezas que se combinan. El agente acaba reflejando tus decisiones de diseño, no solo tu intención. Y la responsabilidad sobre la corrección, la seguridad y la claridad sigue siendo tuya como ingeniero.
