"""Pruebas del QuestionEditor (Grupo 1).

Se ejecutan desde la raiz del repositorio con:

    python -m pytest grupo_01_questions

Las pruebas marcadas con ``@pytest.mark.skip`` corresponden a metodos que
todavia no se implementan en el stub. Cuando el Integrante responsable las
implemente, debe quitar el marcador ``skip`` para que la prueba corra.
"""

import json
from pathlib import Path

import pytest

from grupo_01_questions import (
    Attribute,
    AttributeExistsError,
    AttributeNotFoundError,
    DependsOn,
    QuestionEditor,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Pruebas del stub (ya funcionan)
# ---------------------------------------------------------------------------


def test_attribute_se_construye_con_campos_minimos():
    attr = Attribute(id="promedio", name="Promedio", type="numeric")
    assert attr.id == "promedio"
    assert attr.options == []
    assert attr.depends_on is None


def test_attribute_to_dict_omite_opcionales_vacios():
    attr = Attribute(id="promedio", name="Promedio", type="numeric")
    datos = attr.to_dict()
    assert datos == {"id": "promedio", "name": "Promedio", "type": "numeric"}


def test_attribute_from_dict_reconstruye_depends_on():
    datos = {
        "id": "nombre_tesis",
        "name": "Nombre del trabajo de graduacion",
        "type": "text",
        "question": "Cual es el nombre de tu tesis?",
        "depends_on": {
            "attribute_id": "materia",
            "operator": "==",
            "value": "Trabajo de Graduacion",
        },
    }
    attr = Attribute.from_dict(datos)
    assert isinstance(attr.depends_on, DependsOn)
    assert attr.depends_on.attribute_id == "materia"


def test_add_y_get_atributo():
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="Promedio", type="numeric"))
    assert editor.get_attribute("promedio").name == "Promedio"


def test_add_rechaza_duplicados():
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="Promedio", type="numeric"))
    with pytest.raises(AttributeExistsError):
        editor.add_attribute(Attribute(id="promedio", name="Otro", type="numeric"))


def test_edit_modifica_un_campo():
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="Promedio", type="numeric"))
    editor.edit_attribute("promedio", name="Promedio Ponderado")
    assert editor.get_attribute("promedio").name == "Promedio Ponderado"


def test_delete_elimina_el_atributo():
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="Promedio", type="numeric"))
    editor.delete_attribute("promedio")
    with pytest.raises(AttributeNotFoundError):
        editor.get_attribute("promedio")


def test_list_conserva_orden_de_insercion():
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="materia", name="Materia", type="categorical",
                                   options=["A", "B"]))
    editor.add_attribute(Attribute(id="promedio", name="Promedio", type="numeric"))
    ids = [a.id for a in editor.list_attributes()]
    assert ids == ["materia", "promedio"]


def test_operaciones_sobre_atributo_inexistente_fallan():
    editor = QuestionEditor()
    with pytest.raises(AttributeNotFoundError):
        editor.get_attribute("no_existe")
    with pytest.raises(AttributeNotFoundError):
        editor.delete_attribute("no_existe")
    with pytest.raises(AttributeNotFoundError):
        editor.edit_attribute("no_existe", name="x")


# ---------------------------------------------------------------------------
# Pruebas pendientes (Sprint 1) - las implementa el Integrante responsable
# ---------------------------------------------------------------------------



def test_validate_rechaza_tipo_invalido():
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="x", name="X", type="tipo_inexistente"))
    resultado = editor.validate()
    assert resultado["valido"] is False
    assert any("tipo" in e.lower() for e in resultado["errores"])



def test_validate_rechaza_rango_invertido():
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="Promedio",
                                   type="numeric", range=[3.0, 0.0]))
    resultado = editor.validate()
    assert resultado["valido"] is False



def test_validate_rechaza_categorico_sin_opciones():
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="materia", name="Materia", type="categorical"))
    resultado = editor.validate()
    assert resultado["valido"] is False



def test_validate_rechaza_depends_on_a_atributo_inexistente():
    editor = QuestionEditor()
    editor.add_attribute(Attribute(
        id="nombre_tesis", name="Nombre tesis", type="text",
        depends_on=DependsOn(attribute_id="materia", operator="==",
                             value="Trabajo de Graduacion")))
    resultado = editor.validate()
    assert resultado["valido"] is False


def test_round_trip_json(tmp_path):
    ruta = tmp_path / "conocimiento.json"
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="Promedio",
                                   type="numeric", range=[0.0, 3.0],
                                   question="Cual es tu promedio?"))
    editor.add_attribute(Attribute(id="materia", name="Materia",
                                   type="categorical",
                                   options=["Obligatoria", "Electiva"],
                                   question="Que materia?"))
    editor.save_to_json(str(ruta))

    otro = QuestionEditor()
    otro.load_from_json(str(ruta))
    assert [a.id for a in otro.list_attributes()] == ["promedio", "materia"]
    assert otro.get_attribute("promedio").range == [0.0, 3.0]


def test_load_preserva_depends_on(tmp_path):
    ruta = tmp_path / "conocimiento.json"
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="materia", name="Materia",
                                   type="categorical",
                                   options=["A", "B"]))
    editor.add_attribute(Attribute(
        id="detalle", name="Detalle", type="text",
        depends_on=DependsOn(attribute_id="materia", operator="==", value="A")))
    editor.save_to_json(str(ruta))

    otro = QuestionEditor()
    otro.load_from_json(str(ruta))
    detalle = otro.get_attribute("detalle")
    assert detalle.depends_on is not None
    assert detalle.depends_on.attribute_id == "materia"


def test_save_preserva_otras_secciones(tmp_path):
    ruta = tmp_path / "dominio.json"
    datos = {"meta": {"titulo": "Evaluación"}, "rules": [{"id": "r1"}],
             "extension": {"activo": True}, "attributes": []}
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="tesis", name="Título", type="text",
                                   help_text="Escriba el título"))
    editor.save_to_json(ruta)
    guardado = json.loads(ruta.read_text(encoding="utf-8"))
    assert guardado == {**datos, "attributes": [editor.get_attribute("tesis").to_dict()]}
    assert "Título" in ruta.read_text(encoding="utf-8")


def test_load_sample_reemplaza_estado_y_conserva_campos(tmp_path):
    muestra = Path(__file__).parents[1] / "datos_ejemplo/conocimiento_dominio.sample.json"
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="viejo", name="Viejo", type="text"))
    editor.load_from_json(muestra)
    datos = json.loads(muestra.read_text(encoding="utf-8"))
    assert [a.to_dict() for a in editor.list_attributes()] == datos["attributes"]
    ruta = tmp_path / "nuevo.json"
    editor.save_to_json(ruta)
    guardado = json.loads(ruta.read_text(encoding="utf-8"))
    assert guardado["attributes"] == datos["attributes"]
    assert guardado["rules"] == []
    assert set(guardado["meta"]) == {"project_title", "version", "author_group"}


@pytest.mark.parametrize("contenido, error", [
    ("{", json.JSONDecodeError),
    ("[]", ValidationError),
    ('{"attributes": {}}', ValidationError),
    ('{"attributes": [{"id": "nuevo", "name": "Nuevo", "type": "text"}, {}]}', KeyError),
    ('{"attributes": [null]}', ValidationError),
    ('{"attributes": [{"id": "x", "name": "X", "type": "text"}, '
     '{"id": "x", "name": "Otro", "type": "text"}]}', AttributeExistsError),
])
def test_load_fallido_conserva_estado(tmp_path, contenido, error):
    ruta = tmp_path / "dominio.json"
    ruta.write_text(contenido, encoding="utf-8")
    editor = QuestionEditor()
    previo = Attribute(id="previo", name="Previo", type="text")
    editor.add_attribute(previo)
    with pytest.raises(error):
        editor.load_from_json(ruta)
    assert editor.list_attributes() == [previo]


@pytest.mark.parametrize("contenido, error", [("{", json.JSONDecodeError),
                                              ("[]", ValidationError)])
def test_save_no_sobrescribe_documento_invalido(tmp_path, contenido, error):
    ruta = tmp_path / "dominio.json"
    ruta.write_text(contenido, encoding="utf-8")
    with pytest.raises(error):
        QuestionEditor().save_to_json(ruta)
    assert ruta.read_text(encoding="utf-8") == contenido


def test_save_error_serializacion_conserva_archivo(tmp_path):
    ruta = tmp_path / "dominio.json"
    ruta.write_text('{"meta": {}, "rules": []}', encoding="utf-8")
    previo = ruta.read_bytes()
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="x", name="X", type="numeric",
                                   range=[0, float("nan")]))
    with pytest.raises(ValueError):
        editor.save_to_json(ruta)
    assert ruta.read_bytes() == previo


def test_load_lista_vacia_limpia_editor(tmp_path):
    ruta = tmp_path / "dominio.json"
    ruta.write_text('{"attributes": []}', encoding="utf-8")
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="x", name="X", type="text"))
    editor.load_from_json(ruta)
    assert editor.list_attributes() == []


def test_load_archivo_inexistente_conserva_estado(tmp_path):
    editor = QuestionEditor()
    previo = Attribute(id="x", name="X", type="text")
    editor.add_attribute(previo)
    with pytest.raises(FileNotFoundError):
        editor.load_from_json(tmp_path / "inexistente.json")
    assert editor.list_attributes() == [previo]
