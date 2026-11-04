---
title: "OIDC en GitHub Actions: despliega en la nube sin guardar secretos"
seoTitle: "OIDC en GitHub Actions"
description: "Cómo sustituir las credenciales de larga duración por tokens temporales con OIDC entre GitHub Actions, Azure y AWS, y cómo limitar qué repositorio y rama pueden usarlas."
date: 2025-10-16
tags: ["GitHub Actions", "Seguridad", "CI/CD"]
---

Durante años, desplegar desde CI ha significado guardar una clave de nube en un secreto del repositorio. Esa clave no caduca, suele tener demasiados permisos, y si se filtra, sirve desde cualquier sitio. OIDC elimina el problema de raíz: ya no hay ninguna clave que guardar.

## Cómo funciona

En vez de presentar un secreto, el workflow demuestra quién es:

1. GitHub emite un token firmado, con información sobre la ejecución: repositorio, rama, entorno.
2. El workflow lo presenta al proveedor de nube.
3. El proveedor comprueba la firma y las condiciones que has configurado.
4. Devuelve credenciales temporales, válidas para ese trabajo.

No hay nada que robar de la configuración del repositorio. Y un token filtrado caducaría enseguida.

## En el workflow

El job necesita permiso para pedir ese token:

```yaml
permissions:
  id-token: write
  contents: read
```

## Con Azure

Crea una identidad administrada o un registro de aplicación con una credencial federada, indicando el repositorio y lo que se autoriza:

```bash
az identity federated-credential create \
  --name github-produccion \
  --identity-name despliegue-api \
  --resource-group mi-grupo \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:mi-org/mi-repo:environment:produccion \
  --audiences api://AzureADTokenExchange
```

```yaml
jobs:
  desplegar:
    runs-on: ubuntu-24.04
    environment: produccion
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - run: az webapp deploy --name mi-api --resource-group mi-grupo --src-path app.zip
```

`client-id` y `tenant-id` no son secretos. Por eso van como variables.

## Con AWS

Registra GitHub como proveedor de identidad en IAM, y crea un rol con esta política de confianza:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:mi-org/mi-repo:environment:produccion"
        }
      }
    }
  ]
}
```

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/despliegue-api
    aws-region: eu-west-1
```

## El punto crítico: la condición `sub`

Toda la seguridad depende de esta comprobación. Si es demasiado amplia, cualquiera con la posibilidad de ejecutar un workflow podría asumir el rol:

| Valor de `sub` | Qué autoriza |
|---|---|
| `repo:org/repo:*` | Cualquier rama, y a veces pull requests. **Peligroso** |
| `repo:org/repo:ref:refs/heads/main` | Solo la rama `main` |
| `repo:org/repo:environment:produccion` | Solo el entorno `produccion` |

Lo mejor es usar un entorno, ya que permite añadir aprobaciones, restringir ramas y tiempos de espera. Sin eso, alguien con permiso de escritura podría crear un workflow en una rama cualquiera y, si la condición lo permite, conseguir credenciales de producción.

Evita los comodines en la organización o en el repositorio. Las reglas muy amplias eliminan casi toda la protección.

## Permisos del rol

OIDC resuelve cómo se obtienen las credenciales, no lo que se puede hacer con ellas. Limítalo a lo que el despliegue necesita. Un rol por entorno y por aplicación es una buena práctica. Si un repositorio se ve comprometido, los daños se limitan a su propio ámbito.

## Publicar paquetes

La misma idea se aplica a los registros de paquetes. npm ofrece *trusted publishing* desde GitHub Actions y GitLab, lo que permite retirar `NPM_TOKEN`:

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - run: npm publish
```

Debes configurar en npm el repositorio y el workflow autorizados.

## Migrar paso a paso

1. Haz un inventario de secretos en los repositorios.
2. Empieza por un entorno de pruebas, para familiarizarte.
3. Crea las identidades con el mínimo permiso.
4. Cambia el workflow, y verifica que no necesita el secreto.
5. Elimina el secreto del repositorio y revoca la clave en el proveedor.

El último paso se olvida con facilidad. Una clave que ya no usas sigue siendo una clave válida, por lo que hasta que no la revoques, no has eliminado el riesgo.

## Limitaciones

No todos los servicios admiten federación. Para los que no, sigue haciendo falta un secreto; rótalo periódicamente y exponlo solo en el paso que lo necesita. Otra opción es usar OIDC para acceder a un gestor de secretos, como Azure Key Vault, de forma que el repositorio no guarde nada.

## Referencias

- [OIDC en GitHub Actions](https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [Autenticación de Azure con OIDC](https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect)
- [Publicación de confianza en npm](https://docs.npmjs.com/trusted-publishers)
