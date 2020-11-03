# Trapy

> Mi Nombre Es La Tiza (ymicorret@mbien.com)

Mi proyecto por supuesto que es la tiza.

## Recomendaciones

### Editor de texto

Se recomienda utilizar `VSCode`.

### *Virtual Environment*.

Instalar un ambiente virtual que contenga las dependencias de su proyecto.

```bash
virutualenv --python=python3.7 venv
```

Para activar el *virtual environment*

```bash
. venv/bin/activate
```

Para desactivarlo

```bash
deactivate
```

`VSCode` se integra correctamente con este tipo de flujo de trabajo, usando la
extensión [ms-python.python](https://marketplace.visualstudio.com/items?itemName=ms-python.python).

### *Linters*

Utilizar un *linter* que valide estáticamente su código. Se recomienda utilizar
`flake8`.

```bash
pip install flake8
```

En la configuración de `VSCode` puede utilizar

```json
{
    "python.linting.flake8Enabled": true,
    "python.linting.enabled": true
}
```
