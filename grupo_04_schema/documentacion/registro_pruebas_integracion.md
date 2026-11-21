# Registro de pruebas de integración — Grupo 4 (SchemaManager)

**Proyecto:** ES-Shell Suite (SI-1IL143)  
**Fecha de revisión:** 18 de noviembre de 2026  
**Versión base:** copia del repositorio distribuida como `17-11.zip`; el módulo `grupo_04_schema/esb_schema.py` y los contratos JSON compartidos permanecen sin modificaciones.  
**Estado:** compatibilidad entre documentos y prueba directa con G8 verificadas; **integración extremo a extremo del sistema pendiente** de que los grupos conecten sus módulos.

## 1. Objetivo y alcance

Registrar pruebas reproducibles de interoperabilidad entre SchemaManager (G4), los contratos en `contracts/`, el explicador del Grupo 8 (G8) y los documentos de ejemplo de la API del Grupo 12 (G12). Además, dejar identificados los componentes del sistema experto que aún utilizan código simulado o no tienen integración verificable.

Las pruebas del archivo `tests/test_integracion_schema.py` comprueban la compatibilidad real de entradas y salidas y **conectan manualmente G4 con G8**. No ejecutan motores de inferencia, no demuestran que G12 invoque al validador y no equivalen a una prueba end-to-end de la suite.

## 2. Entorno y comandos

**Entorno en el que se verificó este registro:** Linux, Python 3.13.5 y pytest 9.0.2.  
**Entorno local del integrante:** Windows, Python 3.12.10 y pytest 9.2.0. Se verificaron las 107 pruebas unitarias, las 19 pruebas de integración y el conjunto de 126 pruebas del Grupo 4, sin fallos ni omisiones. Los archivos de evidencia se encuentran en `tests/resultado_pruebas.txt` y `tests/resultado_integracion.txt`.

Los comandos se ejecutan desde la raíz del repositorio, que contiene `grupo_04_schema/`.

```powershell
# Solo integración del Grupo 4
python -m pytest .\grupo_04_schema\tests\test_integracion_schema.py -v -rs

# Unitarias y de integración del Grupo 4
python -m pytest .\grupo_04_schema\tests -v -rs

# Generar evidencia local de las pruebas de integración
python -m pytest .\grupo_04_schema\tests\test_integracion_schema.py -v -rs |
    Tee-Object -FilePath .\grupo_04_schema\tests\resultado_integracion.txt

# Ejecutar todas las pruebas existentes del repositorio (requiere dependencias de otros grupos)
python -m pytest -q -rs
```

**Dependencias:** `jsonschema` y `pytest` para G4. Para ejecutar las pruebas de G12 se requieren también las dependencias de `grupo_12_api/requirements.txt` (`fastapi`, `httpx`, etc.). La integración directa G4–G8 incluida en estas pruebas no requiere levantar un servidor HTTP.

## 3. Resultados comprobados

| Identificador | Comprobación | Casos | Resultado |
| --- | --- | ---: | --- |
| INT-01 | Los esquemas de `grupo_04_schema/schemas/` y `contracts/` son idénticos | 3 | Aprobados |
| INT-02 | Los ejemplos de G12 cumplen individualmente los tres contratos G4 | 3 | Aprobados |
| INT-03 | El conjunto conocimiento–memoria–dictamen de G12 es coherente | 1 | Aprobado |
| INT-04 | Los tres escenarios G4 son coherentes al validarlos conjuntamente | 3 | Aprobados |
| INT-05 | El explicador real de G8 genera HOW/WHY compatible con un dictamen validado por G4 | 3 | Aprobados |
| INT-06 | G8 interpreta las trazas de las memorias válidas de G4 | 3 | Aprobados |
| INT-07 | G4 admite memorias parciales y devuelve faltantes según tipo de consulta | 2 | Aprobados |
| INT-08 | G4 rechaza un dato numérico fuera del rango de la base de ejemplo de G12 | 1 | Aprobado |
| **Total de integración** | | **19** | **19 aprobados; 0 fallidos; 0 omitidos** |

### Resumen de ejecuciones comprobadas en la revisión y reproducidas en Windows para el Grupo 4

| Comando | Resultado |
| --- | --- |
| `python -m pytest grupo_04_schema/tests/test_integracion_schema.py -v -rs` | **19 passed** |
| `python -m pytest grupo_04_schema/tests -q -rs` | **126 passed** (107 unitarias + 19 de integración) |
| `python -m pytest -q -rs` | **146 passed** (126 de G4 + 20 existentes en G8/G12) |

No se identificaron fallos en esos casos específicos. En Windows también se ejecutaron los 19 casos de integración y los 126 casos del Grupo 4 sin fallos. Las 19 pruebas nuevas no alteran las 107 pruebas unitarias originales.

## 4. Observaciones de integración

### 4.1. Contratos y casos JSON

- Las tres parejas de archivos `.schema.json` en `contracts/` y `grupo_04_schema/schemas/` coinciden byte por byte en esta versión.
- Los ejemplos de G12 (`grupo_12_api/datos_ejemplo/`) se validan mediante los esquemas de G4.
- Los casos G4 `calificacion`, `repeticion_a` y `repeticion_d` pasan `validar_conjunto(..., "dictamen")`.
- Las reglas de calificación admiten decimales dentro de los intervalos del conocimiento académico, pero SchemaManager **no ejecuta** esas reglas.

### 4.2. Explicador G8 — comprobación real y manualmente conectada

Se instanció `XAIExplainer` con la base de conocimiento de G4; se procesaron memorias de G4 con `explain_how`, `explain_why` y `explain_trace`. Las explicaciones obtenidas se insertaron en un dictamen de ejemplo y se comprobó su estructura y coherencia con `SchemaManager.validar_conjunto`. Los tres escenarios pasaron.

**Límite:** esta conexión la realiza el archivo de prueba. No demuestra que el orquestador o la API del sistema la estén utilizando.

### 4.3. Completitud y memoria parcial

- `validar_memoria()` admite los hechos presentes y puede aceptar memorias incompletas.
- `validar_completitud()` recibe una lista externa de atributos requeridos y solo señala los que faltan; no decide qué preguntar ni comprueba los valores.
- Requisitos pactados: `Calificacion` → `tipo_consulta`, `puntaje_final`; `Repeticion` → `tipo_consulta`, `nota_obtenida`.
- La integración real con el motor de preguntas/inferencia responsable de suministrar los atributos requeridos queda pendiente.

### 4.4. API G12 — compatibilidad de ejemplos, **no conexión real con G4**

En `grupo_12_api/servicio.py`, el registro `MODULOS` indica `"G4 SchemaManager": "simulado"`. Las operaciones `cargar_conocimiento`, `iniciar_consulta` y `registrar_hechos` no invocan los métodos de `SchemaManager` en esta copia del repositorio.

**Comprobación exploratoria ejecutada:** se inició una sesión de G12 con `promedio = 4.0`, aunque el conocimiento de ejemplo fija `promedio` en `[0.0, 3.0]`. El servicio admitió ese hecho sin validarlo; posteriormente G4 devolvió `{"valido": false, ... "fuera del rango" ...}` al examinar la memoria. Esto **no es un fallo de G4**: demuestra una validación aún no integrada en el servicio. No se modificó el código de G12.

Recomendación para el equipo G12: antes de aceptar bases y memorias, invocar `validar_datos()` y `validar_memoria()`, y definir cómo se traducen los errores del validador a respuestas HTTP. Después, volver a probar el flujo HTTP completo, incluidas entradas inválidas.

## 5. Integraciones pendientes de verificación real

| Área | Situación en la versión examinada | Condición para cerrarla |
| --- | --- | --- |
| G1 — Preguntas | No se dispone de lógica integrada para comprobar consumo de `validar_completitud()` | Ejecutar una consulta real y verificar que el llamador envía la lista de atributos correcta |
| G5/G6/G7 — Inferencia | No se dispone de ejecución real de motores conectados a la memoria validada | Generar hechos/trazas con el motor y validarlos en G4 |
| G12 — API y G4 | Servicio actualmente simulado respecto de SchemaManager | Integrar llamadas al validador y probar errores HTTP y el ciclo completo |
| G9/G11 — Reporte/almacenamiento | No se verifica intercambio real con G4 en esta revisión | Probar datos producidos, lectura/escritura y contratos una vez conectados |
| Suite completa | No existe evidencia de ejecución de punta a punta de todos los grupos | Ejecutar una sesión real con entradas, inferencia, dictamen, explicación y reporte |

Estos asuntos se registran como **pendientes de integración externa**, no como pruebas aprobadas ni como tareas que deban corregirse unilateralmente en el módulo G4.

## 6. Acuerdos respetados

1. Se mantienen enteros y decimales válidos; no se añade `numeric_format` sin acuerdo de contrato.
2. Se conserva el manejo actual de `dictamen` como hecho derivado.
3. G4 comprueba completitud; el módulo llamador determina qué atributos solicitar.
4. No se modificaron `esb_schema.py`, `contracts/` ni los esquemas JSON del Grupo 4.

## 7. Conclusión del registro

Las pruebas realizadas demuestran que el validador del Grupo 4 es compatible con los contratos compartidos, los ejemplos de la API del Grupo 12 y las salidas que puede producir directamente el explicador del Grupo 8. **La compatibilidad parcial está verificada**, mientras que el acoplamiento de los componentes restantes, en especial la validación automática desde la API y los motores de inferencia, permanece pendiente del trabajo coordinado entre grupos. El registro se actualizará cuando esos módulos se conecten realmente.
