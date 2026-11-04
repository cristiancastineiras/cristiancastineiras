---
title: "Playwright en CI: pruebas end-to-end que no fallan al azar"
seoTitle: "Playwright en CI sin pruebas inestables"
description: "Cómo escribir pruebas Playwright estables: localizadores por rol, esperas automáticas, sesiones reutilizables, datos aislados, trazas y paralelismo en GitHub Actions."
date: 2025-11-06
tags: ["Testing", "CI/CD", "TypeScript"]
---

Una prueba end-to-end que falla una de cada veinte veces es peor que no tener ninguna: el equipo se acostumbra a relanzarla y deja de confiar en los resultados. La mayor parte de esa inestabilidad se debe a esperas manuales, selectores frágiles y datos compartidos, y todo eso se puede evitar.

## Localizadores que resisten

```ts
// Frágil: se rompe con cualquier cambio de maquetación
await page.locator("div.form > div:nth-child(3) button.btn-primary").click();

// Robusto: lo que ve el usuario
await page.getByRole("button", { name: "Guardar" }).click();
await page.getByLabel("Correo electrónico").fill("ana@ejemplo.com");
```

Si no puedes localizar un botón por su rol y su nombre, puede que tengas también un problema de accesibilidad. Usa `getByTestId` solo como último recurso, cuando el texto cambie mucho o no exista.

## No uses esperas fijas

```ts
// Mal: lento si sobra, frágil si no alcanza
await page.waitForTimeout(3000);

// Bien: espera y reintenta hasta que se cumple
await expect(page.getByText("Pedido confirmado")).toBeVisible();
```

Las aserciones `expect` de Playwright reintentan automáticamente, y las acciones esperan a que el elemento esté visible, estable y habilitado. Si ves un `waitForTimeout`, normalmente es un error.

Cuidado con las aserciones que no reintentan:

```ts
// No reintenta: comprueba una sola vez
expect(await page.getByRole("listitem").count()).toBe(3);

// Reintenta
await expect(page.getByRole("listitem")).toHaveCount(3);
```

## Reutilizar la sesión

Iniciar sesión por la interfaz en cada prueba es lento y añade un punto de fallo. Hazlo una vez, y reutiliza el estado:

```ts
// playwright.config.ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      dependencies: ["setup"],
      use: { storageState: "playwright/.auth/usuario.json" },
    },
  ],
});
```

```ts
// auth.setup.ts
import { test as setup } from "@playwright/test";

setup("iniciar sesión", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Correo").fill(process.env.E2E_USUARIO!);
  await page.getByLabel("Contraseña").fill(process.env.E2E_CLAVE!);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL("/");
  await page.context().storageState({ path: "playwright/.auth/usuario.json" });
});
```

Añade `playwright/.auth` a `.gitignore`, porque contiene sesiones válidas.

## Datos aislados

Si dos pruebas modifican el mismo registro, fallarán solo cuando se ejecuten en paralelo. Cada una debería crear lo que necesita, por API, que es más rápido que por la interfaz:

```ts
test("permite cancelar un pedido", async ({ page, request }) => {
  const respuesta = await request.post("/api/pedidos", { data: { total: 10 } });
  const { id } = await respuesta.json();

  await page.goto(`/pedidos/${id}`);
  await page.getByRole("button", { name: "Cancelar pedido" }).click();

  await expect(page.getByText("Cancelado")).toBeVisible();
});
```

No dependas del orden de ejecución ni del resultado de otras pruebas.

## Simular servicios externos

Lo que no controlas no debería poder hacer fallar tus pruebas. Intercepta esas llamadas:

```ts
await page.route("**/api.proveedor.com/**", (ruta) =>
  ruta.fulfill({ json: { estado: "ok" } }),
);
```

Para los flujos críticos con terceros, mantén unas pocas pruebas reales, pero apartadas del pipeline principal.

## Configuración para CI

```ts
export default defineConfig({
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html"]] : "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:4173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
});
```

`forbidOnly` impide que un `test.only` olvidado deje el resto sin ejecutar. Un reintento es razonable, pero vigila las pruebas que solo pasan al reintentar: están marcadas como *flaky* en el informe, y hay que arreglarlas, no ignorarlas.

## Dividir en GitHub Actions

```yaml
jobs:
  e2e:
    runs-on: ubuntu-24.04
    strategy:
      fail-fast: false
      matrix:
        parte: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - run: pnpm playwright install --with-deps chromium
      - run: pnpm build
      - run: pnpm playwright test --shard=${{ matrix.parte }}/4
      - uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: informe-${{ matrix.parte }}
          path: playwright-report/
```

Prueba contra la compilación de producción, con `vite preview` o similar, y no contra el servidor de desarrollo.

## Depurar un fallo

El visor de trazas es la función más útil. Descarga el artefacto y ejecútalo:

```bash
pnpm playwright show-trace trace.zip
```

Muestra cada acción, el DOM en ese momento, la red y la consola. Con eso, se puede depurar un fallo de CI sin tener que reproducirlo.

## Cuántas pruebas escribir

Las end-to-end son las más costosas de mantener. Dedícalas a los flujos cuyo fallo sería más grave, como iniciar sesión, pagar o registrarse, y deja los detalles para pruebas de nivel inferior. Unas pocas fiables valen más que cientos en las que nadie confía.

## Referencias

- [Buenas prácticas de Playwright](https://playwright.dev/docs/best-practices)
- [Autenticación en Playwright](https://playwright.dev/docs/auth)
- [Visor de trazas](https://playwright.dev/docs/trace-viewer)
