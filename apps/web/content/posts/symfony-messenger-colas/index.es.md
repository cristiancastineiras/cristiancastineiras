---
title: "Symfony Messenger: colas fiables, reintentos y workers en producción"
seoTitle: "Symfony Messenger en producción"
description: "Cómo usar Symfony Messenger para tareas en segundo plano: transportes, reintentos con espera, cola de fallos, workers bajo supervisión y mensajes idempotentes."
date: 2026-07-27
tags: ["Symfony", "PHP", "Arquitectura"]
---

Enviar un correo, generar un PDF o llamar a un servicio lento no debería retrasar la respuesta. Symfony Messenger permite mover ese trabajo a segundo plano con poco código. Lo complicado llega cuando un mensaje falla, un worker se queda sin memoria o el mismo mensaje se procesa dos veces.

## Mensaje y manejador

Un mensaje es una clase simple, y conviene que contenga datos, no entidades:

```php
final readonly class GenerarFactura
{
    public function __construct(public int $pedidoId) {}
}
```

```php
#[AsMessageHandler]
final class GenerarFacturaHandler
{
    public function __construct(
        private PedidoRepository $pedidos,
        private GeneradorFacturas $generador,
    ) {}

    public function __invoke(GenerarFactura $mensaje): void
    {
        $pedido = $this->pedidos->find($mensaje->pedidoId)
            ?? throw new UnrecoverableMessageHandlingException('Pedido inexistente');

        $this->generador->generar($pedido);
    }
}
```

Envía solo el identificador, y vuelve a consultar los datos. Una entidad serializada podría estar obsoleta cuando se procese. Y `UnrecoverableMessageHandlingException` indica que no tiene sentido reintentar.

```php
$bus->dispatch(new GenerarFactura($pedido->getId()));
```

## Transportes

```yaml
# config/packages/messenger.yaml
framework:
  messenger:
    failure_transport: fallidos

    transports:
      asincrono:
        dsn: '%env(MESSENGER_TRANSPORT_DSN)%'
        retry_strategy:
          max_retries: 3
          delay: 1000
          multiplier: 3
          max_delay: 60000
          jitter: 0.1
      fallidos: 'doctrine://default?queue_name=fallidos'

    routing:
      App\Message\GenerarFactura: asincrono
```

Sin la entrada en `routing`, el mensaje se procesa de forma síncrona. Es un error fácil de cometer y difícil de notar en desarrollo.

Con Doctrine como transporte, no necesitas ningún otro servicio:

```dotenv
MESSENGER_TRANSPORT_DSN=doctrine://default?auto_setup=0
```

Es una buena forma de empezar. Además, si el mensaje se guarda en la misma base de datos y dentro de la misma transacción que el cambio de negocio, evitas el problema de la doble escritura. Con mucho volumen, RabbitMQ, Redis o SQS serán mejores opciones.

## Fallos

Si un mensaje agota sus reintentos, pasa a la cola de fallos, y puedes actuar:

```bash
php bin/console messenger:failed:show
php bin/console messenger:failed:show 42 -vv
php bin/console messenger:failed:retry 42
php bin/console messenger:failed:remove 42
```

Crea una alerta sobre esta cola, o se llenará sin que nadie lo vea. Es, en la práctica, una lista de cosas que tus usuarios esperaban y que nunca ocurrieron.

## Workers en producción

```bash
php bin/console messenger:consume asincrono \
  --time-limit=3600 \
  --memory-limit=256M \
  --limit=1000
```

PHP no se diseñó para procesos de larga duración. Por eso, los workers deben reiniciarse periódicamente: los límites anteriores hacen que terminen de forma ordenada, y un supervisor los levanta otra vez.

```ini
# /etc/systemd/system/messenger-worker@.service
[Unit]
Description=Worker de Symfony Messenger %i

[Service]
User=www-data
WorkingDirectory=/var/www/app
ExecStart=/usr/bin/php bin/console messenger:consume asincrono --time-limit=3600
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now messenger-worker@{1..4}
```

## Al desplegar

Un worker tiene el código antiguo en memoria, y seguirá ejecutándolo. Avísale de que se detenga al terminar el mensaje actual:

```bash
php bin/console messenger:stop-workers
```

Esto requiere una caché compartida. Si cambias la clase de un mensaje, recuerda que puede haber otros antiguos en la cola: quita los campos en dos pasos, para no romper su deserialización.

## Procesar dos veces

Messenger entrega **al menos una vez**. Un worker puede caerse tras hacer el trabajo y antes de confirmar. Los manejadores deben tolerarlo:

```php
public function __invoke(GenerarFactura $mensaje): void
{
    if ($this->facturas->existeParaPedido($mensaje->pedidoId)) {
        return;
    }

    $this->generador->generar($mensaje->pedidoId);
}
```

Una restricción `UNIQUE` en la base de datos es la mejor garantía, ya que una comprobación previa no te protege frente a dos workers simultáneos.

## Doctrine en workers

El gestor de entidades acumula objetos, y una conexión puede cerrarse tras horas sin usarse. Messenger incluye *middlewares* que lo solucionan:

```yaml
framework:
  messenger:
    buses:
      messenger.bus.default:
        middleware:
          - doctrine_ping_connection
          - doctrine_close_connection
          - doctrine_transaction
```

## Prioridades

Puedes separar colas para que un informe enorme no retrase un correo de restablecimiento de contraseña:

```bash
php bin/console messenger:consume alta baja
```

Procesa primero la que aparece antes, y solo atiende la siguiente cuando la primera esté vacía.

## Probarlo

Con el transporte `in-memory://` en el entorno de pruebas, puedes comprobar lo que se ha enviado sin ejecutarlo. Además, prueba cada manejador directamente: al fin y al cabo, es una clase normal.

## Referencias

- [Messenger en la documentación de Symfony](https://symfony.com/doc/current/messenger.html)
