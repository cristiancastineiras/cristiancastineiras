---
title: "Tests de caracterización: cómo tocar código legacy que nadie entiende"
seoTitle: "Tests de caracterización en legacy"
description: "Cómo fijar el comportamiento actual de código sin pruebas antes de refactorizarlo, con tests de caracterización, snapshots aprobados y costuras para aislar dependencias."
date: 2025-05-22
tags: ["Testing", "Refactorización", ".NET"]
---

Hay código que nadie se atreve a tocar. No tiene pruebas, no hay documentación y quien lo escribió ya no está. Sin embargo, funciona, y el negocio depende de ello. ¿Cómo lo cambias sin romperlo?

La respuesta, que popularizó Michael Feathers, parece un contrasentido: antes de cambiarlo, escribe pruebas que confirmen lo que hace ahora, incluso los errores.

## Qué es un test de caracterización

Una prueba normal comprueba lo que el código *debería* hacer. Una de caracterización documenta lo que *hace*. El proceso es casi mecánico:

1. Escribe una prueba que llame al código, con una aserción que sabes que fallará.
2. Ejecútala y mira el resultado real.
3. Cambia la aserción para que coincida.

```csharp
[Fact]
public void Calcula_el_recargo_de_un_pedido_tardio()
{
    var calculadora = new CalculadoraRecargos();

    var recargo = calculadora.Calcular(importe: 100m, diasRetraso: 45);

    // Valor obtenido al ejecutar. ¿Debería ser 15? Quizá, pero es lo que hoy hace.
    Assert.Equal(12.5m, recargo);
}
```

Puede que encuentres algo que parece un error. No lo arregles en ese momento: anótalo. Si alguien depende de ese comportamiento, un arreglo silencioso podría ser el verdadero fallo. Primero, fija el estado actual. Después, corrige de forma deliberada en un cambio aparte.

## Muchas combinaciones con poco código

Si el método tiene mucha lógica, escribir cada caso a mano es tedioso. Las pruebas de aprobación permiten capturar una salida grande de una sola vez, y compararla con una versión aprobada.

Con la librería Verify:

```csharp
[Fact]
public Task Recargos_para_todas_las_combinaciones()
{
    var calculadora = new CalculadoraRecargos();

    var resultados =
        from importe in new[] { 0m, 50m, 100m, 1000m }
        from dias in new[] { 0, 1, 30, 31, 90, 365 }
        select new { importe, dias, recargo = calculadora.Calcular(importe, dias) };

    return Verify(resultados);
}
```

La primera ejecución genera un archivo, que revisas y guardas en Git. A partir de ahí, cualquier diferencia hace que falle. Elige los valores con cuidado: los bordes como 30 y 31 días suelen ser donde está la lógica.

Si no sabes qué valores son relevantes, una herramienta de cobertura te dirá qué ramas aún no has recorrido.

## Cuando no se puede instanciar la clase

Lo normal es que el código legacy no sea fácil de probar: llama a la base de datos, usa `DateTime.Now`, envía correos. Feathers llama *seams*, costuras, a los puntos donde se puede cambiar el comportamiento sin modificar el código.

**Extraer e invalidar.** Es el mínimo cambio posible y suele ser seguro:

```csharp
public class ServicioFacturas
{
    public decimal Procesar(int id)
    {
        var ahora = ObtenerFecha();
        // ... lógica existente
    }

    protected virtual DateTime ObtenerFecha() => DateTime.Now;
}

// En la prueba
class ServicioFacturasDePrueba : ServicioFacturas
{
    protected override DateTime ObtenerFecha() => new(2025, 1, 15);
}
```

**Inyectar la dependencia.** Es una opción más limpia si puedes cambiar el constructor. Para el tiempo, .NET ya ofrece `TimeProvider`:

```csharp
public class ServicioFacturas(TimeProvider reloj)
{
    public decimal Procesar(int id)
    {
        var ahora = reloj.GetUtcNow();
        // ...
    }
}
```

Con el paquete `Microsoft.Extensions.TimeProvider.Testing`, puedes usar `FakeTimeProvider` en las pruebas.

## Probar desde más arriba

A veces lo más eficaz no es aislar una clase, sino probar desde fuera: una petición HTTP a la API, con una base de datos real en un contenedor. Estas pruebas no dependen de la estructura interna, de modo que sobreviven a la refactorización. Es justo lo que necesitas al reorganizar el código.

## Cómo avanzar

1. **Delimita lo que vas a cambiar.** No necesitas probar todo el sistema, solo lo que afectará tu cambio.
2. **Caracteriza** esa zona hasta tener confianza.
3. **Refactoriza en pasos pequeños**, sin cambiar el comportamiento, y con las herramientas automáticas del IDE.
4. **Añade la funcionalidad** con pruebas normales.
5. **Sustituye** las pruebas de caracterización por otras más claras cuando la intención ya sea evidente.

No mezcles refactorización y cambios de comportamiento en el mismo commit. Si una prueba falla en un commit que solo reorganiza, sabes que algo ha ido mal.

## Lo que no te dicen estas pruebas

Una prueba de caracterización pasada no indica que el comportamiento sea correcto. Solo que no ha cambiado. No las trates como una especificación, y deja claro en su nombre o en un comentario qué casos están fijando un error conocido.

## Referencias

- [Working Effectively with Legacy Code, de Michael Feathers](https://www.oreilly.com/library/view/working-effectively-with/0131177052/)
- [Verify](https://github.com/VerifyTests/Verify)
- [TimeProvider en .NET](https://learn.microsoft.com/dotnet/standard/datetime/timeprovider-overview)
