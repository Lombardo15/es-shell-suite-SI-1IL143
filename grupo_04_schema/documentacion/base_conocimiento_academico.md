# Propuesta de base de conocimiento académico

**Proyecto:** ES-Shell Suite en Python  
**Módulo:** Grupo 4 — Schema Manager  
**Versión del conocimiento:** 1.0

## 1. Descripción

Se preparó una base de conocimiento para atender dos consultas relacionadas con el rendimiento académico: clasificar un puntaje final y revisar si una calificación satisface un criterio de repetición de asignatura para mejorar el índice. Se utilizan reglas de tipo SI-ENTONCES, con condiciones sencillas y resultados explicables.

El conjunto permite comprobar el funcionamiento de los contratos JSON, la memoria de trabajo y la generación de dictámenes. **Los criterios aquí configurados pertenecen a este caso de ejemplo; no deben interpretarse como una normativa aplicable a cualquier institución.**

## 2. Estructura de los archivos

| Archivo | Contenido |
|---|---|
| `ejemplos/conocimiento_dominio.json` | Atributos, preguntas y diez reglas de conocimiento. |
| `ejemplos/memoria_trabajo.json` | Datos de una consulta con puntaje 85 y hecho derivado. |
| `ejemplos/dictamen_salida.json` | Resultado y explicaciones de esa consulta. |
| `ejemplos/casos/repeticion_d/` | Consulta de repetición con una nota D. |
| `ejemplos/casos/repeticion_a/` | Consulta de repetición con una nota A. |
| `schemas/*.schema.json` | Definiciones generales de estructura que utilizará el validador. |

Los archivos de `ejemplos/` contienen información concreta. Los de `schemas/` describen el formato esperado. `SchemaManager`, desarrollado en `esb_schema.py`, utilizará estas definiciones para validar archivos recibidos de otros módulos.

## 3. Atributos utilizados

| Atributo | Tipo | Uso |
|---|---|---|
| `tipo_consulta` | Categórico | Indica si se solicita `Calificacion` o `Repeticion`. |
| `puntaje_final` | Numérico | Puntaje entre 0 y 100 para clasificar la calificación. |
| `nota_obtenida` | Categórico | Letra A, B, C, D o F para consultar el criterio de repetición. |

Primero se solicita `tipo_consulta`. Si es `Calificacion`, se pide `puntaje_final`; si es `Repeticion`, se pide `nota_obtenida`. No se necesitan los dos datos en una misma consulta.

## 4. Reglas incluidas

### 4.1. Clasificación del puntaje

Se usan cinco reglas. El puntaje de entrada se considera **entero** entre 0 y 100.

| Regla | Puntaje | Resultado |
|---|---|---|
| `reg_calificacion_a` | 91–100 | A — Sobresaliente |
| `reg_calificacion_b` | 81–90 | B — Bueno |
| `reg_calificacion_c` | 71–80 | C — Regular |
| `reg_calificacion_d` | 61–70 | D — Mínima de promoción |
| `reg_calificacion_f` | 0–60 | F — Fracaso |

Los rangos son excluyentes y cubren todos los puntajes enteros válidos. Así, una sola regla debe activarse para cada valor.

### 4.2. Criterio de repetición

Estas cinco reglas revisan si la nota ingresada es **D o F**, que son las calificaciones admitidas para la consulta de repetición definida en esta base de conocimiento.

| Regla | Nota | Resultado |
|---|---|---|
| `reg_repeticion_a` | A | No cumple el criterio D/F. |
| `reg_repeticion_b` | B | No cumple el criterio D/F. |
| `reg_repeticion_c` | C | No cumple el criterio D/F. |
| `reg_repeticion_d` | D | Cumple el criterio D/F. |
| `reg_repeticion_f` | F | Cumple el criterio D/F. |

Esta evaluación no realiza una matrícula ni comprueba cupos, horarios o requisitos administrativos.

## 5. Ejemplo de regla y explicación del código

```json
{
  "id": "reg_calificacion_b",
  "description": "Clasificación de calificación B (81-90)",
  "priority": 10,
  "conditions": [
    {"attribute_id": "tipo_consulta", "operator": "==", "value": "Calificacion"},
    {"attribute_id": "puntaje_final", "operator": ">=", "value": 81},
    {"attribute_id": "puntaje_final", "operator": "<=", "value": 90}
  ],
  "conclusion": {"attribute_id": "dictamen", "value": "Calificación B - Bueno"},
  "explanation_template": "El puntaje ingresado se encuentra entre 81 y 90, por lo que corresponde a la calificación B (Bueno)."
}
```

- `id`: identifica la regla y permite registrarla en la traza de ejecución.
- `description`: describe brevemente qué comprueba.
- `priority`: prioridad numérica que el motor puede utilizar para resolver conflictos.
- `conditions`: condiciones que deben cumplirse. Se emplean los operadores `==`, `>=` y `<=`.
- `conclusion`: hecho que se obtiene cuando se activa la regla.
- `explanation_template`: texto que puede utilizarse al explicar el resultado.

Se asume que las condiciones de una misma regla se combinan mediante **AND** (todas deben cumplirse). Esta interpretación debe coincidir con la implementación de los motores de inferencia.

## 6. Ejemplos de consulta

**Clasificación de una nota.** Se ingresa `tipo_consulta = Calificacion` y `puntaje_final = 85`. Se activa `reg_calificacion_b` y se obtiene **Calificación B - Bueno**. El resultado queda registrado en memoria junto con el identificador de la regla aplicada.

**Repetición con D.** Se ingresa `tipo_consulta = Repeticion` y `nota_obtenida = D`. Se activa `reg_repeticion_d` y se indica que cumple el criterio D/F configurado.

**Repetición con A.** Si la nota es A, se activa `reg_repeticion_a` y se indica que no cumple ese criterio.

Los archivos de memoria y dictamen muestran resultados esperados; el motor de inferencia tendrá que producirlos durante la ejecución real.

## 7. Validación e integración

Los esquemas definen las estructuras generales de conocimiento, memoria y dictamen. No limitan la plataforma a este caso académico. Las comprobaciones adicionales previstas para `SchemaManager` incluyen identificadores duplicados, atributos referenciados que no existen, rangos mal ordenados y valores incompatibles con los tipos declarados.

Para esta consulta, la entrada `puntaje_final` debe ser un entero de 0 a 100. Esta restricción se verificará durante la captura o validación semántica del caso, ya que el esquema general admite otros atributos numéricos.

El atributo de salida `dictamen` se considera derivado y no se solicita al usuario. Se debe confirmar con los demás grupos si los atributos derivados requieren aparecer previamente en `attributes`.

Los archivos compartidos de `contracts/` y las firmas públicas de `SchemaManager` deben mantenerse de acuerdo con el contrato aprobado por los coordinadores del proyecto. El contenido académico puede cambiar sin modificar la estructura general del sistema.
