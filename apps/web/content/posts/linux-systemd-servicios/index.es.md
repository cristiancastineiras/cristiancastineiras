---
title: "systemd para desarrolladores: desplegar un servicio en Linux como es debido"
seoTitle: "systemd: desplegar servicios en Linux"
description: "Cómo ejecutar una aplicación .NET o Node.js con systemd: archivo de unidad, reinicios, variables de entorno, logs con journalctl, seguridad básica y temporizadores."
date: 2025-03-27
tags: ["Linux", "systemd", ".NET"]
---

No todo necesita Kubernetes ni contenedores. Para una API en un único servidor, una herramienta interna o un trabajo programado, systemd ya está instalado, y ofrece arranque automático, reinicios, logs y aislamiento. Dejar un proceso con `nohup` o dentro de un `screen` es algo que tarde o temprano acabará mal.

## Un servicio básico

Publica la aplicación, por ejemplo en `/opt/api`, y crea `/etc/systemd/system/api.service`:

```ini
[Unit]
Description=API de facturación
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=notify
User=api
Group=api
WorkingDirectory=/opt/api
ExecStart=/opt/api/Api
Restart=on-failure
RestartSec=5
EnvironmentFile=/etc/api/api.env
Environment=ASPNETCORE_URLS=http://127.0.0.1:5000

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now api
systemctl status api
```

`enable` hace que arranque con el sistema, y `--now` lo inicia en este momento.

## Tipos de servicio

Con `Type=notify`, systemd espera a que la aplicación indique que está lista. En .NET se activa con el paquete `Microsoft.Extensions.Hosting.Systemd`:

```csharp
builder.Host.UseSystemd();
```

También configura el formato de los logs y gestiona correctamente la señal de parada. Si no quieres añadir esa dependencia, con `Type=exec` o `simple`, systemd da el servicio por iniciado en cuanto lanza el proceso.

## Un usuario propio

No ejecutes como `root`:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin api
sudo chown -R api:api /opt/api
```

## Secretos fuera del archivo de unidad

Cualquier usuario puede ver una unidad con `systemctl cat`, de modo que no debes poner secretos en ella:

```bash
sudo install -d -m 750 -o root -g api /etc/api
sudo install -m 640 -o root -g api /dev/null /etc/api/api.env
```

```dotenv
ConnectionStrings__Principal=Host=localhost;Database=facturas;Username=api;Password=...
```

Recuerda: en .NET, el doble guion bajo equivale a `:` en la configuración. Para mayor seguridad, las versiones recientes de systemd ofrecen `LoadCredential=`, con la que el secreto no aparece en el entorno del proceso.

## Logs

No necesitas gestionar archivos, ni la rotación:

```bash
journalctl -u api -f                 # en directo
journalctl -u api --since "1 hour ago"
journalctl -u api -p err             # solo errores
journalctl -u api -b                 # desde el último arranque
```

Escribe a la salida estándar y systemd lo recoge. Si necesitas búsquedas complejas, puedes enviar el journal a un sistema central.

## Reinicios controlados

`Restart=on-failure` reinicia si falla, pero si la aplicación tiene un error al arrancar, entraría en un bucle. systemd lo limita:

```ini
[Unit]
StartLimitIntervalSec=300
StartLimitBurst=5
```

Tras 5 fallos en 5 minutos, deja de intentarlo y marca el servicio como fallido. Conviene monitorizar ese estado, y puedes reaccionar con `OnFailure=` para enviar una alerta.

## Aislamiento con pocas líneas

systemd puede restringir mucho un servicio sin contenedores:

```ini
[Service]
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/api
CapabilityBoundingSet=
```

- `ProtectSystem=strict` deja casi todo el sistema de archivos en solo lectura.
- `ReadWritePaths` indica lo que sí se puede escribir.
- `PrivateTmp` da un `/tmp` privado.

`systemd-analyze security api` evalúa el servicio, y sugiere mejoras. Añádelas poco a poco, comprobando que todo sigue funcionando.

## Delante, un proxy inverso

Deja la aplicación en `127.0.0.1`, y usa Nginx o Caddy para el TLS. Caddy obtiene y renueva los certificados de forma automática:

```text
api.ejemplo.com {
    reverse_proxy 127.0.0.1:5000
}
```

Con un proxy delante, ASP.NET Core necesita conocer las cabeceras reenviadas, para ver la IP y el esquema reales. Configura `UseForwardedHeaders` y limítalo a tu proxy.

## Trabajos programados

Los temporizadores sustituyen a `cron`, y tienen sus ventajas: logs integrados, dependencias y recuperación si la máquina estaba apagada:

```ini
# /etc/systemd/system/limpieza.timer
[Unit]
Description=Limpieza diaria

[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

Se acompaña de un `limpieza.service` con el mismo nombre y `Type=oneshot`. Para verlos, usa `systemctl list-timers`.

## Desplegar sin interrupciones

Una técnica sencilla es usar un enlace simbólico a la versión activa:

```bash
sudo cp -r publicacion /opt/api/releases/1.4.0
sudo ln -sfn /opt/api/releases/1.4.0 /opt/api/current
sudo systemctl restart api
```

Con `ExecStart=/opt/api/current/Api`, volver a la versión anterior se reduce a cambiar el enlace. Habrá un breve corte durante el reinicio. Si no es aceptable, necesitarás dos instancias detrás del proxy.

## Referencias

- [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [Hospedar ASP.NET Core en Linux con Nginx](https://learn.microsoft.com/aspnet/core/host-and-deploy/linux-nginx)
