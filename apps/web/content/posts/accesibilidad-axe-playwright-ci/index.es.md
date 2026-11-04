---
title: "Pruebas automáticas de accesibilidad con axe y Playwright en CI"
seoTitle: "Accesibilidad con axe y Playwright"
description: "Cómo añadir comprobaciones de accesibilidad a tu CI con axe-core y Playwright, gestionar errores ya existentes con una base y entender lo que estas pruebas no detectan."
date: 2025-07-17
tags: ["Accesibilidad", "Testing", "CI/CD"]
---

Una auditoría manual se queda obsoleta en cuanto se publica la siguiente versión. Las pruebas automáticas no sustituyen a una auditoría, pero evitan que vuelvan a aparecer los mismos errores. Y con Playwright se pueden añadir sin grandes cambios.

## Configuración

```bash
pnpm add -D @playwright/test @axe-core/playwright
```

## La primera prueba

```ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("la página de inicio no tiene errores de accesibilidad", async ({ page }) => {
  await page.goto("/");

  const resultado = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();

  expect(resultado.violations).toEqual([]);
});
```

`withTags` limita las reglas a las de los niveles de WCAG que te interesan.

## Analizar también los estados

La mayoría de los problemas no aparecen en la carga inicial, sino en lo que se abre tras una interacción: modales, menús o mensajes de error. Lleva la página a ese estado y analízalo:

```ts
test("el formulario con errores es accesible", async ({ page }) => {
  await page.goto("/registro");
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  await expect(page.getByRole("alert").first()).toBeVisible();

  const resultado = await new AxeBuilder({ page })
    .include("form")
    .analyze();

  expect(resultado.violations).toEqual([]);
});
```

## Un mensaje de error útil

La salida por defecto es difícil de leer. Con un resumen, cualquiera puede ver qué falla:

```ts
function resumir(violaciones: Result[]) {
  return violaciones.map((v) => ({
    regla: v.id,
    impacto: v.impact,
    ayuda: v.helpUrl,
    elementos: v.nodes.map((n) => n.target.join(" ")),
  }));
}

expect(resumir(resultado.violations)).toEqual([]);
```

## Proyectos que ya tienen errores

Si activas todo en una aplicación existente, puede haber cientos de errores, y nadie va a detener el trabajo. Una opción es empezar por lo más grave:

```ts
const graves = resultado.violations.filter(
  (v) => v.impact === "critical" || v.impact === "serious",
);

expect(resumir(graves)).toEqual([]);
```

Otra es guardar los errores actuales como referencia, de forma que solo los nuevos hagan fallar la prueba:

```ts
const conocidos = new Set<string>(baseDeReferencia);

const nuevos = resultado.violations.flatMap((v) =>
  v.nodes
    .map((n) => `${v.id}:${n.target.join(" ")}`)
    .filter((clave) => !conocidos.has(clave)),
);

expect(nuevos).toEqual([]);
```

Ten en cuenta que esta referencia depende de los selectores, así que puede romperse al refactorizar. También hace falta un compromiso para que la lista vaya bajando. Si no, se convierte en un lugar donde olvidar problemas.

Se puede excluir un elemento externo sin ocultar toda la página:

```ts
new AxeBuilder({ page }).exclude("#widget-externo");
```

Añade siempre un comentario con el motivo y dónde se hace seguimiento.

## En CI

```yaml
- name: Pruebas de accesibilidad
  run: pnpm playwright test --project=accesibilidad

- uses: actions/upload-artifact@v4
  if: failure()
  with:
    name: informe-playwright
    path: playwright-report/
```

Solo hace falta un navegador. Analizar los tres repite casi los mismos resultados y aumenta el tiempo de ejecución.

## Comprobar el teclado

Axe no pulsa teclas, pero Playwright sí. Con muy poco esfuerzo puedes verificar el comportamiento:

```ts
test("el modal atrapa el foco y lo devuelve al cerrar", async ({ page }) => {
  await page.goto("/");
  const abrir = page.getByRole("button", { name: "Abrir ajustes" });

  await abrir.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(abrir).toBeFocused();
});
```

## Lo que no detecta

Según estimaciones habituales, las herramientas automáticas encuentran una fracción de los problemas posibles. No pueden saber:

- si un texto alternativo describe la imagen o solo dice «imagen»;
- si el orden de lectura tiene sentido;
- si los errores se entienden;
- si el flujo se puede completar con un lector de pantalla.

Un resultado limpio indica que no se ha encontrado lo que estas reglas buscan, no que la aplicación sea accesible. Mantén pruebas manuales periódicas en los flujos críticos.

## Referencias

- [Pruebas de accesibilidad en Playwright](https://playwright.dev/docs/accessibility-testing)
- [Reglas de axe-core](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)
