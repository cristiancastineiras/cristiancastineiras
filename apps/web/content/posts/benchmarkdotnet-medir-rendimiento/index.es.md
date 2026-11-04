---
title: "BenchmarkDotNet: mide antes de optimizar tu código .NET"
seoTitle: "BenchmarkDotNet: medir rendimiento"
description: "Cómo escribir microbenchmarks fiables con BenchmarkDotNet, leer sus resultados de tiempo y memoria y evitar las conclusiones falsas más habituales."
date: 2025-09-08
tags: [".NET", "C#", "Rendimiento"]
---

Un `Stopwatch` alrededor de un bucle mide muchas cosas: el calentamiento del JIT, el recolector de basura, lo que esté haciendo tu máquina. Cuando la diferencia que buscas está en los nanosegundos, ese número no sirve para decidir nada.

BenchmarkDotNet se ocupa de esa parte: calienta, repite, descarta valores atípicos y calcula márgenes de error.

## Un primer benchmark

Crea un proyecto de consola independiente y añade el paquete:

```bash
dotnet new console -n Benchmarks
cd Benchmarks
dotnet add package BenchmarkDotNet
```

```csharp
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Running;

BenchmarkRunner.Run<ConcatenacionBenchmarks>();

[MemoryDiagnoser]
public class ConcatenacionBenchmarks
{
    [Params(10, 1_000)]
    public int Elementos;

    private string[] _textos = [];

    [GlobalSetup]
    public void Preparar() =>
        _textos = Enumerable.Range(0, Elementos).Select(i => i.ToString()).ToArray();

    [Benchmark(Baseline = true)]
    public string ConConcatenacion()
    {
        var resultado = "";
        foreach (var texto in _textos) resultado += texto;
        return resultado;
    }

    [Benchmark]
    public string ConStringJoin() => string.Join("", _textos);
}
```

Ejecútalo siempre en `Release`:

```bash
dotnet run -c Release
```

## Cómo leer el resultado

La tabla incluye varias columnas:

- **Mean**: tiempo medio por operación.
- **Error** y **StdDev**: si son grandes respecto a la media, el resultado es inestable.
- **Ratio**: comparación con el método marcado como `Baseline`.
- **Allocated**: memoria asignada por operación, gracias a `[MemoryDiagnoser]`.

La columna de memoria es a menudo la más reveladora. En un servidor con mucha carga, reducir asignaciones significa menos trabajo para el recolector, y eso se nota en la latencia de los percentiles altos.

## Errores que invalidan una medición

**Dejar que el compilador elimine el trabajo.** Si un cálculo no se usa, el JIT puede quitarlo. Devuelve siempre el resultado desde el método.

**Trabajar con datos irreales.** Un benchmark con 10 elementos no dice nada de lo que pasa con 100 000. Usa `[Params]` para cubrir tamaños representativos.

**Preparar datos dentro del método.** Lo que hay dentro de `[Benchmark]` se mide. La preparación va en `[GlobalSetup]`.

**Optimizar lo que no importa.** Un método diez veces más rápido que se ejecuta una vez por petición, al lado de una consulta de 40 ms, no cambia nada. Primero localiza el cuello de botella con un perfilador o con trazas; después usa BenchmarkDotNet para comparar alternativas sobre esa parte concreta.

## Comparar entre versiones de .NET

Puedes ejecutar el mismo benchmark en varios runtimes. Es útil para justificar una migración con datos de tu propio código:

```csharp
[SimpleJob(RuntimeMoniker.Net80)]
[SimpleJob(RuntimeMoniker.Net90)]
[MemoryDiagnoser]
public class ConcatenacionBenchmarks { /* ... */ }
```

Hay que declarar ambos frameworks en `TargetFrameworks` del proyecto.

## Qué no hacer en CI

Los runners compartidos tienen un rendimiento variable, así que comparar tiempos absolutos entre ejecuciones da falsas alarmas. Si quieres vigilar regresiones, las asignaciones de memoria son una señal mucho más estable, porque no dependen de la velocidad de la máquina.

## Referencias

- [Documentación de BenchmarkDotNet](https://benchmarkdotnet.org/articles/overview.html)
