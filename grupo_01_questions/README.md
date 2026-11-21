# Grupo 1 · Editor de preguntas y atributos

**Archivo principal:** `esb_questions.py`
**Clase entregable:** `QuestionEditor`
**Categoría del shell:** 2 — Módulo de adquisición de conocimiento.

Este módulo permite que el experto del dominio cree, edite, valide y guarde los **atributos y preguntas** que el shell experto hará al usuario, sin modificar el código del motor de inferencia. Produce la sección `attributes` de `conocimiento_dominio.json`.

## Integrantes

| Integrante | Usuario GitHub | Rol |
|---|---|---|
| Edward Liu (coordinador) | [@edwardliu2601](https://github.com/edwardliu2601) | Integrante C: interfaz, documentación, integración y revisión de PRs |
| José Luis Silvera | [@korruptful](https://github.com/korruptful) | Integrante A: modelo y persistencia JSON |
| Abdullah Patel | [@Abdullahpat20](https://github.com/Abdullahpat20) | Integrante B: lógica del editor y validación |

## Estado

- **Stub inicial (Semana 11):** listo. Las operaciones básicas en memoria (`add`, `edit`, `delete`, `get`, `list`) funcionan con pruebas.
- **Persistencia JSON (Integrante A):** implementada y con pruebas activas.
- **Pendiente (Sprint 1):** `validate()` y sus cuatro pruebas corresponden al Integrante B.

## Reparto de trabajo

### Integrante A — José Luis Silvera (modelo y persistencia)

- Implementar `QuestionEditor.save_to_json(path)` y `load_from_json(path)`.
- Serializar y deserializar los atributos respetando el contrato oficial acordado por la clase.
- Si el archivo destino ya tiene otras secciones (`meta`, `rules`), **preservarlas** y reemplazar solo `attributes`.
- Quitar el `@pytest.mark.skip` de las pruebas `test_round_trip_json` y `test_load_preserva_depends_on`, y asegurarse de que pasen.

### Integrante B — Abdullah Patel (lógica del editor y validación)

- Implementar `QuestionEditor.validate()` con, como mínimo:
  - `type` dentro de `TIPOS_VALIDOS` (`numeric`, `categorical`, `boolean`, `text`).
  - Si `type == "numeric"` y hay `range`: lista de 2 números con `min <= max`.
  - Si `type == "categorical"`: `options` no vacía y sin duplicados.
  - Si existe `depends_on`: el `attribute_id` referenciado existe y el `operator` está en `OPERADORES_VALIDOS`.
- Devolver `{"valido": bool, "errores": list[str]}`.
- Quitar el `@pytest.mark.skip` de las 4 pruebas de `validate_*`, y añadir más casos borde.

### Integrante C — Edward Liu (interfaz, documentación, integración)

- Construir un menú CLI interactivo (clase `QuestionEditorCLI` o funciones libres) que envuelva `QuestionEditor` y permita al experto usar el editor sin escribir código Python.
- Mantener este `README.md` y los datos de ejemplo (`datos_ejemplo/`).
- Coordinar con el **Grupo 2** (reglas) que los `attribute_id` que generamos aquí funcionen como referencia en sus condiciones.
- Coordinar con el **Grupo 4** (SchemaManager) que el JSON que escribimos pase su validación.
- Revisar los Pull Requests de los otros integrantes y mergearlos a `grupo-01`.

## API pública

### Dataclasses

```python
@dataclass
class Attribute:
    id: str                      # único, usado como referencia por G2/G5/G6/G7
    name: str                    # nombre legible
    type: str                    # numeric | categorical | boolean | text
    question: Optional[str] = None
    range: Optional[list[float]] = None    # [min, max] para numeric
    options: list[Any] = []                # para categorical
    help_text: Optional[str] = None        # ayuda para la interfaz
    depends_on: Optional[DependsOn] = None # pregunta condicional

@dataclass
class DependsOn:
    attribute_id: str
    operator: str                # ==, !=, >, <, >=, <=
    value: Any
```

### Clase `QuestionEditor`

| Método | Qué hace | Estado |
|---|---|---|
| `add_attribute(attr)` | Agrega un atributo nuevo | ✅ funciona |
| `edit_attribute(id, **changes)` | Modifica campos de un atributo | ✅ funciona |
| `delete_attribute(id)` | Elimina un atributo | ✅ funciona |
| `get_attribute(id)` | Devuelve un atributo | ✅ funciona |
| `list_attributes()` | Lista todos en orden de inserción | ✅ funciona |
| `validate()` | Verifica coherencia | ⏳ Sprint 1 — Abdullah |
| `save_to_json(path)` | Escribe la sección `attributes` | ✅ funciona |
| `load_from_json(path)` | Carga desde un JSON | ✅ funciona |

### Excepciones

- `AttributeExistsError`: se agrega un atributo cuyo `id` ya existe.
- `AttributeNotFoundError`: se busca, edita o borra un atributo inexistente.
- `ValidationError`: la base no cumple las reglas de validación.

## Dependencias con otros grupos

| Grupo | Qué necesita G1 | Para qué |
|---|---|---|
| G2 (reglas) | Los `attribute_id` que define G1, para referenciarlos en las condiciones de las reglas | Que las reglas sean coherentes con los atributos existentes |
| G4 (schema) | El esquema JSON final y la clase `SchemaManager` para validar nuestro output | Que el JSON que escribimos pase la validación común |
| G10 (interfaz) | Los campos `question`, `options`, `range`, `help_text`, `depends_on` para presentar las preguntas al usuario | Mostrar la pregunta correcta en el momento correcto |

| Grupo | Qué recibe de G1 |
|---|---|
| G2, G4, G5, G6, G10 | La sección `attributes` de `conocimiento_dominio.json` serializada correctamente |

## Contrato de atributos propuesto

Alineado con la propuesta del Grupo 4 (SchemaManager). G1 propone estas dos ampliaciones:

1. **`depends_on`** opcional en cada atributo, para preguntas condicionales (requisito del enunciado del proyecto).
2. **`help_text`** opcional en cada atributo, para que la interfaz pueda mostrar texto adicional al usuario.

Ambas ampliaciones son **opcionales**: un JSON sin estos campos sigue siendo válido.

## Ejecución de las pruebas

Desde la raíz del repositorio:

```bash
python -m pytest grupo_01_questions
```

Para ver también las pruebas marcadas como `skip` (pendientes):

```bash
python -m pytest grupo_01_questions -v
```

## Datos de ejemplo

El archivo `datos_ejemplo/conocimiento_dominio.sample.json` muestra el formato de salida esperado, incluyendo un caso de pregunta condicional (`nombre_tesis` solo se pregunta si `materia == "Trabajo de Graduacion"`).

## Flujo de trabajo del grupo

- **Edward (coordinador):** trabaja en ramas `grupo-01/<descripcion>` del repo central. Hace merge de los PRs de José Luis y Abdullah a `grupo-01`.
- **José Luis y Abdullah:** hacen **fork** del repo central, trabajan en su fork dentro de `grupo_01_questions/`, y abren Pull Request desde su fork hacia la rama `grupo-01`.
- Cuando el módulo esté terminado, Edward abre el PR final `grupo-01` → `develop`.


### Persistencia JSON

`save_to_json(path)` reemplaza únicamente `attributes` en un archivo existente;
conserva `meta`, `rules` y cualquier otra sección. En un archivo nuevo crea
metadatos iniciales y `rules: []`, siguiendo la estructura del ejemplo de G1.
Usa UTF-8 y conserva `depends_on`, `help_text` y el orden de los atributos.
`load_from_json(path)` reemplaza el estado solo después de leer todos los
atributos; rechaza IDs duplicados y no cambia el estado si la carga falla.
Los errores de lectura, JSON o serialización se propagan al llamador.

El contrato `contracts/conocimiento_dominio.schema.json` está actualmente en
`develop`, no en `grupo-01`. Exige al menos un atributo y una regla, mientras
que el ejemplo de G1 contiene `rules: []`. Por ello, un archivo nuevo sin reglas
es un documento de trabajo: G2 debe aportar reglas para validar el documento
completo. La persistencia no implementa `validate()` ni inventa reglas del dominio.
