"""Pruebas unitarias del Grupo 4: SchemaManager.

Cobertura: completitud, memorias, contratos, semántica, trazas, dictámenes,
archivos JSON, caché, versiones, tipos de datos y dependencias.

Ejecutar desde la raíz del repositorio:
    python -m pytest grupo_04_schema/tests/test_schema.py -v -rs
"""

import copy
import json
import shutil
from pathlib import Path

import pytest

from grupo_04_schema.esb_schema import SchemaManager


# -----------------------------------------------------------------------------
# Configuración y datos de ejemplo
# -----------------------------------------------------------------------------
BASE = Path(__file__).resolve().parents[1]
EJEMPLOS = BASE / "ejemplos"
SCHEMAS = BASE / "schemas"
TIPOS = ("conocimiento_dominio", "memoria_trabajo", "dictamen_salida")


@pytest.fixture
def documentos_memoria():
    """Conocimiento y memoria originales, independientes en cada prueba."""
    conocimiento = json.loads(
        (EJEMPLOS / "conocimiento_dominio.json").read_text(encoding="utf-8")
    )
    memoria = json.loads(
        (EJEMPLOS / "memoria_trabajo.json").read_text(encoding="utf-8")
    )
    return conocimiento, memoria


@pytest.fixture
def contratos_json():
    """Contratos de ejemplo sin modificaciones entre pruebas."""
    return {
        tipo: json.loads(
            (EJEMPLOS / f"{tipo}.json").read_text(encoding="utf-8")
        )
        for tipo in TIPOS
    }


@pytest.fixture
def casos_de_sesion():
    """Recupera las tres sesiones reales de ejemplo del proyecto."""
    def cargar(nombre):
        carpeta = EJEMPLOS if nombre == "calificacion" else EJEMPLOS / "casos" / nombre
        conocimiento = json.loads(
            (EJEMPLOS / "conocimiento_dominio.json").read_text(encoding="utf-8")
        )
        memoria = json.loads(
            (carpeta / "memoria_trabajo.json").read_text(encoding="utf-8")
        )
        dictamen = json.loads(
            (carpeta / "dictamen_salida.json").read_text(encoding="utf-8")
        )
        return conocimiento, memoria, dictamen

    return cargar


@pytest.fixture
def conocimiento():
    return SchemaManager.cargar_json(EJEMPLOS / "conocimiento_dominio.json")


@pytest.fixture
def gestor_esquemas_temporales(tmp_path):
    for archivo in SCHEMAS.glob("*.schema.json"):
        shutil.copy2(archivo, tmp_path / archivo.name)
    return SchemaManager(carpeta_esquemas=tmp_path)


# -----------------------------------------------------------------------------
# 1. Completitud de memoria (6 casos)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "hechos, requeridos, faltantes",
    [
        ({}, ["tipo_consulta", "puntaje_final"], ["tipo_consulta", "puntaje_final"]),
        ({"tipo_consulta": "Calificacion"}, ["tipo_consulta", "puntaje_final"], ["puntaje_final"]),
        ({"tipo_consulta": "Calificacion", "puntaje_final": 90.5}, ["tipo_consulta", "puntaje_final"], []),
        ({"tipo_consulta": "Repeticion"}, ["tipo_consulta", "nota_obtenida"], ["nota_obtenida"]),
        ({"tipo_consulta": "Repeticion", "nota_obtenida": 75}, ["tipo_consulta", "nota_obtenida"], []),
        ({"tipo_consulta": "Calificacion"}, ["tipo_consulta", "puntaje_final", "puntaje_final"], ["puntaje_final"]),
    ],
)
def test_validar_completitud(hechos, requeridos, faltantes):
    memoria = {"facts": hechos}
    resultado = SchemaManager.validar_completitud(memoria, requeridos)
    assert resultado == {"completa": len(faltantes) == 0, "faltantes": faltantes}


# -----------------------------------------------------------------------------
# 2. Validación de memoria (12 casos)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("hechos", [
    {},
    {"tipo_consulta": "Calificacion"},
    {"tipo_consulta": "Calificacion", "puntaje_final": 90.5},
    {"tipo_consulta": "Calificacion", "puntaje_final": 0},
    {"tipo_consulta": "Calificacion", "puntaje_final": 100},
    {"tipo_consulta": "Repeticion", "nota_obtenida": "A"},
])
def test_validar_memoria_valida(documentos_memoria, hechos):
    conocimiento, memoria = documentos_memoria
    memoria["facts"] = hechos
    resultado = SchemaManager().validar_memoria(memoria, conocimiento)
    assert resultado == {"valido": True, "errores": []}


@pytest.mark.parametrize("hechos, mensaje", [
    ({"puntaje_final": 101}, "fuera del rango"),
    ({"puntaje_final": -1}, "fuera del rango"),
    ({"puntaje_final": "85"}, "Se esperaba un número"),
    ({"tipo_consulta": "Otra"}, "no está entre las opciones"),
    ({"nota_obtenida": "Z"}, "no está entre las opciones"),
    ({"atributo_desconocido": 50}, "no está declarado"),
])
def test_validar_memoria_invalida(documentos_memoria, hechos, mensaje):
    conocimiento, memoria = documentos_memoria
    memoria["facts"] = hechos
    resultado = SchemaManager().validar_memoria(memoria, conocimiento)
    assert resultado["valido"] is False
    assert any(mensaje in error for error in resultado["errores"])


# -----------------------------------------------------------------------------
# 3. Validación de contratos JSON (10 casos)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("tipo", TIPOS)
def test_contrato_valido(contratos_json, tipo):
    resultado = SchemaManager().validar_datos(contratos_json[tipo], tipo)
    assert resultado == {"valido": True, "errores": []}


@pytest.mark.parametrize("tipo, campo", [
    ("conocimiento_dominio", "meta"),
    ("memoria_trabajo", "session_id"),
    ("dictamen_salida", "final_outcome"),
])
def test_contrato_campo_obligatorio(contratos_json, tipo, campo):
    datos = copy.deepcopy(contratos_json[tipo])
    del datos[campo]
    resultado = SchemaManager().validar_datos(datos, tipo)
    assert resultado["valido"] is False
    assert resultado["errores"]


@pytest.mark.parametrize("tipo, campo, valor", [
    ("conocimiento_dominio", "attributes", "incorrecto"),
    ("memoria_trabajo", "facts", []),
    ("dictamen_salida", "explanation_how", "incorrecto"),
])
def test_contrato_tipo_incorrecto(contratos_json, tipo, campo, valor):
    datos = copy.deepcopy(contratos_json[tipo])
    datos[campo] = valor
    resultado = SchemaManager().validar_datos(datos, tipo)
    assert resultado["valido"] is False
    assert resultado["errores"]


def test_contrato_desconocido():
    with pytest.raises(ValueError):
        SchemaManager().validar_datos({}, "contrato_inexistente")


# -----------------------------------------------------------------------------
# 4. Reglas, atributos y dependencias (10 casos)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("caso, mensaje", [
    ("atributo_duplicado", "está repetido"),
    ("regla_duplicada", "está repetida"),
    ("referencia_inexistente", "no existe"),
    ("rango_invertido", "El valor mínimo debe ser menor"),
])
def test_validar_conocimiento_semantico(contratos_json, caso, mensaje):
    conocimiento = copy.deepcopy(contratos_json["conocimiento_dominio"])

    if caso == "atributo_duplicado":
        conocimiento["attributes"][1]["id"] = conocimiento["attributes"][0]["id"]
    elif caso == "regla_duplicada":
        conocimiento["rules"][1]["id"] = conocimiento["rules"][0]["id"]
    elif caso == "referencia_inexistente":
        conocimiento["rules"][0]["conditions"][0]["attribute_id"] = "fantasma"
    elif caso == "rango_invertido":
        conocimiento["attributes"][1]["range"] = [100, 0]

    errores = SchemaManager.validar_conocimiento(conocimiento)
    assert any(mensaje in error for error in errores)


@pytest.mark.parametrize("caso, mensaje", [
    ("operador_no_numerico", "requiere un atributo numérico"),
    ("opcion_invalida", "no está entre las opciones"),
    ("dependencia_propia", "no puede depender de sí mismo"),
    ("dependencia_inexistente", "no existe"),
])
def test_validar_condiciones_semanticas(contratos_json, caso, mensaje):
    conocimiento = copy.deepcopy(contratos_json["conocimiento_dominio"])

    if caso == "operador_no_numerico":
        conocimiento["rules"][0]["conditions"][0]["operator"] = ">"
    elif caso == "opcion_invalida":
        conocimiento["rules"][0]["conditions"][0]["value"] = "Otra"
    elif caso == "dependencia_propia":
        conocimiento["attributes"][1]["depends_on"] = {
            "attribute_id": "puntaje_final", "operator": ">=", "value": 80,
        }
    elif caso == "dependencia_inexistente":
        conocimiento["attributes"][1]["depends_on"] = {
            "attribute_id": "fantasma", "operator": "==", "value": "x",
        }

    errores = SchemaManager().validar_condiciones(conocimiento)
    assert any(mensaje in error for error in errores)


@pytest.mark.parametrize("con_ciclo", [False, True])
def test_validar_dependencias_circulares(contratos_json, con_ciclo):
    conocimiento = copy.deepcopy(contratos_json["conocimiento_dominio"])
    if con_ciclo:
        conocimiento["attributes"][0]["depends_on"] = {
            "attribute_id": "puntaje_final", "operator": ">=", "value": 80,
        }
        conocimiento["attributes"][1]["depends_on"] = {
            "attribute_id": "tipo_consulta", "operator": "==", "value": "Calificacion",
        }

    errores = SchemaManager.validar_dependencias_circulares(conocimiento)
    assert bool(errores) == con_ciclo
    if con_ciclo:
        assert any("Dependencia circular" in error for error in errores)


# -----------------------------------------------------------------------------
# 5. Trazas, dictámenes y validación conjunta (19 casos)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("caso", ["calificacion", "repeticion_a", "repeticion_d"])
def test_traza_valida(casos_de_sesion, caso):
    conocimiento, memoria, _ = casos_de_sesion(caso)
    resultado = SchemaManager().validar_traza(memoria, conocimiento)
    assert resultado == {"valido": True, "errores": []}


@pytest.mark.parametrize("cambio, texto_esperado", [
    ("regla_derivada_inexistente", "no existe"),
    ("conclusion_distinta", "no produce el hecho"),
    ("valor_distinto", "no coincide"),
    ("sin_registro", "Falta el registro"),
    ("regla_traza_inexistente", "no existe"),
    ("hecho_traza_incorrecto", "no produce"),
])
def test_traza_invalida(casos_de_sesion, cambio, texto_esperado):
    conocimiento, memoria, _ = casos_de_sesion("calificacion")

    if cambio == "regla_derivada_inexistente":
        memoria["derived_facts"]["dictamen"]["derived_by_rule"] = "reg_no_existe"
    elif cambio == "conclusion_distinta":
        memoria["derived_facts"]["otro_hecho"] = memoria["derived_facts"].pop("dictamen")
    elif cambio == "valor_distinto":
        memoria["derived_facts"]["dictamen"]["value"] = "Otro dictamen"
    elif cambio == "sin_registro":
        memoria["execution_trace"] = []
    elif cambio == "regla_traza_inexistente":
        memoria["execution_trace"][0]["rule_fired"] = "reg_no_existe"
    elif cambio == "hecho_traza_incorrecto":
        memoria["execution_trace"][0]["added_fact"] = "otro_hecho"

    resultado = SchemaManager().validar_traza(memoria, conocimiento)
    assert resultado["valido"] is False
    assert any(texto_esperado in error for error in resultado["errores"])


@pytest.mark.parametrize("caso", ["calificacion", "repeticion_a", "repeticion_d"])
def test_dictamen_valido(casos_de_sesion, caso):
    _, memoria, dictamen = casos_de_sesion(caso)
    resultado = SchemaManager().validar_dictamen(dictamen, memoria, "dictamen")
    assert resultado == {"valido": True, "errores": []}


@pytest.mark.parametrize("cambio, texto_esperado", [
    ("sesion_diferente", "sesiones diferentes"),
    ("resultado_distinto", "no coincide"),
    ("hecho_derivado_ausente", "No existe el hecho derivado"),
])
def test_dictamen_invalido(casos_de_sesion, cambio, texto_esperado):
    _, memoria, dictamen = casos_de_sesion("calificacion")

    if cambio == "sesion_diferente":
        dictamen["session_id"] = "otra_sesion"
    elif cambio == "resultado_distinto":
        dictamen["final_outcome"] = "Resultado no coincidente"
    elif cambio == "hecho_derivado_ausente":
        memoria["derived_facts"].pop("dictamen")

    resultado = SchemaManager().validar_dictamen(dictamen, memoria, "dictamen")
    assert resultado["valido"] is False
    assert any(texto_esperado in error for error in resultado["errores"])


@pytest.mark.parametrize("caso", ["calificacion", "repeticion_a", "repeticion_d"])
def test_conjunto_valido(casos_de_sesion, caso):
    conocimiento, memoria, dictamen = casos_de_sesion(caso)
    resultado = SchemaManager().validar_conjunto(conocimiento, memoria, dictamen, "dictamen")
    assert resultado == {"valido": True, "errores": []}


def test_conjunto_rechaza_puntaje_fuera_de_rango(casos_de_sesion):
    conocimiento, memoria, dictamen = casos_de_sesion("calificacion")
    memoria["facts"]["puntaje_final"] = 101
    resultado = SchemaManager().validar_conjunto(conocimiento, memoria, dictamen, "dictamen")
    assert resultado["valido"] is False
    assert any("fuera del rango" in error for error in resultado["errores"])


# -----------------------------------------------------------------------------
# 6. Archivos, caché, versiones, valores y ciclos: pruebas complementarias
# -----------------------------------------------------------------------------
# 6.1. Carga y validación de archivos (15 casos)
@pytest.mark.parametrize("tipo", TIPOS)
def test_archivo_de_ejemplo_valido(tipo):
    resultado = SchemaManager().validar_archivo(EJEMPLOS / f"{tipo}.json", tipo)
    assert resultado == {"valido": True, "errores": []}


def test_cargar_json_con_bom(tmp_path):
    ruta = tmp_path / "bom.json"
    ruta.write_text('{"dato": 5}', encoding="utf-8-sig")
    assert SchemaManager.cargar_json(ruta) == {"dato": 5}


@pytest.mark.parametrize("constante", ["NaN", "Infinity", "-Infinity"])
def test_cargar_json_rechaza_constantes_no_estandar(tmp_path, constante):
    ruta = tmp_path / "no_estandar.json"
    ruta.write_text('{"dato": ' + constante + '}', encoding="utf-8")
    with pytest.raises(ValueError, match="Constante numérica no válida"):
        SchemaManager.cargar_json(ruta)


def test_cargar_json_malformado(tmp_path):
    ruta = tmp_path / "incorrecto.json"
    ruta.write_text('{"x": ', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        SchemaManager.cargar_json(ruta)


def test_validar_archivo_inexistente(tmp_path):
    resultado = SchemaManager().validar_archivo(tmp_path / "no_existe.json", "memoria_trabajo")
    assert not resultado["valido"]
    assert "No se encontró el archivo" in " ".join(resultado["errores"])


def test_validar_archivo_json_incorrecto(tmp_path):
    ruta = tmp_path / "roto.json"
    ruta.write_text('{"facts": ', encoding="utf-8")
    resultado = SchemaManager().validar_archivo(ruta, "memoria_trabajo")
    assert not resultado["valido"]
    assert "JSON mal formado" in " ".join(resultado["errores"])


def test_validar_archivo_rechaza_nan(tmp_path):
    ruta = tmp_path / "nan.json"
    ruta.write_text('{"session_id": NaN}', encoding="utf-8")
    resultado = SchemaManager().validar_archivo(ruta, "memoria_trabajo")
    assert not resultado["valido"]
    assert "JSON inválido" in " ".join(resultado["errores"])


def test_validar_archivo_tipo_desconocido(tmp_path):
    ruta = tmp_path / "datos.json"
    ruta.write_text('{}', encoding="utf-8")
    resultado = SchemaManager().validar_archivo(ruta, "tipo_inexistente")
    assert not resultado["valido"]
    assert "Tipo de contrato desconocido" in " ".join(resultado["errores"])


def test_validar_archivo_esquema_ausente(tmp_path):
    ruta = tmp_path / "datos.json"
    ruta.write_text('{}', encoding="utf-8")
    resultado = SchemaManager(carpeta_esquemas=tmp_path).validar_archivo(ruta, "memoria_trabajo")
    assert not resultado["valido"]
    assert "No se encontró el esquema" in " ".join(resultado["errores"])


def test_validar_archivo_esquema_json_roto(tmp_path):
    ruta_datos = tmp_path / "datos.json"
    ruta_datos.write_text('{}', encoding="utf-8")
    (tmp_path / "memoria_trabajo.schema.json").write_text('{', encoding="utf-8")
    resultado = SchemaManager(carpeta_esquemas=tmp_path).validar_archivo(
        ruta_datos, "memoria_trabajo"
    )
    assert not resultado["valido"]
    assert "Expecting" in " ".join(resultado["errores"])  # El código actual devuelve el error del decodificador


def test_validar_archivo_esquema_incorrecto(tmp_path):
    ruta_datos = tmp_path / "datos.json"
    ruta_datos.write_text('{}', encoding="utf-8")
    (tmp_path / "memoria_trabajo.schema.json").write_text(
        json.dumps({"type": "tipo_no_permitido"}), encoding="utf-8"
    )
    resultado = SchemaManager(carpeta_esquemas=tmp_path).validar_archivo(
        ruta_datos, "memoria_trabajo"
    )
    assert not resultado["valido"]
    assert "esquema de validación es incorrecto" in " ".join(resultado["errores"])


# 6.2. Caché de esquemas (5 casos)
def test_cache_reutiliza_validador():
    gestor = SchemaManager()
    uno = gestor._obtener_validador("memoria_trabajo")
    dos = gestor._obtener_validador("memoria_trabajo")
    assert uno is dos


def test_limpiar_cache_invalida_validadores():
    gestor = SchemaManager()
    antes = gestor._obtener_validador("memoria_trabajo")
    gestor.limpiar_cache_esquemas()
    despues = gestor._obtener_validador("memoria_trabajo")
    assert despues is not antes


def test_cache_detecta_cambio_en_archivo(gestor_esquemas_temporales):
    gestor = gestor_esquemas_temporales
    antes = gestor._obtener_validador("memoria_trabajo")
    ruta = gestor.carpeta_esquemas / "memoria_trabajo.schema.json"
    contenido = ruta.read_text(encoding="utf-8")
    ruta.write_text(contenido + "\n", encoding="utf-8")
    despues = gestor._obtener_validador("memoria_trabajo")
    assert despues is not antes


def test_cache_limitada_a_tres_contratos():
    gestor = SchemaManager()
    for tipo in TIPOS:
        gestor._obtener_validador(tipo)
    assert set(gestor._cache_validadores) == set(TIPOS)
    assert len(gestor._cache_validadores) == 3


def test_cache_independiente_por_instancia():
    primero, segundo = SchemaManager(), SchemaManager()
    assert primero._obtener_validador("memoria_trabajo") is not segundo._obtener_validador(
        "memoria_trabajo"
    )


# 6.3. Versiones de conocimiento (9 casos)
def test_validar_version_del_ejemplo(conocimiento):
    assert SchemaManager().validar_version(conocimiento) == []


def test_version_admitida_como_texto(conocimiento):
    version = conocimiento["meta"]["version"]
    assert SchemaManager(versiones_admitidas=version).validar_version(conocimiento) == []


def test_version_admitida_en_lista(conocimiento):
    version = conocimiento["meta"]["version"]
    assert SchemaManager(versiones_admitidas=["0.9", version]).validar_version(conocimiento) == []


def test_version_no_admitida(conocimiento):
    resultado = SchemaManager(versiones_admitidas=["9.9"]).validar_version(conocimiento)
    assert any("no está entre las versiones admitidas" in mensaje for mensaje in resultado)


@pytest.mark.parametrize("version", ["", "   ", None, 2, False])
def test_version_vacia_o_tipo_incorrecto(conocimiento, version):
    datos = copy.deepcopy(conocimiento)
    datos["meta"]["version"] = version
    resultado = SchemaManager().validar_version(datos)
    assert any("texto no vacío" in mensaje for mensaje in resultado)


# 6.4. Tipos y rangos de los valores (20 casos)
@pytest.mark.parametrize("valor", [0, 85, 85.5, 100])
def test_valor_numerico_valido(valor):
    atributo = {"type": "numeric", "range": [0, 100]}
    assert SchemaManager._comprobar_valor(atributo, valor, "$.valor", True) == []


@pytest.mark.parametrize("valor, mensaje", [
    (True, "Se esperaba un número"),
    ("90", "Se esperaba un número"),
    (None, "Se esperaba un número"),
    (float("nan"), "número finito"),
    (float("inf"), "número finito"),
    (float("-inf"), "número finito"),
])
def test_valor_numerico_tipo_o_finito_incorrecto(valor, mensaje):
    atributo = {"type": "numeric", "range": [0, 100]}
    errores = SchemaManager._comprobar_valor(atributo, valor, "$.valor", True)
    assert any(mensaje in error for error in errores)


@pytest.mark.parametrize("valor", [-0.01, 100.01])
def test_valor_numerico_fuera_de_rango(valor):
    atributo = {"type": "numeric", "range": [0, 100]}
    errores = SchemaManager._comprobar_valor(atributo, valor, "$.valor", True)
    assert any("fuera del rango" in error for error in errores)


@pytest.mark.parametrize("valor", ["Calificacion", "Repeticion"])
def test_valor_categorico_correcto(valor):
    atributo = {"type": "categorical", "options": ["Calificacion", "Repeticion"]}
    assert SchemaManager._comprobar_valor(atributo, valor, "$.tipo") == []


@pytest.mark.parametrize("valor, mensaje", [
    (20, "Se esperaba un texto"),
    ("Otra", "no está entre las opciones"),
])
def test_valor_categorico_incorrecto(valor, mensaje):
    atributo = {"type": "categorical", "options": ["Calificacion", "Repeticion"]}
    errores = SchemaManager._comprobar_valor(atributo, valor, "$.tipo")
    assert any(mensaje in error for error in errores)


@pytest.mark.parametrize("valor", ["true", 1])
def test_valor_booleano_incorrecto(valor):
    assert SchemaManager._comprobar_valor({"type": "boolean"}, valor, "$.activo") == [
        "$.activo: Se esperaba true o false."
    ]


@pytest.mark.parametrize("valor", [4, None])
def test_valor_texto_incorrecto(valor):
    assert SchemaManager._comprobar_valor({"type": "text"}, valor, "$.texto") == [
        "$.texto: Se esperaba un texto."
    ]


# 6.5. Dependencias de longitud mayor que dos (1 caso)
def test_detecta_ciclo_de_tres_atributos(conocimiento):
    datos = copy.deepcopy(conocimiento)
    dependencias = {
        "tipo_consulta": {"attribute_id": "puntaje_final", "operator": ">=", "value": 80},
        "puntaje_final": {"attribute_id": "nota_obtenida", "operator": "==", "value": "A"},
        "nota_obtenida": {"attribute_id": "tipo_consulta", "operator": "==", "value": "Calificacion"},
    }
    for atributo in datos["attributes"]:
        atributo["depends_on"] = dependencias[atributo["id"]]
    errores = SchemaManager.validar_dependencias_circulares(datos)
    assert any("Dependencia circular" in error for error in errores)
