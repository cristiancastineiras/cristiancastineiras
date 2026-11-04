---
title: "Copias de seguridad en PostgreSQL: pg_dump, pg_basebackup y recuperación a un punto en el tiempo"
seoTitle: "Backups y PITR en PostgreSQL"
description: "Diferencias entre pg_dump y pg_basebackup, cómo funciona la recuperación a un punto en el tiempo con WAL y por qué una copia que no se ha restaurado no sirve de garantía."
date: 2026-07-20
tags: ["PostgreSQL", "Linux", "Operaciones"]
---

Solo hay una forma de saber si una copia de seguridad funciona: restaurarla. Hasta ese momento, es solo una suposición. Antes de elegir herramienta, conviene responder a dos preguntas:

- **RPO**: ¿cuántos datos puedes permitirte perder?
- **RTO**: ¿cuánto tiempo puedes tardar en volver a estar en servicio?

Con una copia diaria, puedes perder hasta un día de datos. Si eso no es aceptable, `pg_dump` no te basta por sí solo.

## pg_dump: copia lógica

Exporta el contenido de una base de datos como instrucciones o en un formato propio:

```bash
pg_dump -Fc -d aplicacion -f aplicacion.dump
```

El formato personalizado (`-Fc`) está comprimido y permite restaurar en paralelo y de forma selectiva:

```bash
pg_restore -d aplicacion_restaurada -j 4 aplicacion.dump
```

Es portable entre versiones mayores de PostgreSQL, ideal para migraciones y para recuperar una sola tabla. Sus limitaciones: no captura lo que ocurre después de la copia, y restaurar una base de datos grande puede llevar mucho tiempo, porque hay que recrear los índices.

También existe `pg_dumpall --globals-only`, necesario porque `pg_dump` no incluye roles.

## pg_basebackup: copia física

Copia los archivos del clúster completo:

```bash
pg_basebackup -D /copias/base -Ft -z -Xs -P
```

Restaurar es mucho más rápido, porque los archivos ya contienen los índices. Pero solo sirve para la misma versión mayor y arquitectura, y copia todo el clúster, no una base de datos concreta.

## WAL y recuperación a un punto en el tiempo

PostgreSQL escribe cada cambio en el WAL (*write-ahead log*) antes de aplicarlo. Si guardas esos archivos y tienes una copia física base, puedes reproducir todos los cambios hasta el momento que elijas.

Esto es la recuperación a un punto en el tiempo (PITR), que permite responder a «alguien ejecutó un `DELETE` sin `WHERE` a las 11:42».

```text
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /archivo/%f && cp %p /archivo/%f'
```

Para recuperar, restaura la copia base en un directorio vacío y configura el destino:

```text
restore_command = 'cp /archivo/%f %p'
recovery_target_time = '2026-07-14 11:41:00+02'
recovery_target_action = 'promote'
```

Después, crea el archivo `recovery.signal` y arranca el servidor. En la práctica, restaura en otro servidor, comprueba los datos y entonces decide cómo volver.

## Usa una herramienta

Escribir un `archive_command` robusto es más difícil de lo que parece: hay que tratar errores, verificar, retener y copiar fuera del servidor. Herramientas como pgBackRest o Barman ya resuelven todo esto:

```bash
pgbackrest --stanza=principal --type=full backup
pgbackrest --stanza=principal --type=time \
  "--target=2026-07-14 11:41:00+02" restore
```

Añaden copias incrementales, cifrado, compresión y envío a almacenamiento de objetos. Para cualquier cosa más allá de un entorno pequeño, yo empezaría por una de ellas.

## Una réplica no es una copia

Una réplica en streaming protege frente a fallos del servidor, pero reproduce los errores de inmediato. Un `DROP TABLE` llega a la réplica en milisegundos. Necesitas ambas cosas, porque cubren riesgos distintos.

## Automatizar la verificación

Una prueba periódica vale más que cualquier documento:

1. restaura la última copia en un entorno aislado;
2. arranca PostgreSQL y comprueba que no hay errores;
3. ejecuta algunas consultas, como el número de filas y la fecha más reciente de una tabla clave;
4. registra cuánto ha tardado y compáralo con tu RTO;
5. alerta si algo falla o si la copia es más antigua de lo esperado.

La regla 3-2-1 sigue vigente: tres copias, en dos soportes, una fuera del lugar principal. Además, cífralas y protege sus credenciales, porque contienen los mismos datos que tu base de datos.

## Referencias

- [Copia de seguridad y restauración](https://www.postgresql.org/docs/current/backup.html)
- [Archivado continuo y PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [pgBackRest](https://pgbackrest.org/)
