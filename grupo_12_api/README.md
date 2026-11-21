# Grupo 12 · API REST (FastAPI)

Archivo `esb_api.py`, servicio FastAPI. Coordinador: Samuel Díaz (@Shazam15).

Este módulo expone el shell experto por HTTP para el perfil de integrador o desarrollador externo. Cubre tres operaciones: cargar una base de conocimiento, ejecutar una consulta y pedir el dictamen con sus explicaciones HOW/WHY. La API no razona por su cuenta. Recibe la petición, llama al módulo del grupo que corresponde y devuelve el resultado con la forma de los contratos JSON de la sección 4.2.

## Estado

Stub del 14 de noviembre. Todas las rutas están declaradas y documentadas en `/docs`, y responden con la forma final de los contratos. Las bases de conocimiento y las sesiones se guardan en memoria. La inferencia, el dictamen y la explicación HOW todavía devuelven los ejemplos de la sección 4.2 (`datos_ejemplo/`), y `/salud` marca como `simulado` cada módulo que aún no está integrado. Las rutas y los cuerpos de petición quedan sujetos al congelamiento de contratos del 16 de noviembre.

## Estructura

| Archivo | Contenido |
|---|---|
| `esb_api.py` | Aplicación FastAPI y rutas. Solo traduce HTTP a llamadas del servicio. |
| `servicio.py` | `ServicioESB`, la lógica de negocio, que no depende de FastAPI. Aquí se conectarán los módulos de los demás grupos. |
| `modelos.py` | Modelos Pydantic de los tres contratos y de los cuerpos propios de la API. |
| `datos_ejemplo/` | Los tres JSON de la sección 4.2. Se usarán hasta que exista `contracts/`. |
| `tests/test_api.py` | Pruebas con `TestClient`. |

## Instalación y ejecución

Desde la raíz del repositorio, con Python 3.11 o superior:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r grupo_12_api/requirements.txt
uvicorn grupo_12_api.esb_api:app --reload
```

La documentación interactiva queda en http://127.0.0.1:8000/docs (Swagger) y http://127.0.0.1:8000/redoc. Al iniciar se precarga la base de ejemplo con el id `kb_ejemplo`.

## Endpoints

| Método y ruta | Qué hace | Respuesta | Módulo que usará |
|---|---|---|---|
| `GET /salud` | Estado del servicio y de los módulos integrados | `Salud` | — |
| `POST /conocimiento` | Carga y valida un `conocimiento_dominio.json` | `kb_id` y resumen | G4, G11 |
| `GET /conocimiento/{kb_id}` | Devuelve la base cargada | `conocimiento_dominio.json` | G11 |
| `GET /conocimiento/{kb_id}/preguntas` | Atributos con su pregunta, tipo, opciones y rango | lista de `Pregunta` | G1 |
| `POST /consultas` | Inicia una sesión (`kb_id`, `motor`: `adelante` o `atras`, `hechos`) | `session_id` | G5, G6 |
| `POST /consultas/{session_id}/hechos` | Registra datos del usuario | `memoria_trabajo.json` | G5, G6 |
| `GET /consultas/{session_id}/siguiente-pregunta` | Próximo dato que pide el motor, con su WHY | `SiguientePregunta` | G6, G8 |
| `POST /consultas/{session_id}/inferir` | Ejecuta el motor | `memoria_trabajo.json` | G5, G6, G7 |
| `GET /consultas/{session_id}/memoria` | Memoria de trabajo actual | `memoria_trabajo.json` | — |
| `GET /consultas/{session_id}/dictamen` | Resultado final con HOW/WHY | `dictamen_salida.json` | G7, G8 |
| `GET /consultas/{session_id}/reporte?formato=md\|html` | Reporte descargable | Markdown o HTML | G9 |
| `GET /consultas/{session_id}/explicacion/how?atributo=` | ¿Cómo se llegó a ese valor? | `explanation_how` | G8 |
| `GET /consultas/{session_id}/explicacion/why?atributo=&regla=` | ¿Por qué se pide ese dato? | `explanation_why` | G8 |
| `GET /consultas/{session_id}/traza` | Reglas aplicadas en orden | lista de pasos | G8 |

Errores: `404` cuando la base, la sesión, el atributo o la regla no existe; `409` cuando se infiere sin hechos o se pide el dictamen antes de inferir; `422` cuando el cuerpo no cumple el contrato. El campo `detail` trae el mensaje en español.

Ejemplo del escenario de la sección 6 con `curl`:

```bash
curl -X POST localhost:8000/consultas -H 'Content-Type: application/json' \
     -d '{"kb_id": "kb_ejemplo", "motor": "adelante", "hechos": {"materia": "Trabajo de Graduacion"}}'
# {"session_id": "sess_2026_00001", ...}
curl -X POST localhost:8000/consultas/sess_2026_00001/hechos -H 'Content-Type: application/json' \
     -d '{"hechos": {"promedio": 2.25}}'
curl -X POST localhost:8000/consultas/sess_2026_00001/inferir
curl localhost:8000/consultas/sess_2026_00001/dictamen
```

## Dependencias con otros grupos

| Grupo | Qué necesita G12 | Para qué |
|---|---|---|
| G4 | `SchemaManager` con un método para validar `conocimiento_dominio.json` | Validar la base en `POST /conocimiento` además de los modelos Pydantic |
| G5, G6 | Firma pública de `ForwardEngine` y `BackwardEngine`: cómo se construyen, cómo se ejecutan y qué devuelven | `POST /inferir` |
| G6 | Cómo informa el motor hacia atrás el próximo dato que necesita y la regla que evalúa | `GET /siguiente-pregunta` |
| G7 | Cómo se obtiene el `certainty_score` final | Dictamen |
| G8 | `XAIExplainer` (ya publicado en `grupo-08/stub-explicador`) | HOW, WHY y traza |
| G9 | `ReportGenerator` y los formatos que soporta | `GET /reporte` |
| G11 | `ESBConverter` para guardar y cargar bases y sesiones | Persistencia de `/conocimiento` y `/consultas` |

| Grupo | Qué recibe de G12 |
|---|---|
| G10 | Opcionalmente, la API como backend de la interfaz web |
| Integradores externos | El servicio documentado en `/docs` |

## Observaciones para la revisión de contratos (antes del 16 nov. al mediodía)

1. Ningún contrato dice quién genera `session_id`. La API lo genera con el formato `sess_AAAA_NNNNN` del ejemplo; G10 debería usar el mismo si crea sesiones por su cuenta.
2. Hace falta un formato acordado para la "pregunta pendiente" del motor hacia atrás (atributo y `rule_id`). G8 pidió lo mismo para que el WHY cite la regla correcta.
3. `explanation_why` es una sola cadena. Se mantiene así en la API, alineado con la observación 1 de G8.
4. Conviene que cada sesión guarde la `meta.version` de la base con la que se ejecutó, para que G8 y G11 la reconstruyan sin ambigüedad.
5. Los modelos de contrato aceptan campos adicionales y no restringen `type` ni `operator` mientras G1, G2 y G4 no cierren la lista de valores válidos.

## Pruebas

Desde la raíz del repositorio:

```bash
python -m pytest grupo_12_api
```

Cubren el recorrido completo de una consulta (cargar base, iniciar, registrar hechos, siguiente pregunta, inferir, traza, dictamen, HOW/WHY y reporte), cuerpos que no cumplen el contrato, bases, sesiones, atributos y reglas inexistentes, y una consulta en la que no se activa ninguna regla (dictamen pedido antes de inferir o inferencia sin hechos).
