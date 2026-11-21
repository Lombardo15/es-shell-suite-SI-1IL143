# Grupo 4 — SchemaManager

**Proyecto:** ES-Shell Suite · Sistema experto modular en Python  
**Responsabilidad:** validación de contratos JSON y consistencia de conocimiento, memorias de trabajo y dictámenes.  
**Versión utilizada como base:** código compartido por el equipo el 17/11/2026.

## 1. Descripción

`SchemaManager` es el componente de validación del **Grupo 4**. Comprueba que los documentos intercambiados entre los módulos del sistema experto respeten los contratos JSON y, cuando corresponde, verifica relaciones semánticas entre atributos, reglas, hechos, trazas y resultados.

**Este módulo no ejecuta las reglas de inferencia, no calcula calificaciones y no decide qué pregunta hacer.** Su función es detectar inconsistencias y comunicar errores para que otros componentes puedan gestionarlos.

### Qué valida

- **Conocimiento del dominio:** estructura, identificadores duplicados, referencias a atributos, condiciones, rangos, dependencias circulares y versión.
- **Memoria de trabajo:** estructura y valores de los hechos registrados, incluso cuando la recopilación aún está incompleta.
- **Completitud:** presencia de los atributos que otro módulo haya definido como necesarios para una consulta.
- **Trazas y hechos derivados:** correspondencia de las reglas indicadas, los hechos producidos y los registros de ejecución.
- **Dictamen de salida:** estructura, identificación de la sesión y, opcionalmente, coincidencia con el hecho derivado elegido como resultado final.

## 2. Estructura de archivos

Las rutas siguientes son relativas a la raíz del repositorio:

```text
grupo_04_schema/
├── __init__.py
├── esb_schema.py                  # Clase SchemaManager
├── README.md                      # Guía del módulo
├── schemas/
│   ├── conocimiento_dominio.schema.json
│   ├── memoria_trabajo.schema.json
│   └── dictamen_salida.schema.json
├── ejemplos/
│   ├── conocimiento_dominio.json
│   ├── memoria_trabajo.json
│   ├── dictamen_salida.json
│   └── casos/
│       ├── repeticion_a/
│       └── repeticion_d/
├── tests/
│   ├── __init__.py
│   ├── test_schema.py             # 107 pruebas unitarias
│   ├── test_integracion_schema.py # 19 pruebas de integración parcial
│   ├── resultado_pruebas.txt      # Evidencia de 126 pruebas del Grupo 4
│   └── resultado_integracion.txt  # Evidencia de integración
└── documentacion/
    ├── base_conocimiento_academico.md
    ├── acuerdos_coordinacion_grupo_04.md
    └── registro_pruebas_integracion.md
```

Los contratos compartidos del proyecto se encuentran también en `contracts/`, en la raíz del repositorio. **No se deben modificar unilateralmente**: los cambios de contrato requieren coordinación entre los grupos según `CONTRIBUTING.md`.

## 3. Requisitos y preparación

- **Python 3.11 o superior** (convención del repositorio).
- **`jsonschema`** para validar los contratos basados en JSON Schema Draft 2020-12.
- **`pytest`** para ejecutar las pruebas unitarias.
- `json`, `pathlib`, `math` y `threading` son parte de la biblioteca estándar de Python.

Desde la **raíz del repositorio** (la carpeta que contiene `grupo_04_schema/`), instala las dependencias del módulo:

```bash
python -m pip install jsonschema pytest
```

Para trabajar en Windows con PowerShell, abre la carpeta del repositorio antes de ejecutar los ejemplos. No es necesario modificar `PYTHONPATH` cuando los comandos se ejecutan desde esa raíz.

## 4. Contratos JSON soportados

| Identificador utilizado en la API | Archivo de esquema | Documento |
| --- | --- | --- |
| `conocimiento_dominio` | `conocimiento_dominio.schema.json` | Metadatos, atributos y reglas IF–THEN. |
| `memoria_trabajo` | `memoria_trabajo.schema.json` | Identificador de sesión, hechos, hechos derivados y traza. |
| `dictamen_salida` | `dictamen_salida.schema.json` | Resultado final y explicaciones HOW/WHY. |

**Campos principales** (consultar los archivos `.schema.json` para las restricciones completas):

| Documento | Campos obligatorios principales |
| --- | --- |
| Conocimiento | `meta`, `attributes`, `rules` |
| Memoria | `session_id`, `facts`, `derived_facts`, `execution_trace` |
| Dictamen | `session_id`, `final_outcome`, `explanation_how`, `explanation_why` |

En el conocimiento, los tipos admitidos para atributos son `numeric`, `categorical`, `boolean` y `text`. Para atributos numéricos se admiten **enteros y decimales**; si existe `range`, sus extremos se comprueban de manera inclusiva al validar los hechos.

### Forma de los resultados

La mayoría de los métodos de validación devuelve un diccionario:

```python
{"valido": True, "errores": []}
```

Si hay problemas, devuelve `"valido": False` y una lista de mensajes en `"errores"`. Los errores pueden incluir una ruta como `$.facts.puntaje_final` para señalar el dato afectado.

**Excepción:** `validar_completitud()` tiene un formato propio: `{"completa": bool, "faltantes": list[str]}`.

## 5. Referencia de la API

Se importa la clase con:

```python
from grupo_04_schema.esb_schema import SchemaManager

gestor = SchemaManager()
```

### Configuración y carga

| Método | Función y resultado |
| --- | --- |
| `SchemaManager(carpeta_esquemas=None, versiones_admitidas=None)` | Constructor. Usa `grupo_04_schema/schemas/` por defecto; permite seleccionar otra carpeta y restringir versiones aceptadas del conocimiento. |
| `cargar_json(ruta)` | Lee un archivo JSON UTF-8 (también con BOM). Rechaza las constantes no estándar `NaN` e `Infinity`. Devuelve el objeto cargado; los errores de lectura o formato se propagan. |
| `limpiar_cache_esquemas()` | Vacía la caché interna de validadores, sin devolver un resultado de validación. |
| `validar_archivo(ruta, tipo)` | Lee y valida un archivo por su tipo de contrato. Convierte errores de lectura o del esquema a `{"valido", "errores"}`. |

### Validación de documentos y relaciones

| Método | Qué comprueba |
| --- | --- |
| `validar_datos(datos, tipo)` | El esquema del tipo indicado; para conocimiento añade validaciones semánticas, de condiciones, dependencias circulares y versión. |
| `validar_conocimiento(conocimiento)` | Identificadores de atributos y reglas duplicados; referencias de condiciones; rangos numéricos mal definidos. |
| `validar_condiciones(conocimiento)` | Operadores y valores compatibles con los tipos de atributos; referencias en reglas y `depends_on`. |
| `validar_dependencias_circulares(conocimiento)` | Ciclos entre relaciones `depends_on`. |
| `validar_version(conocimiento)` | `meta.version` no vacía y, cuando se haya configurado, incluida entre las versiones admitidas. |
| `validar_memoria(memoria, conocimiento)` | Estructura de ambos documentos y validez de los hechos existentes respecto a los atributos declarados. **No exige una memoria completa**. |
| `validar_completitud(memoria, atributos_requeridos)` | Presencia de nombres en `memoria["facts"]`; devuelve cuáles faltan. **No valida los valores**. |
| `validar_traza(memoria, conocimiento)` | Validación de memoria y coherencia entre reglas referenciadas, hechos derivados y traza. |
| `validar_dictamen(dictamen, memoria, atributo_resultado=None)` | Estructura del dictamen y la memoria, coincidencia de sesión y, si se indica `atributo_resultado`, coincidencia con el hecho derivado. |
| `validar_conjunto(conocimiento, memoria, dictamen, atributo_resultado=None)` | Validación conjunta de contratos, hechos, traza y relación entre dictamen y memoria. |

Los métodos semánticos de bajo nivel (`validar_conocimiento`, `validar_condiciones` y `validar_dependencias_circulares`) devuelven **listas de mensajes de error** y esperan que el conocimiento tenga previamente la estructura válida. Para una verificación completa del conocimiento se recomienda `validar_datos(conocimiento, "conocimiento_dominio")`.

`validar_datos()` lanza `ValueError` si recibe un tipo de contrato desconocido. Para validar archivos con manejo de errores de lectura o de configuración del esquema, utilizar `validar_archivo()`.

## 6. Ejemplo de uso completo

Ejecutar desde la raíz del repositorio. Este ejemplo utiliza los JSON incluidos en `grupo_04_schema/ejemplos/`; **no crea reglas ni ejecuta inferencia**.

```python
from pathlib import Path
from grupo_04_schema.esb_schema import SchemaManager

base = Path("grupo_04_schema/ejemplos")
gestor = SchemaManager()

conocimiento = gestor.cargar_json(base / "conocimiento_dominio.json")
memoria = gestor.cargar_json(base / "memoria_trabajo.json")
dictamen = gestor.cargar_json(base / "dictamen_salida.json")

# Validar el contrato y la semántica del conocimiento.
print(gestor.validar_datos(conocimiento, "conocimiento_dominio"))

# Validar solo los hechos que ya existen en la memoria.
print(gestor.validar_memoria(memoria, conocimiento))

# Consultar cuáles datos se requieren para calificación.
requeridos = ["tipo_consulta", "puntaje_final"]
print(gestor.validar_completitud(memoria, requeridos))

# Comprobar trazas, resultado final y los tres documentos en conjunto.
print(gestor.validar_traza(memoria, conocimiento))
print(gestor.validar_dictamen(dictamen, memoria, "dictamen"))
print(gestor.validar_conjunto(conocimiento, memoria, dictamen, "dictamen"))
```

Con los archivos de ejemplo sin modificar, los métodos de validación anteriores devuelven `{"valido": True, "errores": []}` y la comprobación de completitud devuelve `{"completa": True, "faltantes": []}`.

### Ejemplo de memoria aún incompleta

```python
memoria_parcial = {
    "session_id": "sesion_pendiente",
    "facts": {"tipo_consulta": "Calificacion"},
    "derived_facts": {},
    "execution_trace": [],
}

print(gestor.validar_memoria(memoria_parcial, conocimiento))
# {"valido": True, "errores": []}

print(gestor.validar_completitud(
    memoria_parcial, ["tipo_consulta", "puntaje_final"]
))
# {"completa": False, "faltantes": ["puntaje_final"]}
```

La memoria puede ser estructural y semánticamente válida sin disponer todavía de toda la información de la consulta. La completitud es una comprobación **separada**.

## 7. Dominio académico utilizado en los ejemplos

La base `ejemplos/conocimiento_dominio.json` incluye dos consultas:

| Consulta | Atributos requeridos para procesarla |
| --- | --- |
| `Calificacion` | `tipo_consulta`, `puntaje_final` |
| `Repeticion` | `tipo_consulta`, `nota_obtenida` |

La consulta `Calificacion` contiene estas reglas de ejemplo, que aceptan valores decimales sin dejar intervalos sin cubrir:

| Calificación | Intervalo de `puntaje_final` |
| --- | --- |
| A | `91 ≤ puntaje ≤ 100` |
| B | `81 ≤ puntaje < 91` |
| C | `71 ≤ puntaje < 81` |
| D | `61 ≤ puntaje < 71` |
| F | `0 ≤ puntaje < 61` |

El atributo `nota_obtenida` de la consulta `Repeticion` admite `A`, `B`, `C`, `D` y `F`. Las reglas de ejemplo tratan `D` y `F` como las notas que cumplen el criterio definido de repetición para mejorar el índice académico.

**Importante:** las reglas anteriores están definidas en el JSON de ejemplo. `SchemaManager` valida ese conocimiento, pero no calcula por sí mismo la calificación ni determina si se debe repetir una asignatura.

## 8. Pruebas unitarias

Las pruebas del Grupo 4 están en `grupo_04_schema/tests/test_schema.py`. Cubren contratos, memoria, completitud, reglas y condiciones, dependencias, traza, dictamen, validación conjunta, lectura de archivos, versiones, caché y casos límite.

Desde la raíz del repositorio:

**Windows (PowerShell):**

```powershell
python -m pytest .\grupo_04_schema\tests\test_schema.py -v -rs
```

**Linux:**

```bash
python3 -m pytest grupo_04_schema/tests/test_schema.py -v -rs
```

Para guardar evidencia en Windows:

```powershell
python -m pytest .\grupo_04_schema\tests -v -rs |
    Tee-Object -FilePath .\grupo_04_schema\tests\resultado_pruebas.txt
```

**Últimos resultados verificados en Windows:** `107 passed` para `test_schema.py`, `19 passed` para `test_integracion_schema.py` y `126 passed` para el conjunto `grupo_04_schema/tests/` (0 fallidas y 0 omitidas). El número puede variar si se agregan o cambian pruebas.

Para ejecutar únicamente las 19 pruebas de integración parcial:

```powershell
python -m pytest .\grupo_04_schema\tests\test_integracion_schema.py -v -rs
```

Los resultados y sus límites están documentados en `documentacion/registro_pruebas_integracion.md`. Estas pruebas no equivalen a la integración extremo a extremo de todos los módulos.

## 9. Integración con otros grupos

1. El **módulo de preguntas** recopila las respuestas del usuario y puede consultar qué datos faltan.
2. El **motor de inferencia** determina los datos necesarios para procesar la consulta y ejecuta las reglas.
3. **SchemaManager** valida documentos, valores y relaciones; recibe de otro componente la lista de `atributos_requeridos` al consultar completitud.
4. Los componentes que producen trazas y dictámenes pueden utilizar `validar_traza()`, `validar_dictamen()` o `validar_conjunto()` para comprobar consistencia.

Por acuerdo del equipo, **no se incorpora `numeric_format`** al contrato: los atributos `numeric` siguen aceptando enteros y decimales. Asimismo, se mantiene el modelo actual de reglas, que genera el resultado derivado `dictamen` aunque este no aparezca en la lista de atributos de entrada del ejemplo. No se modifica ese comportamiento sin coordinación entre grupos.

La comprobación de que otros módulos envían correctamente los requisitos a `validar_completitud()` corresponde a las **pruebas de integración**, no a la validación unitaria del Grupo 4.

## 10. Consideraciones y límites

- Los contratos se validan según los esquemas del repositorio; su modificación requiere el proceso de coordinación definido en `CONTRIBUTING.md`.
- `validar_completitud()` comprueba presencia de claves, no si sus valores tienen el tipo correcto: combinarlo con `validar_memoria()`.
- La validación de trazas comprueba referencias y coherencia entre registros; **no reconstruye la inferencia ni vuelve a evaluar si una condición se cumplió**.
- La coincidencia del dictamen con el resultado derivado se comprueba cuando se proporciona `atributo_resultado` (por ejemplo, `"dictamen"`).
- Los validadores de esquemas se almacenan en una caché protegida por bloqueo y se recargan cuando cambia la fecha de modificación o el tamaño del esquema; se puede forzar su limpieza con `limpiar_cache_esquemas()`.
- El módulo no ofrece interfaz gráfica ni API HTTP propia: expone la clase Python `SchemaManager` para que otros componentes la utilicen.

---

**Archivos de referencia:** `esb_schema.py`, `schemas/*.schema.json`, `ejemplos/*.json`, `documentacion/base_conocimiento_academico.md` y `CONTRIBUTING.md` en la raíz del repositorio.
