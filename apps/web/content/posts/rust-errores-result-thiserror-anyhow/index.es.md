---
title: "Manejo de errores en Rust: Result, thiserror y anyhow sin confusión"
seoTitle: "Errores en Rust: thiserror y anyhow"
description: "Cómo gestionar errores en Rust con Result y el operador ?, cuándo usar thiserror y cuándo anyhow, cómo añadir contexto, y por qué conviene evitar unwrap fuera de pruebas."
date: 2026-08-24
tags: ["Rust"]
---

Rust no tiene excepciones. Una función que puede fallar lo declara en su tipo de retorno, y quien llama debe decidir qué hacer. Al principio resulta verboso, pero se reduce mucho con las herramientas adecuadas. La duda suele ser qué librería usar en cada caso.

## `Result` y el operador `?`

```rust
use std::fs;

fn leer_configuracion(ruta: &str) -> Result<String, std::io::Error> {
    let contenido = fs::read_to_string(ruta)?;
    Ok(contenido.trim().to_string())
}
```

`?` significa: si es un `Err`, devuélvelo ya; si es `Ok`, extrae el valor. Además, convierte el error con `From` si los tipos no coinciden. Es lo que hace llevadero este modelo.

No se puede ignorar un `Result` sin que el compilador avise. Compáralo con una excepción, que puede atravesar diez capas sin que ninguna firma lo indique.

## `unwrap` y `expect`

```rust
let puerto: u16 = texto.parse().unwrap();
```

Si falla, el programa entra en *panic*. Es razonable en pruebas, en prototipos y cuando algo que falla significa un error de programación. Si lo usas por un invariante, `expect` explica el motivo:

```rust
let patron = Regex::new(r"^\d+$").expect("la expresión regular es una constante válida");
```

Para errores que dependen del exterior, como archivos, red o entrada del usuario, no los uses.

## Librerías: `thiserror`

Si los consumidores necesitan distinguir unos errores de otros, define un tipo. `thiserror` genera el código repetitivo:

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("no se pudo leer {ruta}")]
    Lectura {
        ruta: String,
        #[source]
        origen: std::io::Error,
    },

    #[error("formato no válido")]
    Formato(#[from] toml::de::Error),

    #[error("falta la clave obligatoria {0}")]
    ClaveAusente(String),
}

pub fn cargar(ruta: &str) -> Result<Config, ConfigError> {
    let texto = std::fs::read_to_string(ruta).map_err(|origen| ConfigError::Lectura {
        ruta: ruta.to_string(),
        origen,
    })?;

    let config: Config = toml::from_str(&texto)?; // usa #[from]
    Ok(config)
}
```

Quien llama puede actuar según la variante:

```rust
match cargar("config.toml") {
    Ok(config) => iniciar(config),
    Err(ConfigError::ClaveAusente(clave)) => eprintln!("Añade {clave} a la configuración"),
    Err(error) => return Err(error.into()),
}
```

## Aplicaciones: `anyhow`

En el nivel superior de una aplicación, muchas veces solo quieres informar del error y terminar. `anyhow::Error` puede contener cualquier error y añadirle contexto:

```rust
use anyhow::{Context, Result, bail};

fn main() -> Result<()> {
    let ruta = std::env::args().nth(1).context("Falta la ruta del archivo")?;

    let texto = std::fs::read_to_string(&ruta)
        .with_context(|| format!("No se pudo leer {ruta}"))?;

    if texto.is_empty() {
        bail!("El archivo {ruta} está vacío");
    }

    println!("{} líneas", texto.lines().count());
    Ok(())
}
```

Si falla, el programa imprime toda la cadena:

```text
Error: No se pudo leer datos.txt

Caused by:
    No such file or directory (os error 2)
```

`with_context` recibe una función, de modo que el texto solo se construye si hay un error.

## La regla

- **`thiserror` en librerías**: errores con tipo que el consumidor puede tratar.
- **`anyhow` en aplicaciones**: propagar con contexto hacia un punto donde se informa.

Se pueden combinar: los módulos internos de una aplicación pueden tener sus tipos con `thiserror`, y `main` los recibe con `anyhow`. No expongas `anyhow::Error` en la API pública de una librería, porque obligas a tus usuarios a inspeccionar textos para distinguir errores.

## El contexto es lo que más ayuda

Un `No such file or directory` a secas es inútil. ¿Qué archivo? ¿Qué se intentaba hacer? Añade contexto en cada nivel que aporte información nueva, sin repetirlo:

```rust
let datos = descargar(&url)
    .await
    .with_context(|| format!("Error al descargar el informe de {cliente}"))?;
```

## `Option` no es un error

`Option` indica que algo puede no existir, sin que sea un fallo. Se puede convertir cuando la ausencia sí lo sea:

```rust
let usuario = buscar(id).ok_or(ApiError::NoEncontrado)?;
```

## Paralelismo con C#

Si vienes de .NET, es parecido a modelar errores esperados como un tipo de resultado, y dejar las excepciones para lo inesperado. `panic` se aproxima a una excepción no controlada: es para lo que no debería pasar. La diferencia es que en Rust el modelo es obligatorio, y el compilador lo hace cumplir.

## Referencias

- [El libro de Rust: manejo de errores](https://doc.rust-lang.org/book/ch09-00-error-handling.html)
- [thiserror](https://docs.rs/thiserror)
- [anyhow](https://docs.rs/anyhow)
