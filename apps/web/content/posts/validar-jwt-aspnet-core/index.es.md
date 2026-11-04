---
title: "Validar JWT en ASP.NET Core sin dejar huecos de seguridad"
seoTitle: "Validar JWT en ASP.NET Core"
description: "Qué comprobar al validar tokens JWT en ASP.NET Core: emisor, audiencia, firma, expiración y políticas de autorización, con los errores de configuración más peligrosos."
date: 2025-03-31
tags: [".NET", "ASP.NET Core", "Seguridad"]
---

Que una API exija un JWT no significa que esté protegida. Lo está si comprueba que el token lo emitió quien debe, para esa API, con una firma válida y dentro de su vigencia. Un parámetro mal puesto puede desactivar parte de esa comprobación sin que nada lo advierta.

## Una configuración de partida

Con un proveedor de identidad compatible con OpenID Connect, solo necesitas indicar la autoridad y la audiencia:

```csharp
builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = "https://login.ejemplo.com/realms/empresa";
        options.Audience = "api-facturacion";
    });

builder.Services.AddAuthorization();

var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();
```

A partir de `Authority`, el middleware descarga el documento de descubrimiento y las claves públicas, y las rota cuando corresponde. No hay que copiar ninguna clave a mano.

## Qué se valida y qué nunca debes desactivar

Por defecto se comprueban emisor, audiencia, firma y expiración. En internet aún circulan ejemplos como este, y conviene no copiarlos:

```csharp
// Nunca en producción
options.TokenValidationParameters = new()
{
    ValidateIssuer = false,
    ValidateAudience = false,
    ValidateIssuerSigningKey = false,
};
```

Sin validar la audiencia, un token emitido para otra aplicación del mismo proveedor sería aceptado por tu API. En una empresa con decenas de aplicaciones bajo el mismo proveedor, esto es un riesgo real: un token de una aplicación poco crítica abriría la puerta a otra sensible.

Tampoco desactives HTTPS para los metadatos fuera de desarrollo (`RequireHttpsMetadata = false`).

## Ajustar el margen de reloj

`ClockSkew` tolera diferencias de hora entre servidores, y por defecto son 5 minutos. Un token puede seguir siendo válido hasta 5 minutos después de expirar. Si usas tokens de vida muy corta, quizá quieras reducirlo:

```csharp
options.TokenValidationParameters.ClockSkew = TimeSpan.FromSeconds(30);
```

## Autenticación no es autorización

Un token válido dice quién eres, no qué puedes hacer. Las políticas expresan el permiso de forma explícita:

```csharp
builder.Services.AddAuthorizationBuilder()
    .AddPolicy("facturas:escribir", policy =>
        policy.RequireAuthenticatedUser()
              .RequireClaim("scope", "facturas.write"));

app.MapPost("/facturas", CrearFactura)
   .RequireAuthorization("facturas:escribir");
```

Cuidado con `scope`: algunos proveedores lo envían como una sola cadena separada por espacios, y `RequireClaim` compararía contra el valor completo. Si es tu caso, transforma las *claims* o usa una comprobación propia.

También hay que recordar la autorización a nivel de recurso. Tener permiso para leer facturas no implica poder leer *cualquier* factura. Filtra siempre por el propietario o el inquilino, ya que olvidarlo es la causa de una de las vulnerabilidades más frecuentes en APIs.

## Hacer segura la API por defecto

Una política de reserva obliga a autenticarse en cualquier endpoint que no diga lo contrario:

```csharp
builder.Services.AddAuthorizationBuilder()
    .SetFallbackPolicy(new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .Build());
```

Lo público se marca con `AllowAnonymous()`. Si alguien olvida un atributo, el resultado es un 401, no una fuga de datos.

## Qué no guardar en un JWT

El contenido del token está codificado en Base64URL, no cifrado. Cualquiera que lo tenga puede leerlo. No incluyas datos personales innecesarios ni información sensible.

## Referencias

- [Autenticación JWT bearer en ASP.NET Core](https://learn.microsoft.com/aspnet/core/security/authentication/configure-jwt-bearer-authentication)
- [OWASP API Security Top 10](https://owasp.org/API-Security/)
