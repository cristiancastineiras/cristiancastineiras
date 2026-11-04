---
title: "Symfony 8: qué cambia, qué se elimina y cómo actualizar desde 7.4"
seoTitle: "Symfony 8: novedades y actualización"
description: "Qué trae Symfony 8: PHP 8.4 como requisito, comandos invocables, configuración en PHP con array shapes, eliminación de XML, y un camino seguro para actualizar desde 7.4 LTS."
date: 2026-01-22
tags: ["Symfony", "PHP"]
---

Symfony 8.0 y 7.4 LTS se publicaron el mismo día, en noviembre de 2025, y tienen las mismas funcionalidades. La diferencia es que 8.0 elimina todo lo que estaba marcado como obsoleto y exige PHP 8.4. Por eso, la pregunta no es tanto qué hay de nuevo, sino qué versión te conviene.

## 7.4 LTS o 8.0

- **Symfony 7.4 LTS**: soporte a largo plazo. La opción natural para una aplicación empresarial que no quiere actualizarse cada pocos meses.
- **Symfony 8.0**: versión estándar, con soporte durante unos meses, hasta que llegue la siguiente menor.

Si quieres estabilidad, quédate en la LTS. Si puedes seguir el ritmo de actualizaciones, irás siempre al día. Tus dependencias también pueden influir en la decisión, porque algunos paquetes tardan en adaptarse.

## Comandos invocables

Los comandos ya no necesitan heredar de una clase base, ni separar la definición de sus argumentos. Se declaran con atributos en `__invoke`:

```php
#[AsCommand(name: 'app:crear-usuario', description: 'Crea un usuario')]
final class CrearUsuarioCommand
{
    public function __construct(private UsuarioManager $usuarios) {}

    public function __invoke(
        SymfonyStyle $io,
        #[Argument(description: 'Correo del usuario')] string $correo,
        #[Option(description: 'Con permisos de administración')] bool $admin = false,
    ): int {
        $this->usuarios->crear($correo, $admin);
        $io->success("Usuario {$correo} creado");

        return Command::SUCCESS;
    }
}
```

Los tipos de PHP definen los argumentos, de modo que hay menos código repetido. También se admiten enumeraciones, y hay atributos para enlazar un DTO completo o definir preguntas interactivas. Los comandos heredados siguen funcionando.

## Configuración: adiós a XML

Desaparecen los formatos XML y PHP *fluent*. Quedan YAML y un nuevo formato en PHP basado en arrays, con *array shapes*:

```php
// config/packages/framework.php
use Symfony\Component\DependencyInjection\Loader\Configurator\App;

return App::config([
    'framework' => [
        'secret' => '%env(APP_SECRET)%',
        'session' => ['enabled' => true],
    ],
]);
```

Las formas se generan a partir de tu propia configuración. Esto te da autocompletado y comprobación de tipos en el IDE, y además los archivos YAML obtienen un esquema JSON. Con YAML, no tienes que hacer nada. Si tenías configuración en XML en tu aplicación, sí tendrás que migrarla.

## Aprovechar PHP 8.4

Exigir esta versión permite eliminar código propio, y usar directamente funciones del lenguaje:

- objetos diferidos nativos, en lugar de generar clases proxy;
- *property hooks* y visibilidad asimétrica, en tus propias clases;
- un analizador HTML5 nativo para `DomCrawler` y `HtmlSanitizer`, que ahora interpreta los documentos como un navegador.

Comprueba el último punto si tus pruebas analizan HTML, porque pueden cambiar resultados en documentos mal formados.

## Otras novedades útiles

- **Formularios de varios pasos**: una forma estándar de implementar asistentes, algo que antes requería mucho código propio.
- **Atributos en extensiones de Twig**: definir filtros y funciones con atributos, sin clases adicionales.
- **Componentes más recientes**: mapeo de objetos, serialización JSON en flujo y otros que se han ido estabilizando.

## Cómo actualizar

El proyecto hace que este proceso sea predecible: como 8.0 equivale a 7.4 sin lo obsoleto, el trabajo se reduce a eliminar esas obsolescencias.

1. **Actualiza a la última versión de 7.4** y asegúrate de que las pruebas pasan.
2. **Actualiza PHP a 8.4** por separado, y comprueba tus extensiones.
3. **Elimina los avisos de obsolescencia**. Con `symfony/phpunit-bridge` los verás en las pruebas:

```bash
SYMFONY_DEPRECATIONS_HELPER='max[self]=0' ./vendor/bin/simple-phpunit
```

4. **Automatiza lo que puedas** con Rector, que incluye reglas específicas para Symfony:

```php
// rector.php
use Rector\Config\RectorConfig;

return RectorConfig::configure()
    ->withPaths([__DIR__.'/src'])
    ->withComposerBased(symfony: true)
    ->withAttributesSets(symfony: true);
```

5. **Actualiza las dependencias** en `composer.json`:

```json
{
  "extra": {
    "symfony": {
      "require": "8.0.*"
    }
  }
}
```

```bash
composer update "symfony/*" --with-all-dependencies
composer recipes:update
```

6. **Revisa los bundles de terceros**, que son lo que más suele bloquear este tipo de migraciones.

Hazlo en una rama, con un entorno de preproducción, y comprueba también los comandos de consola y los trabajos en segundo plano, porque las pruebas no siempre los cubren.

## Mi criterio

Para sistemas que deben durar años, me quedaría en 7.4 LTS e iría eliminando avisos de obsolescencia poco a poco. Así, el salto a la próxima LTS será un trámite. Si el proyecto es nuevo, y el equipo puede seguir el calendario, 8.x permite aprovechar antes lo último. Lo que no conviene es saltarse los avisos durante años, porque ahí es donde las actualizaciones se vuelven dolorosas.

## Referencias

- [Symfony 8](https://symfony.com/8)
- [Lanzamiento de Symfony 8.0](https://symfony.com/releases/8.0)
- [Actualizar una versión mayor](https://symfony.com/doc/current/setup/upgrade_major.html)
