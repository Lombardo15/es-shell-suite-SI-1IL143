"""Pruebas del stub de la API REST (Grupo 12).

Se ejecutan desde la raiz del repositorio con: python -m pytest grupo_12_api
"""

import copy

import pytest
from fastapi.testclient import TestClient

from grupo_12_api.esb_api import app, obtener_servicio
from grupo_12_api.servicio import KB_EJEMPLO, ServicioESB, cargar_ejemplo

KB = cargar_ejemplo("conocimiento_dominio")
DICTAMEN = cargar_ejemplo("dictamen_salida")


@pytest.fixture
def cliente():
    """Cliente con un servicio nuevo en cada prueba, para que no compartan sesiones."""
    servicio = ServicioESB()
    app.dependency_overrides[obtener_servicio] = lambda: servicio
    yield TestClient(app)
    app.dependency_overrides.clear()


def nueva_sesion(cliente, hechos=None, kb_id=KB_EJEMPLO):
    r = cliente.post("/consultas", json={"kb_id": kb_id, "motor": "adelante",
                                         "hechos": hechos or {}})
    assert r.status_code == 201
    return r.json()["session_id"]


# Caso normal: el escenario de la seccion 6 recorrido por HTTP.

def test_salud_y_documentacion(cliente):
    r = cliente.get("/salud")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"
    assert "G8 XAIExplainer" in r.json()["modulos"]
    assert cliente.get("/docs").status_code == 200
    rutas = cliente.get("/openapi.json").json()["paths"]
    assert "/consultas/{session_id}/explicacion/how" in rutas


def test_cargar_y_leer_conocimiento(cliente):
    r = cliente.post("/conocimiento", json=KB)
    assert r.status_code == 201
    cargada = r.json()
    assert cargada["kb_id"] == "kb_001"
    assert (cargada["atributos"], cargada["reglas"]) == (2, 1)
    kb = cliente.get(f"/conocimiento/{cargada['kb_id']}").json()
    assert kb["rules"][0]["id"] == "rule_01"
    preguntas = cliente.get(f"/conocimiento/{cargada['kb_id']}/preguntas").json()
    assert [p["attribute_id"] for p in preguntas] == ["promedio", "materia"]


def test_consulta_completa(cliente):
    session_id = nueva_sesion(cliente, {"materia": "Trabajo de Graduacion"})

    pendiente = cliente.get(f"/consultas/{session_id}/siguiente-pregunta").json()
    assert pendiente["completa"] is False
    assert pendiente["pregunta"]["attribute_id"] == "promedio"
    assert pendiente["explanation_why"].startswith("Se solicitó 'promedio'")

    memoria = cliente.post(f"/consultas/{session_id}/hechos",
                           json={"hechos": {"promedio": 2.25}}).json()
    assert memoria["facts"] == {"materia": "Trabajo de Graduacion", "promedio": 2.25}
    assert cliente.get(f"/consultas/{session_id}/siguiente-pregunta").json()["completa"] is True

    memoria = cliente.post(f"/consultas/{session_id}/inferir").json()
    assert memoria["session_id"] == session_id
    assert memoria["derived_facts"]["dictamen"]["derived_by_rule"] == "rule_01"

    traza = cliente.get(f"/consultas/{session_id}/traza").json()["pasos"]
    assert traza == ["Paso 1: rule_01 agregó dictamen = 'Elegible'"]

    dictamen = cliente.get(f"/consultas/{session_id}/dictamen").json()
    assert dictamen == {**DICTAMEN, "session_id": session_id}


def test_how_y_why(cliente):
    session_id = nueva_sesion(cliente, {"materia": "Trabajo de Graduacion", "promedio": 2.25})
    cliente.post(f"/consultas/{session_id}/inferir")

    how = cliente.get(f"/consultas/{session_id}/explicacion/how").json()
    assert how["explanation_how"] == DICTAMEN["explanation_how"]
    how_dato = cliente.get(f"/consultas/{session_id}/explicacion/how",
                           params={"atributo": "promedio"}).json()
    assert how_dato["explanation_how"] == ["'promedio' fue ingresado por el usuario: 2.25."]

    why = cliente.get(f"/consultas/{session_id}/explicacion/why",
                      params={"atributo": "promedio"}).json()
    assert why["rule_id"] == "rule_01"
    assert why["explanation_why"] == DICTAMEN["explanation_why"]


def test_reporte_markdown_y_html(cliente):
    session_id = nueva_sesion(cliente, {"promedio": 2.25})
    cliente.post(f"/consultas/{session_id}/inferir")
    md = cliente.get(f"/consultas/{session_id}/reporte")
    assert md.status_code == 200
    assert md.text.startswith(f"# Dictamen {session_id}")
    html = cliente.get(f"/consultas/{session_id}/reporte", params={"formato": "html"})
    assert html.headers["content-type"].startswith("text/html")
    assert "<h1>" in html.text


# Datos invalidos.

def test_base_que_no_cumple_el_contrato(cliente):
    sin_reglas = {k: v for k, v in KB.items() if k != "rules"}
    assert cliente.post("/conocimiento", json=sin_reglas).status_code == 422
    regla_sin_condiciones = copy.deepcopy(KB)
    regla_sin_condiciones["rules"][0]["conditions"] = []
    assert cliente.post("/conocimiento", json=regla_sin_condiciones).status_code == 422


def test_cuerpos_invalidos(cliente):
    assert cliente.post("/consultas", json={"kb_id": KB_EJEMPLO, "motor": "lateral"}).status_code == 422
    session_id = nueva_sesion(cliente)
    assert cliente.post(f"/consultas/{session_id}/hechos", json={"hechos": {}}).status_code == 422
    assert cliente.get(f"/consultas/{session_id}/reporte",
                       params={"formato": "pdf"}).status_code == 422


def test_recursos_inexistentes(cliente):
    assert cliente.get("/conocimiento/kb_999").status_code == 404
    assert cliente.post("/consultas", json={"kb_id": "kb_999"}).status_code == 404
    r = cliente.get("/consultas/sess_0000_00000/memoria")
    assert r.status_code == 404
    assert "sess_0000_00000" in r.json()["detail"]


def test_why_con_atributo_o_regla_desconocidos(cliente):
    session_id = nueva_sesion(cliente)
    url = f"/consultas/{session_id}/explicacion/why"
    r = cliente.get(url, params={"atributo": "edad"})
    assert r.status_code == 404 and "Ninguna regla" in r.json()["detail"]
    r = cliente.get(url, params={"atributo": "promedio", "regla": "rule_99"})
    assert r.status_code == 404 and "rule_99" in r.json()["detail"]


# Reglas que no se activan: sin inferencia no hay dictamen ni explicacion HOW.

def test_inferir_sin_hechos(cliente):
    session_id = nueva_sesion(cliente)
    r = cliente.post(f"/consultas/{session_id}/inferir")
    assert r.status_code == 409


def test_dictamen_antes_de_inferir(cliente):
    session_id = nueva_sesion(cliente, {"promedio": 1.5})
    assert cliente.get(f"/consultas/{session_id}/dictamen").status_code == 409
    assert cliente.get(f"/consultas/{session_id}/traza").json()["pasos"] == []
    r = cliente.get(f"/consultas/{session_id}/explicacion/how")
    assert r.status_code == 404 and "no tiene valor" in r.json()["detail"]
