---
title: "Monolito modular en .NET: los límites de los microservicios sin su coste"
seoTitle: "Monolito modular en .NET"
description: "Cómo estructurar un monolito modular en .NET con módulos bien delimitados, contratos públicos, datos separados por esquema y pruebas de arquitectura que imponen las reglas."
date: 2026-06-08
tags: [".NET", "Arquitectura"]
---

Muchos equipos adoptan microservicios por un motivo razonable, como evitar un código enmarañado, y acaban con un problema mayor: el mismo enredo, pero ahora con llamadas de red de por medio. Un monolito modular intenta conservar los límites claros, sin el coste operativo de un sistema distribuido.

## Qué es

Se trata de una sola aplicación y un solo despliegue, dividida internamente en módulos independientes. Cada módulo es dueño de su lógica y sus datos, y solo se relaciona con los demás a través de un contrato explícito.

```text
src/
├── Host/                       ← punto de entrada
├── Modulos/
│   ├── Pedidos/
│   │   ├── Pedidos.Contratos/  ← lo único visible desde fuera
│   │   └── Pedidos/            ← implementación interna
│   ├── Facturacion/
│   │   ├── Facturacion.Contratos/
│   │   └── Facturacion/
│   └── Clientes/
└── tests/
```

## La regla clave

Un módulo solo puede referenciar los `Contratos` de otros, nunca su implementación:

```xml
<!-- Facturacion.csproj -->
<ItemGroup>
  <ProjectReference Include="..\..\Pedidos\Pedidos.Contratos\Pedidos.Contratos.csproj" />
</ItemGroup>
```

Dentro de cada módulo, los tipos son `internal` por defecto. Si algo no es público, nadie puede acoplarse a ello por accidente:

```csharp
namespace Pedidos.Contratos;

public interface IPedidosModulo
{
    Task<PedidoResumen?> ObtenerAsync(int id, CancellationToken ct);
}

public sealed record PedidoResumen(int Id, decimal Total, string Estado);
```

```csharp
namespace Pedidos.Internos;

internal sealed class PedidosModulo(PedidosDbContext db) : IPedidosModulo
{
    public Task<PedidoResumen?> ObtenerAsync(int id, CancellationToken ct) =>
        db.Pedidos
            .Where(p => p.Id == id)
            .Select(p => new PedidoResumen(p.Id, p.Total, p.Estado))
            .FirstOrDefaultAsync(ct);
}
```

Cada módulo expone un único método de registro, y el host no necesita saber nada más:

```csharp
builder.Services.AddPedidos(builder.Configuration);
builder.Services.AddFacturacion(builder.Configuration);

app.MapPedidos();
app.MapFacturacion();
```

## Datos separados

Es donde más se juega el acoplamiento. Si `Facturacion` hace un `JOIN` con las tablas de `Pedidos`, ya no podrás cambiar ese esquema sin romper otro módulo. Lo más práctico es usar una sola base de datos, con un esquema y un `DbContext` por módulo:

```csharp
internal sealed class PedidosDbContext(DbContextOptions<PedidosDbContext> options)
    : DbContext(options)
{
    protected override void OnModelCreating(ModelBuilder builder)
    {
        builder.HasDefaultSchema("pedidos");
    }
}
```

Sin claves foráneas entre esquemas: un módulo guarda el identificador de otro, sin una relación en la base de datos. Pierdes una garantía, y por eso hay que decidir conscientemente cómo se tratan esos casos.

## Comunicación entre módulos

Hay dos formas:

**Llamada directa**, cuando necesitas una respuesta inmediata. Es un método normal en el mismo proceso, a través de la interfaz.

**Eventos**, cuando un módulo no necesita saber quién reacciona:

```csharp
public sealed record PedidoConfirmado(int PedidoId, decimal Total, DateTimeOffset En);
```

Facturación se suscribe, y Pedidos no depende de ella. Si la reacción tiene que ser fiable, publica estos eventos con el patrón *outbox*, para no perderlos si el proceso cae.

## Hacer cumplir las reglas

Las convenciones que nadie comprueba terminan incumpliéndose. Una prueba de arquitectura lo evita:

```csharp
[Fact]
public void Facturacion_no_depende_de_la_implementacion_de_Pedidos()
{
    var resultado = Types.InAssembly(typeof(FacturacionModulo).Assembly)
        .ShouldNot()
        .HaveDependencyOn("Pedidos.Internos")
        .GetResult();

    Assert.True(resultado.IsSuccessful);
}
```

Con `NetArchTest` o `ArchUnitNET`, una violación hace fallar la CI, y no se queda como un comentario en un pull request.

## Y si luego hace falta un microservicio

Con estos límites, extraer un módulo es un trabajo acotado: el contrato se convierte en una API o en mensajes, y los datos ya están separados. Hazlo cuando exista un motivo concreto:

- necesita escalar de forma muy distinta al resto;
- un equipo independiente lo necesita para desplegar a su propio ritmo;
- tiene requisitos de aislamiento o tecnología diferentes.

Lo que no suele justificarlo es que quede más limpio. Un sistema distribuido añade latencia, fallos parciales, consistencia eventual y más trabajo de operaciones, y este coste se paga para siempre.

## Lo que tampoco resuelve

Un único despliegue significa que un fallo o una fuga de memoria en un módulo afecta a todos. Tampoco ayuda si el dominio está mal dividido: unos módulos mal delimitados son un problema, también en el mismo proceso. Dedica tiempo a identificar qué partes del negocio cambian juntas.

## Referencias

- [MonolithFirst, de Martin Fowler](https://martinfowler.com/bliki/MonolithFirst.html)
- [NetArchTest](https://github.com/BenMorris/NetArchTest)
