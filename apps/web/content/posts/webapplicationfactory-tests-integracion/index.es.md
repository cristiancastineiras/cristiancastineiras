---
title: "Tests de integración en ASP.NET Core con WebApplicationFactory"
seoTitle: "WebApplicationFactory en ASP.NET Core"
description: "Cómo probar tu API desde HTTP hasta la base de datos con WebApplicationFactory: sustituir dependencias externas, simular autenticación y escribir pruebas legibles."
date: 2025-04-10
tags: [".NET", "ASP.NET Core", "Testing"]
---

Una prueba unitaria de un controlador no dice mucho: no comprueba el enrutado, el enlace de modelos, la serialización, los filtros ni la autorización. Con `WebApplicationFactory` puedes arrancar toda la aplicación en memoria y hablar con ella por HTTP, sin abrir un puerto real.

## Lo básico

```bash
dotnet add package Microsoft.AspNetCore.Mvc.Testing
```

Si usas instrucciones de nivel superior, `Program` es interno, y lo tienes que hacer accesible:

```csharp
// Al final de Program.cs
public partial class Program;
```

La primera prueba:

```csharp
public sealed class ClientesApiTests(WebApplicationFactory<Program> factory)
    : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task Devuelve_404_si_el_cliente_no_existe()
    {
        var cliente = factory.CreateClient();

        var respuesta = await cliente.GetAsync("/clientes/999");

        Assert.Equal(HttpStatusCode.NotFound, respuesta.StatusCode);
    }
}
```

Toda tu aplicación se ejecuta: el contenedor de dependencias, los middlewares y la autorización.

## Sustituir lo que no quieres en la prueba

Crea una factoría propia y reemplaza lo externo:

```csharp
public sealed class ApiFactory : WebApplicationFactory<Program>
{
    public FakeEnviadorDeCorreos Correos { get; } = new();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");

        builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<IEnviadorDeCorreos>();
            services.AddSingleton<IEnviadorDeCorreos>(Correos);
        });
    }
}
```

`ConfigureTestServices` se ejecuta después del registro de la aplicación, así que lo tuyo prevalece. Sustituye solo lo que no controlas, como correo, pasarelas de pago o servicios externos. Si reemplazas demasiado, estarás probando otra cosa.

## Comprobar el contrato

Comprobar el JSON real, además de los tipos, ayuda a detectar cambios accidentales en el contrato:

```csharp
[Fact]
public async Task Crear_cliente_devuelve_201_y_la_ubicacion()
{
    var http = _factory.CreateClient();

    var respuesta = await http.PostAsJsonAsync("/clientes", new
    {
        nombre = "Ana",
        email = "ana@ejemplo.com",
    });

    Assert.Equal(HttpStatusCode.Created, respuesta.StatusCode);
    Assert.NotNull(respuesta.Headers.Location);

    var creado = await respuesta.Content.ReadFromJsonAsync<JsonElement>();
    Assert.Equal("Ana", creado.GetProperty("nombre").GetString());
}
```

Si reutilizas el DTO de la API para deserializar, un cambio de nombre en una propiedad no hará fallar la prueba, aunque rompa a tus clientes.

## Probar los errores

```csharp
[Fact]
public async Task Rechaza_un_email_no_valido_con_problem_details()
{
    var http = _factory.CreateClient();

    var respuesta = await http.PostAsJsonAsync("/clientes", new { nombre = "Ana", email = "no" });

    Assert.Equal(HttpStatusCode.BadRequest, respuesta.StatusCode);
    Assert.Equal("application/problem+json", respuesta.Content.Headers.ContentType?.MediaType);
}
```

## Simular la autenticación

No tiene sentido que cada prueba hable con un proveedor de identidad. Sí es conveniente registrar un esquema de prueba:

```csharp
public sealed class AutenticacionDePrueba(
    IOptionsMonitor<AuthenticationSchemeOptions> options,
    ILoggerFactory logger,
    UrlEncoder encoder)
    : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
{
    public const string Esquema = "Prueba";

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        if (!Request.Headers.TryGetValue("X-Usuario-Prueba", out var usuario))
            return Task.FromResult(AuthenticateResult.NoResult());

        var identidad = new ClaimsIdentity(
            [new Claim(ClaimTypes.NameIdentifier, usuario.ToString())],
            Esquema);

        return Task.FromResult(AuthenticateResult.Success(
            new AuthenticationTicket(new ClaimsPrincipal(identidad), Esquema)));
    }
}
```

```csharp
services.AddAuthentication(AutenticacionDePrueba.Esquema)
    .AddScheme<AuthenticationSchemeOptions, AutenticacionDePrueba>(
        AutenticacionDePrueba.Esquema, _ => { });
```

Como no autentica si no hay cabecera, también puedes probar que un usuario anónimo recibe un 401. Los dos tipos de prueba son importantes: el acceso permitido y el acceso denegado. Y comprueba expresamente que un usuario no puede acceder a recursos de otro.

Registra este esquema solo en el proyecto de pruebas, nunca en la aplicación.

## La base de datos

Lo ideal es usar el mismo motor que en producción con Testcontainers, y sustituir la cadena de conexión en la factoría. Si tu aplicación aplica migraciones al arrancar, o carga datos, comprueba lo que ocurre en el entorno `Testing`.

## Velocidad

Crear una factoría arranca la aplicación entera, lo que tarda. Compártela entre pruebas usando `IClassFixture` o `ICollectionFixture`. Eso sí, si cambias la configuración con `WithWebHostBuilder`, se creará otro servidor, así que úsalo solo cuando lo necesites.

Si te encuentras con una prueba que necesita mucha preparación, prueba esa lógica en un nivel más bajo. Estas pruebas funcionan mejor para los contratos, los permisos y los flujos importantes, no para cada combinación de reglas.

## Referencias

- [Pruebas de integración en ASP.NET Core](https://learn.microsoft.com/aspnet/core/test/integration-tests)
