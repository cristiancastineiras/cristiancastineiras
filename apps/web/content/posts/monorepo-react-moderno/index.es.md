---
title: "Cómo monté mi monorepo React moderno y por qué deberías considerarlo"
description: "La arquitectura, las herramientas y las decisiones detrás de una plantilla React con pnpm, Turborepo, Vite, TypeScript, Biome y paquetes reutilizables."
date: 2026-02-02
tags: ["React", "Monorepo", "Vite", "Arquitectura frontend"]
---

Después de ver cómo varios proyectos frontend crecían sin control, decidí crear una plantilla base para arrancar aplicaciones React sin repetir configuraciones, duplicar código ni perder tiempo buscando dónde vive cada cosa.

El objetivo no era construir una arquitectura capaz de resolver cualquier problema futuro. Quería una base práctica que separase las aplicaciones del código compartido, mantuviese la configuración en un único lugar y siguiese siendo comprensible al crecer.

## El problema: una estructura que deja de escalar

Muchos proyectos React empiezan con una estructura parecida a esta:

```text
src/
├── components/
│   ├── Button.tsx
│   ├── Modal.tsx
│   ├── Header.tsx
│   └── ...
├── hooks/
│   └── useAuth.ts
├── utils/
│   └── formatDate.ts
└── pages/
    └── Home.tsx
```

Al principio funciona. El problema aparece cuando `components/` acumula decenas de archivos, los hooks pierden su contexto y las utilidades se convierten en un cajón de sastre.

Si además mantienes varias aplicaciones, el coste se multiplica:

- componentes copiados entre repositorios
- configuraciones de TypeScript ligeramente distintas
- reglas de lint y formato que divergen
- correcciones repetidas en varios proyectos
- decisiones de arquitectura que hay que volver a tomar desde cero

No necesitaba más carpetas dentro de `src/`. Necesitaba definir límites claros entre aplicaciones, código compartido y configuración.

## La solución: un monorepo con paquetes reutilizables

Un monorepo permite mantener varias aplicaciones y paquetes compartidos dentro de un mismo repositorio. Cada paquete conserva sus límites y dependencias, pero todos utilizan una infraestructura común.

La estructura base quedó así:

```text
.
├── apps/
│   └── webapp/
│       ├── src/
│       ├── entorno/
│       ├── index.html
│       ├── vite.config.ts
│       └── tsconfig.json
├── paquetes/
│   ├── api/
│   ├── componentes/
│   ├── configuracion-ts/
│   ├── estados/
│   ├── hooks/
│   ├── modelos/
│   └── utiles/
├── biome.json
├── turbo.json
├── pnpm-workspace.yaml
└── package.json
```

La regla principal es sencilla:

- `apps/` contiene unidades desplegables.
- `paquetes/` contiene código reutilizable.
- la raíz contiene la configuración compartida del repositorio.

Esta separación evita que el código común dependa accidentalmente de una aplicación concreta.

## Aplicaciones y paquetes tienen responsabilidades distintas

Todo lo que se despliega de forma independiente vive en `apps/`. La aplicación web principal está ahí, pero mañana podrían añadirse un panel de administración, una landing o una aplicación móvil.

El código que puede utilizar más de una aplicación vive en `paquetes/`: componentes, modelos, clientes HTTP, hooks o funciones auxiliares.

Esto no significa extraer cualquier función a un paquete. Un módulo solo debe compartirse cuando existe una necesidad real. Mover código prematuramente añade límites artificiales y hace más difícil cambiarlo.

{{< note >}}
Un monorepo facilita compartir código, pero no obliga a compartirlo todo. Si una pieza solo pertenece a una aplicación, debe quedarse dentro de ella.
{{< /note >}}

## Cada paquete declara su propia interfaz

Cada paquete tiene su propio `package.json`. Así puede declarar qué exporta y de qué depende, igual que una librería externa.

Los consumidores utilizan imports predecibles:

```tsx
import { Button } from "@paquetes/componentes";
import { useAuth } from "@paquetes/hooks";
import type { ModeloA } from "@paquetes/modelos";
```

Además de mejorar la lectura, esto evita imports relativos frágiles como `../../../../componentes/Button`.

Un paquete no debería publicar toda su estructura interna. Lo ideal es exponer una entrada clara y mantener el resto como detalle de implementación. De ese modo, reorganizar sus archivos no obliga a modificar todos los consumidores.

## TypeScript centralizado sin ocultar las diferencias

Repetir el mismo `tsconfig.json` en cada aplicación y paquete termina produciendo pequeñas variaciones difíciles de detectar.

Para evitarlo, creé `configuracion-ts`, un paquete con configuraciones base:

```json
{
  "compilerOptions": {
    "strict": true,
    "esModuleInterop": true,
    "moduleResolution": "Bundler",
    "skipLibCheck": true
  }
}
```

Cada aplicación extiende la configuración adecuada y añade únicamente lo que le corresponde:

```json
{
  "extends": "../../paquetes/configuracion-ts/vite.json",
  "include": ["src"],
  "compilerOptions": {
    "jsx": "react-jsx",
    "paths": {
      "@paquetes/*": ["../../paquetes/*"]
    }
  }
}
```

La configuración compartida mantiene la consistencia. La configuración local documenta las diferencias reales de cada proyecto.

Centralizar no significa crear un único archivo enorme. Es preferible tener bases pequeñas para cada entorno, por ejemplo Vite, Node o una librería, y extender la que corresponda.

## Alias automáticos en Vite

Añadir manualmente un alias cada vez que aparece un paquete nuevo es repetitivo y fácil de olvidar. Para evitarlo, la configuración de Vite recorre el directorio de paquetes y genera los alias a partir de sus nombres:

```ts
function crearAliasDesdePaquetes() {
  const directorioPaquetes = path.resolve(__dirname, "../../paquetes");
  const alias: Record<string, string> = {};

  for (const carpeta of fs.readdirSync(directorioPaquetes)) {
    const rutaPackageJson = path.join(
      directorioPaquetes,
      carpeta,
      "package.json",
    );

    if (!fs.existsSync(rutaPackageJson)) continue;

    const packageJson = JSON.parse(
      fs.readFileSync(rutaPackageJson, "utf-8"),
    );

    if (!packageJson.name?.startsWith("@paquetes/")) continue;

    const raizPaquete = path.join(directorioPaquetes, carpeta);
    const rutaSrc = path.join(raizPaquete, "src");

    alias[packageJson.name] = fs.existsSync(rutaSrc)
      ? rutaSrc
      : raizPaquete;
  }

  return alias;
}
```

Cuando se crea un paquete válido dentro de `paquetes/`, Vite puede resolverlo sin modificar una lista adicional.

Esta automatización tiene un coste: la convención del nombre y la estructura pasa a formar parte del contrato del repositorio. Por eso conviene mantener la función pequeña, validar los datos que lee y documentar la convención.

## Variables de entorno tipadas

Las variables de entorno suelen utilizarse como cadenas sin comprobar:

```ts
const apiUrl = import.meta.env.VITE_API_URL;
```

Un error tipográfico puede pasar desapercibido hasta ejecutar una ruta concreta. Para reducir ese riesgo, mi configuración genera un archivo de tipos a partir de las variables disponibles:

```ts
interface ImportMetaEnv {
  readonly VITE_BASE_PATH: string;
  readonly VITE_HOST: string;
  readonly VITE_NOMBRE_APP: string;
  readonly VITE_PROTOCOLO: string;
  readonly VITE_PUERTO: string;
}
```

Esto aporta autocompletado y detecta nombres incorrectos durante el desarrollo.

El tipado no sustituye la validación en tiempo de ejecución. TypeScript puede afirmar que una variable existe, pero el despliegue todavía podría omitirla. Las variables obligatorias deben comprobarse al iniciar la aplicación y producir un error claro.

## Configuración por entorno

En lugar de mezclar todos los valores en un único archivo, la aplicación mantiene archivos separados por modo:

```text
apps/webapp/entorno/
├── .env.desarrollo
├── .env.produccion
└── .env.testing
```

El modo se selecciona al iniciar Vite:

```sh
vite --mode desarrollo
```

Esta separación permite que cada entorno defina sus propios servicios, puertos y rutas sin llenar el código de condiciones.

Los archivos con secretos reales no deben versionarse. El repositorio puede incluir plantillas con los nombres esperados, mientras que los valores sensibles deben inyectarse desde el entorno o desde el sistema de despliegue.

## Herramientas elegidas

La plantilla utiliza pocas herramientas, cada una con una responsabilidad concreta:

- **pnpm** administra el workspace y enlaza los paquetes internos.
- **Turborepo** coordina tareas y reutiliza resultados mediante caché.
- **Vite** sirve la aplicación durante el desarrollo y genera el build.
- **Biome** unifica lint y formato.
- **TypeScript** comprueba los contratos entre aplicaciones y paquetes.
- **Tailwind CSS** genera los estilos utilizados por la aplicación y los componentes compartidos.
- **Zustand** cubre los casos que necesitan estado global sin imponer una arquitectura pesada.

La lista no es una receta universal. Una herramienta debe permanecer en el proyecto porque resuelve un problema actual, no porque sea habitual en otras plantillas.

## Tailwind en los paquetes compartidos

Si los componentes compartidos contienen clases de Tailwind, el compilador tiene que analizar también esos paquetes. De lo contrario, puede eliminar clases que no encuentra dentro de la aplicación.

La hoja de estilos principal incluye Tailwind y declara los paquetes como fuente:

```css
@import "tailwindcss";

/* Clases utilizadas por los paquetes compartidos. */
@source "../../../paquetes";
```

Así, un componente publicado desde `@paquetes/componentes` puede utilizar las mismas utilidades que la aplicación consumidora.

Conviene limitar esta ruta al directorio necesario. Analizar todo el repositorio aumenta el trabajo del compilador y puede incluir archivos que no forman parte de la interfaz.

## Flujo para empezar un proyecto

Una vez preparada la plantilla, el arranque se reduce a tres pasos:

1. Clonar el repositorio.
2. Ejecutar `pnpm install`.
3. Ejecutar `pnpm dev`.

Desde ese momento están disponibles:

- TypeScript estricto
- paquetes internos enlazados
- alias configurados
- variables de entorno tipadas
- Tailwind en aplicaciones y paquetes
- lint y formato compartidos
- tareas coordinadas desde la raíz

Lo importante no es ahorrar unos minutos en la instalación. La ventaja real es que todos los proyectos empiezan con las mismas decisiones y reciben sus mejoras desde un único lugar.

## Cuándo no utilizar un monorepo

Un monorepo introduce costes:

- más configuración inicial
- límites entre paquetes que hay que diseñar
- tareas que deben funcionar tanto de forma aislada como conjunta
- riesgo de acoplar aplicaciones que deberían evolucionar por separado
- una infraestructura que el equipo tiene que entender

Para una aplicación pequeña, sin código compartido ni previsión de nuevas aplicaciones, probablemente sea una solución excesiva.

Empieza a compensar cuando se cumple alguna de estas condiciones:

- existen varias aplicaciones que comparten código
- hay componentes o modelos que deben evolucionar de forma coordinada
- se necesita una configuración consistente entre proyectos
- el equipo repite las mismas correcciones en varios repositorios
- los cambios afectan habitualmente a más de un paquete

La decisión no debería basarse en el tamaño actual del repositorio, sino en la relación real entre sus proyectos.

## Lo que aprendí

La mayor ventaja del monorepo no fue tener todo el código en el mismo lugar. Fue hacer explícitas las fronteras:

- qué se despliega
- qué se comparte
- qué depende de qué
- qué configuración es común
- qué diferencias son intencionadas

Una buena estructura no elimina las decisiones futuras, pero evita tener que resolver una y otra vez los mismos problemas básicos.

La plantilla sigue cambiando según aparecen necesidades reales. Esa es precisamente la idea: disponer de una base sólida sin convertirla en un framework interno imposible de mantener.

El código está disponible en [GitHub](https://github.com/Cristiancastt/plantilla-react-monorepo). Puedes utilizarlo como punto de partida, adaptarlo o quedarte solo con las ideas que encajen en tu proyecto.