# Grupo 4 — SchemaManager
## Registro de acuerdos y comportamientos pendientes

**Fecha:** 18 de noviembre de 2026  
**Versión de referencia:** versión nueva del repositorio del Grupo 4 (`17-11.zip`).  
**Responsabilidad cubierta:** punto 2 — registrar los comportamientos pendientes y revisarlos con el integrante 2.

## 1. Respuestas y acuerdos revisados

| Tema | Acuerdo operativo para esta entrega | Tratamiento en SchemaManager |
|---|---|---|
| Valores numéricos | Mantener la aceptación de números enteros y decimales, sin incorporar `numeric_format` en esta versión. | Se conserva el código actual y el rango permitido de 0 a 100 para los puntajes correspondientes. |
| Intervalos de calificación | Usar intervalos continuos que no dejen valores decimales sin clasificar (por ejemplo, 90.5). | Se conservan las reglas actualizadas de la nueva versión. |
| Memorias incompletas | `validar_memoria()` debe poder validar los datos existentes antes de que se hayan respondido todas las preguntas. | Se conserva el comportamiento actual; validar datos no equivale a exigir completitud. |
| Completitud | `validar_completitud(memoria, atributos_requeridos)` identifica los campos faltantes en `facts`; no valida sus valores. | La función ya está implementada. No es necesario añadir otro método. |
| Consulta `Calificacion` | Atributos requeridos: `tipo_consulta`, `puntaje_final`. | El módulo llamador debe pasar esta lista al verificar completitud. |
| Consulta `Repeticion` | Atributos requeridos: `tipo_consulta`, `nota_obtenida`. | El módulo llamador debe pasar esta lista al verificar completitud. |
| Atributo derivado `dictamen` | Trabajar con la estructura que ya implementaron los compañeros, sin alterar el contrato actual. | Se conserva como está en las reglas y los documentos. |
| Distribución de responsabilidades | El módulo de preguntas obtiene los datos; el motor de inferencia decide cuándo solicitar más información; SchemaManager comprueba validez y completitud a petición de otros módulos. | No se asigna a SchemaManager el control del flujo de preguntas ni las decisiones de inferencia. |

Estas decisiones corresponden al **alcance de trabajo de esta entrega**. No se presentan como una aprobación formal de futuras modificaciones a los contratos por parte de todos los grupos.

## 2. Comportamientos pendientes revisados

1. **`numeric_format`:** propuesta planteada por un compañero, pero no aprobada para esta entrega. Se decidió **no implementarla**; se acepta la validación numérica actual.
2. **Declaración de `dictamen` en `attributes`:** se mantiene la implementación existente de los compañeros. Cualquier cambio estructural posterior requerirá coordinación de contrato.
3. **Selección de atributos para `validar_completitud()`:** se adopta la división de responsabilidades indicada arriba. La comprobación de que los módulos consumidores envían las listas adecuadas se mantiene como cuestión de **integración entre grupos**, no como una modificación pendiente de SchemaManager.

**Resultado del punto 2:** los comportamientos fueron revisados con base en las respuestas recibidas y contrastados con la implementación. No hay cambios adicionales de código aprobados para nuestra parte.

## 3. Evidencia de validación

Resultados ejecutados y comunicados desde el entorno Windows de trabajo:

- **107** pruebas unitarias aprobadas (`tests/test_schema.py`).
- **19** pruebas de integración disponibles aprobadas (`tests/test_integracion_schema.py`).
- **126** pruebas aprobadas al ejecutar el conjunto de pruebas de `grupo_04_schema/tests/`.
- **0** pruebas fallidas en esos resultados reportados.

Los resultados y las integraciones que dependen de módulos todavía no conectados se documentan por separado en `documentacion/registro_pruebas_integracion.md`. Estas pruebas no constituyen una validación de todas las conexiones del sistema experto completo.

## 4. Cierre

Para el alcance asignado al Grupo 4 se decide conservar la versión nueva de los compañeros, sin modificar `esb_schema.py` ni los contratos compartidos. Los temas futuros de integración quedan registrados sin bloquear el cierre de este punto.
