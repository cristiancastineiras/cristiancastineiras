---
title: "Ownership en Rust explicado para quien viene de C#"
seoTitle: "Ownership en Rust para devs de C#"
description: "Ownership, préstamos y lifetimes explicados desde C#: qué sustituye al recolector de basura, cómo leer los errores del compilador y equivalencias entre ambos lenguajes."
date: 2026-02-26
tags: ["Rust", "C#"]
---

En C#, el recolector de basura se ocupa de la memoria, y puedes pasar referencias libremente. En Rust no hay recolector, ni necesitas liberar a mano: el compilador sigue quién es dueño de cada valor. Es lo que más cuesta al principio, y lo que hace posibles sus garantías.

## Mover en lugar de copiar referencias

En C#, esto crea dos referencias al mismo objeto:

```csharp
var a = new List<int> { 1, 2, 3 };
var b = a;
Console.WriteLine(a.Count); // funciona
```

En Rust, una asignación **mueve** el valor, y el nombre anterior deja de ser válido:

```rust
let a = vec![1, 2, 3];
let b = a;
println!("{}", a.len()); // error: borrow of moved value `a`
```

Cada valor tiene un único dueño. Cuando este sale de ámbito, el valor se libera, de forma determinista. Es parecido a tener un `using` implícito en todo.

Los tipos simples, como `i32` o `bool`, implementan `Copy`, y se copian sin más, como un `struct` pequeño de C#. Si quieres duplicar otro tipo, debes pedirlo con `a.clone()`, de modo que el coste queda a la vista.

## Prestar en lugar de mover

Para usar un valor sin quedártelo, lo tomas prestado:

```rust
fn longitud(texto: &String) -> usize {
    texto.len()
}

let nombre = String::from("Ana");
let total = longitud(&nombre);
println!("{nombre} tiene {total} letras"); // nombre sigue siendo válido
```

En la práctica, se escribe `&str` en lugar de `&String`, porque acepta también literales y trozos de texto.

## La regla central

En un momento dado, puedes tener una de estas dos cosas, nunca ambas:

- varias referencias de solo lectura (`&T`);
- una única referencia mutable (`&mut T`).

```rust
let mut lista = vec![1, 2, 3];

let primero = &lista[0];
lista.push(4); // error: no se puede mutar mientras hay un préstamo activo
println!("{primero}");
```

Parece un capricho, pero evita un error real: `push` puede mover el vector a otra zona de memoria, y `primero` apuntaría a memoria liberada. En C#, un caso parecido es modificar una lista mientras la recorres, que falla en ejecución con `InvalidOperationException`. Rust lo detecta al compilar.

Esta misma regla evita las condiciones de carrera: si nadie más puede leer mientras escribes, no hay carrera posible.

## Lifetimes

A veces el compilador necesita saber cuánto vive una referencia:

```rust
fn mas_larga<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() > b.len() { a } else { b }
}
```

`'a` no cambia cuánto vive nada. Solo declara una relación: el resultado no puede vivir más que las entradas. La mayoría de las veces el compilador las deduce, y no tendrás que escribirlas.

Un consejo para empezar: si te encuentras peleando con lifetimes en una `struct`, usa tipos con propiedad, como `String` en lugar de `&str`. Clonar algo de vez en cuando es perfectamente válido mientras aprendes.

## Equivalencias

| C# | Rust |
|---|---|
| `string` | `String` (con propiedad) y `&str` (prestado) |
| `List<T>` | `Vec<T>` |
| `Dictionary<K, V>` | `HashMap<K, V>` |
| `T?` | `Option<T>` |
| Excepciones | `Result<T, E>` y el operador `?` |
| `interface` | `trait` |
| `IDisposable` y `using` | `Drop`, automático |
| `Task<T>` y `async` | `Future` y `async`, con un runtime como Tokio |
| `lock` | `Mutex<T>`, que envuelve los datos que protege |
| Objeto compartido | `Rc<T>` o `Arc<T>` |

## Compartir de verdad

Cuando necesitas varios dueños, como compartir datos entre hilos, lo indicas de forma explícita:

```rust
use std::sync::{Arc, Mutex};
use std::thread;

let contador = Arc::new(Mutex::new(0));
let mut hilos = vec![];

for _ in 0..4 {
    let contador = Arc::clone(&contador);
    hilos.push(thread::spawn(move || {
        *contador.lock().unwrap() += 1;
    }));
}

for hilo in hilos {
    hilo.join().unwrap();
}

println!("{}", *contador.lock().unwrap());
```

Fíjate en que `Mutex` contiene el dato. No se puede acceder a él sin obtener el bloqueo, y el compilador lo garantiza. En C#, nada impide usar un campo sin su `lock`.

## Lee los errores del compilador

Los mensajes de Rust suelen explicar el problema e incluso proponer la solución. Tratarlos como una conversación en vez de un obstáculo cambia mucho la experiencia. `cargo clippy` añade además consejos idiomáticos.

## ¿Merece la pena para alguien de .NET?

Para APIs de negocio, C# suele ser más productivo: el GC simplifica mucho y el rendimiento es muy bueno. Rust compensa en herramientas de línea de comandos, componentes con requisitos estrictos de memoria o latencia, y binarios autónomos pequeños. Aprenderlo también mejora tu forma de pensar: empezarás a preguntarte quién es dueño de cada dato, también en C#.

## Referencias

- [El libro de Rust: ownership](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html)
- [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
