---
title: "Git rebase o merge: cómo elegir y no perder trabajo por el camino"
seoTitle: "Git rebase o merge: cómo elegir"
description: "Qué hacen rebase y merge, cuándo conviene cada uno, cómo limpiar el historial antes de un pull request y cómo recuperarte de un error con git reflog."
date: 2025-01-23
tags: ["Git", "Productividad"]
---

La discusión entre `merge` y `rebase` suele plantearse como una cuestión de gusto. En realidad, responden a preguntas distintas: uno conserva lo que pasó, y el otro reescribe el historial para contar una historia más limpia.

## Qué hace cada uno

```text
Antes:
      A---B  feature
     /
C---D---E    main
```

**Merge** une las dos ramas con un commit nuevo:

```text
      A---B
     /     \
C---D---E---M  feature
```

**Rebase** vuelve a aplicar tus commits encima de la otra rama:

```text
              A'--B'  feature
             /
C---D---E
```

`A'` y `B'` son commits nuevos: tienen el mismo cambio, pero otro hash. Esta es la clave para entender el riesgo.

## La regla de oro

No hagas rebase de commits que otras personas ya estén usando.

Si alguien se ha basado en tu rama y la reescribes, tendrá copias divergentes de los mismos cambios. En tu propia rama de trabajo, en la que nadie más está trabajando, no hay ningún problema.

Al reescribir una rama ya publicada, usa siempre:

```bash
git push --force-with-lease
```

A diferencia de `--force`, falla si alguien ha subido algo que no tienes en local, lo que evita pisar su trabajo sin darte cuenta.

## Actualizar tu rama

```bash
git fetch origin
git rebase origin/main
```

Si hay conflictos, se resuelven commit a commit:

```bash
# Corrige los archivos y después:
git add .
git rebase --continue

# Si te lías, vuelve al estado inicial:
git rebase --abort
```

Con `git config --global rerere.enabled true`, Git recuerda cómo resolviste un conflicto y lo reaplica si vuelve a aparecer.

## Limpiar antes de un pull request

El rebase interactivo te permite reorganizar tus commits antes de publicarlos:

```bash
git rebase -i origin/main
```

```text
pick a1b2c3 Añade validación del NIF
fixup d4e5f6 arreglo errata
pick 789abc Añade pruebas de la validación
reword 0de123 wip
```

- `squash` y `fixup` unen un commit con el anterior.
- `reword` cambia el mensaje.
- Puedes cambiar el orden moviendo líneas.

Un truco para lo cotidiano: si detectas un error en un commit anterior, crea la corrección ya asociada a él.

```bash
git commit --fixup=a1b2c3
git rebase -i --autosquash origin/main
```

## Una estrategia de equipo

Lo importante es que todo el equipo siga la misma. Un flujo que funciona bien:

1. Ramas de corta duración, actualizadas con rebase.
2. Commits limpios antes de pedir la revisión.
3. Sin reescribir durante la revisión, para que quien revisa pueda ver lo que has cambiado desde la última vez. Añade commits nuevos.
4. Al fusionar, aplica la estrategia que haya elegido el equipo.

Las opciones más habituales al fusionar en GitHub o GitLab:

| Estrategia | Resultado | Cuándo |
|---|---|---|
| Squash | Un commit por pull request | Pull requests pequeños, con historial sencillo |
| Rebase | Historial lineal con todos los commits | Commits cuidados y con sentido propio |
| Merge commit | Conserva la rama | Necesitas saber qué se integró en cada momento |

Yo prefiero *squash* en la mayoría de los casos, con pull requests pequeños. El historial principal queda como una lista de cambios completos, cada uno revertible por separado, y facilita `git bisect`.

Cuando no conviene hacer rebase:

- en ramas compartidas, como `main` o `develop`;
- al integrar una rama de larga duración en la que muchas personas han trabajado;
- si tienes muchos commits y muchos conflictos. Un merge resuelve todos los conflictos de una vez, mientras que el rebase puede obligarte a resolver los mismos varias veces.

## Si algo sale mal

Git casi nunca pierde algo que ya estaba confirmado. `reflog` guarda por dónde ha pasado `HEAD`:

```bash
git reflog
```

```text
e4f5a6b HEAD@{0}: rebase (finish): returning to refs/heads/feature
1a2b3c4 HEAD@{5}: commit: Añade validación
```

Para volver al estado anterior:

```bash
git switch -c rescate 1a2b3c4
```

Crear una rama nueva es más seguro que usar `reset --hard`, ya que no modifica la rama en la que estás. Las entradas del reflog duran 90 días por defecto, aunque las que ya no son alcanzables desde una rama caducan a los 30.

Lo que no se puede recuperar es lo que nunca se llegó a confirmar. Antes de una operación arriesgada, un commit temporal o un `git stash` te dará un punto al que volver.

## Referencias

- [Pro Git: rebase](https://git-scm.com/book/es/v2/Ramificaciones-en-Git-Reorganizar-el-Trabajo-Realizado)
- [git-rebase](https://git-scm.com/docs/git-rebase)
