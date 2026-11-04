---
title: "Diagnosticar un servidor Linux lento en cinco minutos"
seoTitle: "Diagnosticar un servidor Linux lento"
description: "Los comandos que conviene ejecutar cuando un servidor Linux va lento: carga, CPU, memoria, disco, red y procesos, y cómo interpretarlos sin sacar conclusiones erróneas."
date: 2025-07-31
tags: ["Linux", "Operaciones", "Rendimiento"]
---

Hay un aviso, la aplicación va lenta y alguien pregunta qué pasa. Antes de reiniciar, conviene dedicar cinco minutos a mirar, porque un reinicio borra las pruebas. Este es un recorrido ordenado, apto para casi cualquier máquina Linux, inspirado en el método de Brendan Gregg.

## 1. Situación general

```bash
uptime
```

```text
12:30:14 up 42 days, load average: 12.40, 8.10, 3.20
```

Los tres números son la carga media de 1, 5 y 15 minutos. Aquí va en aumento, de modo que el problema es reciente. Compáralo con el número de núcleos (`nproc`): 12 de carga en una máquina de 32 no es preocupante, y en una de 2, sí.

Una trampa: en Linux, la carga cuenta también los procesos esperando a disco. Una carga alta no siempre significa CPU saturada.

```bash
dmesg -T | tail -30
```

Es fácil olvidarlo y puede ahorrarte todo lo demás. Busca errores de disco o de red y el temido `Out of memory: Killed process`.

## 2. CPU

```bash
vmstat 1 5
```

```text
procs ---memory--- --swap-- --io-- -system-- ------cpu-----
 r  b  free  cache  si  so  bi  bo  in  cs  us sy id wa st
 9  0  812M  4.1G    0   0  12  40  ...     85  8  6  1  0
```

- `r`: procesos esperando CPU. Por encima del número de núcleos, hay saturación.
- `b`: procesos bloqueados, por lo general por disco.
- `us` y `sy`: tiempo en la aplicación y en el núcleo.
- `wa`: esperando a E/S.
- `st`: tiempo robado por el hipervisor. En una máquina virtual, puede indicar que otra máquina te está quitando recursos.

Después, mira quién la está usando:

```bash
top -o %CPU
pidstat 1 5
```

Si usas `mpstat -P ALL 1`, puedes detectar un único núcleo al 100 %, señal de un proceso que no usa hilos, o de una interrupción mal distribuida.

## 3. Memoria

```bash
free -h
```

```text
        total  used  free  shared  buff/cache  available
Mem:     16G    9G  500M    100M        6.5G       6.2G
Swap:     2G    0B    2G
```

Mira `available`, no `free`. Linux aprovecha la memoria libre como caché de disco, así que un `free` bajo es normal, y no significa que falte memoria.

Las señales reales de problema son:

- `available` muy bajo;
- `si` y `so` en `vmstat` con valores continuos: está usando la swap de forma activa, lo que hunde el rendimiento;
- mensajes del OOM killer en `dmesg`.

## 4. Disco

```bash
df -h
df -i
```

Un disco lleno causa fallos muy extraños. No olvides `df -i`: te puedes quedar sin inodos, con espacio libre todavía.

Para encontrar qué lo ocupa:

```bash
sudo du -xh --max-depth=1 /var | sort -h | tail
```

Si un archivo se ha borrado, pero un proceso sigue teniéndolo abierto, el espacio no se libera. Esto se ve con frecuencia en logs:

```bash
sudo lsof +L1
```

Para ver el rendimiento:

```bash
iostat -xz 1 5
```

- `%util`: cercano a 100 en un disco tradicional indica saturación. En un SSD o NVMe es menos fiable, porque atienden muchas peticiones en paralelo.
- `await`: tiempo medio de cada operación, en milisegundos. Compáralo con lo normal en esa máquina.

Para ver quién está escribiendo: `sudo iotop -o`, o `pidstat -d 1`.

## 5. Red

```bash
ss -s
ss -tan state time-wait | wc -l
sudo ss -tlnp
```

El primero da un resumen de conexiones. Muchísimos `TIME-WAIT` en un cliente pueden indicar que se crea una conexión por petición, algo típico al usar `HttpClient` de forma incorrecta. El último muestra qué proceso escucha en cada puerto.

Para errores y uso de ancho de banda:

```bash
ip -s link
sar -n DEV 1 5
```

Si sospechas de una dependencia, mide directamente:

```bash
curl -o /dev/null -s -w "dns=%{time_namelookup} conn=%{time_connect} tls=%{time_appconnect} total=%{time_total}\n" https://api.ejemplo.com/health
```

Con esto se distingue si el problema está en DNS, en la conexión, en TLS o en el servidor. Un DNS lento es una causa más común de lo que parece.

## 6. Dentro de un proceso

```bash
journalctl -u api --since "15 min ago" -p warning
cat /proc/PID/limits
ls /proc/PID/fd | wc -l
```

El último indica cuántos descriptores tiene abiertos. Si se acerca al límite, verás `Too many open files`. Para .NET, `dotnet-counters`, `dotnet-trace` y `dotnet-dump` permiten ver lo que está pasando dentro del proceso.

## Contenedores

Mira primero lo mismo, y después:

```bash
docker stats --no-stream
docker inspect --format '{{.State.OOMKilled}}' contenedor
```

Dentro de un contenedor, `free` y `top` pueden mostrar los datos de toda la máquina, y no los de sus límites. Ten cuidado para no sacar conclusiones equivocadas.

## Antes de reiniciar

Guarda lo que puedas: logs, salida de estos comandos y, si es una aplicación, un volcado de memoria. Luego, reiniciar puede restaurar el servicio, y no será problema. Pero sin datos, volverá a ocurrir, y seguirás sin saber por qué.

Si esto te resulta difícil de hacer en el momento, recoge estas métricas antes. `sar` guarda historial, y te permite ver qué pasaba a las 3 de la madrugada.

## Referencias

- [Linux Performance Analysis in 60,000 Milliseconds](https://netflixtechblog.com/linux-performance-analysis-in-60-000-milliseconds-accc10403c55)
- [Linux Performance, de Brendan Gregg](https://www.brendangregg.com/linuxperf.html)
