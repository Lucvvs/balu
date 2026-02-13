# Datos de Regiones y Comunas de Chile

## Ubicación del archivo

Coloca tu archivo JSON con las regiones y comunas de Chile en esta carpeta con el nombre:

**`regiones_comunas.json`**

## Estructura del JSON

El archivo puede tener cualquiera de estas estructuras:

### Opción 1: Lista de regiones con comunas
```json
[
  {
    "region": "Arica y Parinacota",
    "comunas": ["Arica", "Camarones", "Putre", "General Lagos"]
  },
  {
    "region": "Tarapacá",
    "comunas": ["Iquique", "Alto Hospicio", "Pozo Almonte", "Camiña"]
  }
]
```

### Opción 2: Lista con campo "nombre"
```json
[
  {
    "nombre": "Arica y Parinacota",
    "comunas": ["Arica", "Camarones", "Putre", "General Lagos"]
  }
]
```

### Opción 3: Objeto con clave "regiones"
```json
{
  "regiones": [
    {
      "nombre": "Arica y Parinacota",
      "comunas": ["Arica", "Camarones", "Putre", "General Lagos"]
    }
  ]
}
```

### Opción 4: Objeto con regiones como claves
```json
{
  "Arica y Parinacota": {
    "comunas": ["Arica", "Camarones", "Putre", "General Lagos"]
  },
  "Tarapacá": {
    "comunas": ["Iquique", "Alto Hospicio", "Pozo Almonte", "Camiña"]
  }
}
```

### Opción 5: Comunas como objetos
```json
[
  {
    "region": "Arica y Parinacota",
    "comunas": [
      {"nombre": "Arica"},
      {"comuna": "Camarones"},
      {"name": "Putre"}
    ]
  }
]
```

## Uso en el código

Las funciones en `shop/utils.py` detectan automáticamente la estructura y cargan los datos correctamente.

## Verificación

Para verificar que el archivo se carga correctamente, puedes ejecutar en el shell de Django:

```python
from shop.utils import get_regiones_choices, get_comunas_choices

# Obtener todas las regiones
regiones = get_regiones_choices()
print(regiones)

# Obtener comunas de una región específica
comunas = get_comunas_choices("Arica y Parinacota")
print(comunas)
```
