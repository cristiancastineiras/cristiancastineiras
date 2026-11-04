---
title: "Cloudflare Access: proteger paneles internos sin una VPN"
seoTitle: "Cloudflare Access sin VPN"
description: "Cómo proteger herramientas internas publicadas con Cloudflare Tunnel usando Access: políticas por identidad, tokens de servicio y validación del JWT en tu propia aplicación."
date: 2026-03-09
tags: ["Cloudflare", "Seguridad", "Homelab"]
---

Paneles de administración, métricas, Grafana o un Jenkins interno: herramientas que no deberían estar abiertas a Internet, pero a las que necesitas acceder desde cualquier parte. Cloudflare Tunnel permite publicar servicios sin abrir puertos. Access añade lo que falta: exigir una identidad antes de que la petición llegue a tu servidor.

## Cómo funciona

```text
Usuario → Cloudflare → ¿Identidad válida?
                          ├─ No: pantalla de acceso
                          └─ Sí: túnel → tu servicio
```

La comprobación ocurre en el borde de Cloudflare. Quien no se autentique no alcanza tu aplicación, por lo que no puede explotar en ella una vulnerabilidad del formulario de inicio de sesión.

## Crear una aplicación

En **Zero Trust → Access → Applications**, añade una aplicación de tipo *Self-hosted*:

```text
Nombre:     Grafana
Dominio:    grafana.midominio.com
Sesión:     24 horas
```

Después, define quién puede entrar:

```text
Política:   Equipo
Acción:     Allow
Incluir:    Emails que terminan en @midominio.com
```

Por defecto, si nadie cumple una política de permiso, se deniega el acceso. Como proveedor de identidad, puedes empezar con códigos de un solo uso por correo, sin configurar nada más. Para un equipo, es mejor conectar el proveedor de identidad de la empresa, porque quien se marche perderá el acceso de forma automática.

## Reglas más finas

Las políticas se pueden combinar, y permiten exigir varias condiciones:

- **Include**: al menos una debe cumplirse.
- **Require**: todas deben cumplirse.
- **Exclude**: si se cumple, no entra.

```text
Incluir:   Grupo "Administradores"
Requerir:  Autenticación multifactor
Requerir:  País = España
```

Cuidado con incluir `Everyone` en una política de tipo *Allow* sin requisitos adicionales: dejarías el servicio abierto a cualquiera que ponga un correo.

## Acceso desde scripts

Un trabajo de CI no puede iniciar sesión con un navegador. Para eso existen los tokens de servicio, con una política de acción *Service Auth*:

```bash
curl https://grafana.midominio.com/api/health \
  -H "CF-Access-Client-Id: $CF_ID" \
  -H "CF-Access-Client-Secret: $CF_SECRET"
```

Crea un token por cada uso, con una caducidad definida, y guárdalo como cualquier otro secreto. Así podrás revocar uno sin afectar a los demás.

## Validar en tu aplicación

Si tu servicio solo escucha a través del túnel, en una red privada de Docker, nadie puede saltarse Cloudflare. Pero si alguien más llega a ese puerto, por ejemplo desde la red local, las comprobaciones de Access no se aplican.

Por eso, Cloudflare añade la cabecera `Cf-Access-Jwt-Assertion`, con un JWT firmado, para que tu aplicación pueda comprobarlo con las claves públicas de tu equipo. En Node.js, con la librería `jose`:

```ts
import { createRemoteJWKSet, jwtVerify } from "jose";

const equipo = "https://miequipo.cloudflareaccess.com";
const claves = createRemoteJWKSet(new URL(`${equipo}/cdn-cgi/access/certs`));

export async function validarAccess(token: string) {
  const { payload } = await jwtVerify(token, claves, {
    issuer: equipo,
    audience: process.env.CF_ACCESS_AUD,
  });

  return payload.email;
}
```

En ASP.NET Core, la comprobación es la misma con `JwtBearer`: emisor, audiencia y esas claves, leyendo el token de la cabecera en el evento `OnMessageReceived`.

El valor de la audiencia (`AUD`) aparece en la configuración de la aplicación de Access. Es imprescindible comprobar la audiencia: si no, un token de otra aplicación de tu cuenta sería válido en esta.

No uses `Cf-Access-Authenticated-User-Email` como prueba de identidad sin validar el token. Cualquiera que acceda directamente a tu servicio podría enviar esa cabecera con el valor que quiera.

## Cuando la aplicación tiene su propio login

Access no sustituye necesariamente a los permisos de la aplicación. Muchos paneles permiten delegar la autenticación en un proxy mediante una cabecera, lo que evita iniciar sesión dos veces. Grafana, por ejemplo, tiene un modo específico para la cabecera JWT. Si lo activas, asegúrate de que la aplicación solo acepta tráfico desde el túnel.

## Acceso que no es HTTP

Para SSH y otros protocolos, Cloudflare Access también puede actuar como intermediario:

```bash
# ~/.ssh/config
Host servidor.midominio.com
  ProxyCommand cloudflared access ssh --hostname %h
```

Así no necesitas exponer el puerto 22 a Internet. Mantén, además, la autenticación por clave en el servidor.

## Registrar y revisar

Los registros de Access muestran quién ha intentado entrar, y desde dónde. Revísalos alguna vez, y envíalos a tu sistema de logs si los necesitas para auditoría.

## Cuándo no es suficiente

Con Access, dependes de Cloudflare para llegar a tus servicios internos: si tiene una incidencia, se corta el acceso. Mantén una vía alternativa documentada para emergencias. Además, Cloudflare ve el tráfico que pasa por él, algo que debes valorar si manejas datos sensibles o con requisitos normativos. Si eso es un problema, una VPN como WireGuard o Tailscale puede ser más adecuada.

## Referencias

- [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/applications/)
- [Validar JWT de Access](https://developers.cloudflare.com/cloudflare-one/identity/authorization-cookie/validating-json/)
- [Tokens de servicio](https://developers.cloudflare.com/cloudflare-one/identity/service-tokens/)
