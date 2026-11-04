---
title: "Modernizar una aplicación React legacy sin detener el desarrollo"
seoTitle: "Modernizar una aplicación React legacy"
description: "Una estrategia incremental para pasar de Create React App, clases y JavaScript a Vite, hooks y TypeScript, sin reescribir y sin bloquear las nuevas funcionalidades."
date: 2025-12-08
tags: ["React", "Refactorización", "Vite"]
---

Una aplicación React de hace unos años suele tener Create React App, componentes de clase, Redux con mucho código repetido, algo de JavaScript sin tipos y dependencias anticuadas. La tentación es reescribirla. Casi nunca es buena idea: durante meses mantendrás dos aplicaciones y el negocio seguirá pidiendo cambios.

Lo que funciona es modernizar por capas, entregando valor en cada paso.

## Primero, una red de seguridad

Antes de tocar nada:

1. pruebas end-to-end de los flujos críticos con Playwright, que no dependen de la implementación;
2. CI que ejecute compilación, linter y pruebas en cada pull request;
3. captura de errores en producción, para detectar regresiones.

Sin esto, cada cambio es una apuesta.

## Paso 1: las herramientas de compilación

Create React App está obsoleto desde febrero de 2025. Pasar a Vite suele ser un cambio mecánico, y mejora de inmediato el trabajo diario:

```bash
pnpm remove react-scripts
pnpm add -D vite @vitejs/plugin-react
```

Cambios habituales:

- mover `public/index.html` a la raíz y añadir `<script type="module" src="/src/index.tsx">`;
- renombrar `REACT_APP_*` a `VITE_*`, y `process.env` a `import.meta.env`;
- renombrar a `.jsx` o `.tsx` los archivos con JSX;
- reemplazar los alias y las configuraciones especiales de Webpack.

Este paso no toca el código de negocio, y por eso va primero.

## Paso 2: actualizar React por etapas

Sube de versión mayor en mayor, leyendo las guías oficiales. React ofrece codemods que automatizan una parte. Si estás en la versión 16 o 17, activa `createRoot` en la 18 y comprueba el comportamiento de `StrictMode`. Destapa efectos mal limpiados.

Actualiza en pasos separados: React por un lado, el enrutador por otro y la librería de componentes aparte. Si algo falla, sabrás qué lo causó.

## Paso 3: TypeScript gradual

No hace falta convertirlo todo. Se puede permitir la coexistencia:

```json
{
  "compilerOptions": {
    "allowJs": true,
    "checkJs": false,
    "strict": true,
    "noEmit": true
  },
  "include": ["src"]
}
```

Convierte primero las hojas: utilidades y tipos de las APIs. Después, los componentes a medida que los modifiques. Si generas los tipos desde OpenAPI, tendrás contratos fiables desde el primer día. Una regla simple ayuda mucho: todo archivo nuevo se escribe en TypeScript.

## Paso 4: clases a hooks, solo cuando compense

Los componentes de clase siguen funcionando. Reescribir uno que no se toca nunca es un riesgo sin beneficio. Migra cuando vayas a modificarlo, o si impide usar algo que necesitas.

## Paso 5: simplificar el estado

Suele ser donde se elimina más código. Separa lo que viene de la API, que puede ir a TanStack Query, del estado real de interfaz, que suele ser muy poco. Puedes migrar una funcionalidad cada vez, de forma que Redux y lo nuevo convivan hasta que el store se quede vacío.

Si te quedas con Redux, Redux Toolkit reduce mucho el código repetido, y funciona junto al código antiguo.

## Cómo organizar el trabajo

- **Regla del *boy scout***: cada cambio de funcionalidad moderniza lo que toca.
- **Medir el avance**: porcentaje de TypeScript, número de clases, tamaño del bundle y tiempo de CI. Lo que se ve se mantiene.
- **Reglas de lint para no empeorar**: por ejemplo, prohibir importaciones de un módulo obsoleto en archivos nuevos.
- **Una migración cada vez**: tres a medias son peores que una acabada.

## Cuándo reescribir

A veces una parte concreta está tan degradada que conviene reemplazarla. Hazlo por secciones, con enrutado por rutas: la nueva sección sirve algunas URLs y la vieja, las demás. Es el mismo patrón *strangler fig* que se aplica en el backend.

## Referencias

- [Create React App obsoleto](https://react.dev/blog/2025/02/14/sunsetting-create-react-app)
- [Guía de migración a React 19](https://react.dev/blog/2024/04/25/react-19-upgrade-guide)
- [Vite](https://vite.dev/guide/)
