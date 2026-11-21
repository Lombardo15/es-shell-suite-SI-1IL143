"""Pruebas de compatibilidad e integración parcial del Grupo 4.

Se ejecutan desde la raíz del repositorio:
    python -m pytest grupo_04_schema/tests/test_integracion_schema.py -v -rs

Estas pruebas NO implican que la API o los motores estén conectados a
SchemaManager. Validan los contratos y el intercambio real con XAIExplainer.
"""

import copy
from pathlib import Path

import pytest

from grupo_04_schema.esb_schema import SchemaManager
from grupo_08_explainer.esb_explainer import XAIExplainer


RAIZ = Path(__file__).resolve().parents[2]
EJEMPLOS_G4 = RAIZ / "grupo_04_schema" / "ejemplos"
EJEMPLOS_G12 = RAIZ / "grupo_12_api" / "datos_ejemplo"
CONTRATOS = ("conocimiento_dominio", "memoria_trabajo", "dictamen_salida")
ESCENARIOS = ("calificacion", "repeticion_a", "repeticion_d")


@pytest.fixture(scope="module")
def gestor():
    return SchemaManager()


def _cargar_caso(gestor, escenario):
    carpeta_caso = (
        EJEMPLOS_G4 if escenario == "calificacion"
        else EJEMPLOS_G4 / "casos" / escenario
    )
    conocimiento = gestor.cargar_json(EJEMPLOS_G4 / "conocimiento_dominio.json")
    memoria = gestor.cargar_json(carpeta_caso / "memoria_trabajo.json")
    dictamen = gestor.cargar_json(carpeta_caso / "dictamen_salida.json")
    return conocimiento, memoria, dictamen


# 1. Contratos compartidos: debe existir una sola definición efectiva.
@pytest.mark.parametrize("tipo", CONTRATOS)
def test_esquemas_del_grupo_4_coinciden_con_contracts(tipo):
    archivo = f"{tipo}.schema.json"
    local = RAIZ / "grupo_04_schema" / "schemas" / archivo
    compartido = RAIZ / "contracts" / archivo
    assert local.read_bytes() == compartido.read_bytes()


# 2. Los documentos de muestra del Grupo 12 deben cumplir el contrato G4.
@pytest.mark.parametrize("tipo", CONTRATOS)
def test_ejemplos_del_grupo_12_cumplen_contratos(gestor, tipo):
    datos = gestor.cargar_json(EJEMPLOS_G12 / f"{tipo}.json")
    assert gestor.validar_datos(datos, tipo) == {"valido": True, "errores": []}


def test_ejemplos_del_grupo_12_son_coherentes_entre_si(gestor):
    documentos = [
        gestor.cargar_json(EJEMPLOS_G12 / f"{nombre}.json")
        for nombre in CONTRATOS
    ]
    assert gestor.validar_conjunto(*documentos, "dictamen") == {
        "valido": True, "errores": []
    }


# 3. La validación conjunta admite los tres escenarios del Grupo 4.
@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_escenarios_del_grupo_4_coherentes(gestor, escenario):
    conocimiento, memoria, dictamen = _cargar_caso(gestor, escenario)
    assert gestor.validar_conjunto(conocimiento, memoria, dictamen, "dictamen") == {
        "valido": True, "errores": []
    }


# 4. Consumidor real: Grupo 8 lee documentos que SchemaManager valida.
@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_explicador_g8_genera_dictamen_compatible(gestor, escenario):
    conocimiento, memoria, dictamen = _cargar_caso(gestor, escenario)
    explicador = XAIExplainer(conocimiento)
    explicaciones_how = explicador.explain_how(memoria, "dictamen")
    explicacion_why = explicador.explain_why("tipo_consulta")

    assert explicaciones_how and all(isinstance(x, str) for x in explicaciones_how)
    assert isinstance(explicacion_why, str) and explicacion_why

    # Se conectan manualmente dos módulos reales; no se ejecuta un motor.
    salida = copy.deepcopy(dictamen)
    salida["explanation_how"] = explicaciones_how
    salida["explanation_why"] = explicacion_why
    assert gestor.validar_conjunto(conocimiento, memoria, salida, "dictamen") == {
        "valido": True, "errores": []
    }


@pytest.mark.parametrize("escenario", ESCENARIOS)
def test_explicador_g8_interpreta_traza_valida(gestor, escenario):
    conocimiento, memoria, _ = _cargar_caso(gestor, escenario)
    assert gestor.validar_traza(memoria, conocimiento)["valido"]
    traza = XAIExplainer(conocimiento).explain_trace(memoria)
    assert len(traza) == len(memoria["execution_trace"])
    assert all(isinstance(linea, str) and linea for linea in traza)


# 5. Integración de responsabilidades con el módulo que gestiona consultas.
@pytest.mark.parametrize("consulta, requerido, faltante", [
    ("Calificacion", "puntaje_final", "puntaje_final"),
    ("Repeticion", "nota_obtenida", "nota_obtenida"),
])
def test_memoria_parcial_validada_y_completitud_separada(
    gestor, consulta, requerido, faltante
):
    conocimiento = gestor.cargar_json(EJEMPLOS_G4 / "conocimiento_dominio.json")
    memoria = {
        "session_id": "sesion_integracion_parcial",
        "facts": {"tipo_consulta": consulta},
        "derived_facts": {},
        "execution_trace": [],
    }
    assert gestor.validar_memoria(memoria, conocimiento)["valido"] is True
    assert gestor.validar_completitud(
        memoria, ["tipo_consulta", requerido]
    ) == {"completa": False, "faltantes": [faltante]}


# 6. Comprobación negativa entre documentos API y validador del Grupo 4.
def test_schema_manager_detecta_hecho_invalido_del_formato_g12(gestor):
    conocimiento = gestor.cargar_json(EJEMPLOS_G12 / "conocimiento_dominio.json")
    memoria = gestor.cargar_json(EJEMPLOS_G12 / "memoria_trabajo.json")
    memoria["facts"]["promedio"] = 4.0  # rango de ejemplo: 0.0 a 3.0
    resultado = gestor.validar_memoria(memoria, conocimiento)
    assert resultado["valido"] is False
    assert any("fuera del rango" in e for e in resultado["errores"])
