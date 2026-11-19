"""Pruebas de la CLI del Grupo 1.

Usa ``monkeypatch`` de pytest para simular las entradas del usuario y
``capsys`` para capturar la salida que la CLI escribe en pantalla.
"""

import pytest

from grupo_01_questions import Attribute, QuestionEditor
from grupo_01_questions.esb_questions_cli import (
    accion_agregar_atributo,
    accion_editar_atributo,
    accion_eliminar_atributo,
    accion_listar_atributos,
    accion_validar,
    ejecutar_menu,
)


def _simular_entradas(monkeypatch, entradas):
    """Hace que las llamadas a input() consuman una lista de respuestas."""
    iterador = iter(entradas)
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: next(iterador))


# ---------------------------------------------------------------------------
# Agregar
# ---------------------------------------------------------------------------


def test_agregar_atributo_numerico_simple(monkeypatch, capsys):
    editor = QuestionEditor()
    _simular_entradas(monkeypatch, [
        "promedio",            # id
        "Promedio Ponderado",  # name
        "1",                   # tipo -> numeric
        "s",                   # es_pregunta
        "¿Cual es tu promedio?",
        "",                    # help_text vacio
        "n",                   # rango -> no
        "n",                   # depends_on -> no
    ])
    accion_agregar_atributo(editor)
    salida = capsys.readouterr().out
    assert "agregado" in salida
    attr = editor.get_attribute("promedio")
    assert attr.type == "numeric"
    assert attr.question == "¿Cual es tu promedio?"
    assert attr.range is None
    assert attr.options == []


def test_agregar_atributo_categorico_con_opciones(monkeypatch, capsys):
    editor = QuestionEditor()
    _simular_entradas(monkeypatch, [
        "materia",
        "Tipo de materia",
        "2",   # categorical
        "s",   # es_pregunta
        "¿Que tipo de materia?",
        "",
        "Obligatoria",
        "Electiva",
        "Trabajo de Graduacion",
        "",    # terminar opciones
        "n",   # depends_on -> no
    ])
    accion_agregar_atributo(editor)
    attr = editor.get_attribute("materia")
    assert attr.type == "categorical"
    assert attr.options == ["Obligatoria", "Electiva", "Trabajo de Graduacion"]


def test_agregar_atributo_con_depends_on(monkeypatch, capsys):
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="materia", name="Materia",
                                   type="categorical",
                                   options=["Trabajo de Graduacion", "Electiva"]))
    _simular_entradas(monkeypatch, [
        "nombre_tesis", "Nombre tesis", "4",   # text
        "s", "¿Cual es el titulo?", "",
        "s",                              # depends_on -> si
        "materia", "1", "Trabajo de Graduacion",  # attr_id, operador ==, valor
    ])
    accion_agregar_atributo(editor)
    attr = editor.get_attribute("nombre_tesis")
    assert attr.depends_on is not None
    assert attr.depends_on.attribute_id == "materia"
    assert attr.depends_on.operator == "=="
    assert attr.depends_on.value == "Trabajo de Graduacion"


def test_agregar_rechaza_id_duplicado(monkeypatch, capsys):
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="X", type="numeric"))
    _simular_entradas(monkeypatch, [
        "promedio", "Promedio", "1",
        "s", "¿Promedio?", "",
        "n", "n",
    ])
    accion_agregar_atributo(editor)
    salida = capsys.readouterr().out
    assert "ya existe" in salida.lower()


# ---------------------------------------------------------------------------
# Editar y eliminar
# ---------------------------------------------------------------------------


def test_editar_cambia_un_campo(monkeypatch, capsys):
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="Promedio",
                                   type="numeric"))
    _simular_entradas(monkeypatch, [
        "promedio",         # id
        "1",                # campo -> name
        "Promedio Ponderado",
    ])
    accion_editar_atributo(editor)
    assert editor.get_attribute("promedio").name == "Promedio Ponderado"


def test_editar_atributo_inexistente(monkeypatch, capsys):
    editor = QuestionEditor()
    _simular_entradas(monkeypatch, ["no_existe"])
    accion_editar_atributo(editor)
    salida = capsys.readouterr().out
    assert "no existe" in salida.lower()


def test_eliminar_pide_confirmacion(monkeypatch, capsys):
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="x", name="X", type="numeric"))
    _simular_entradas(monkeypatch, ["x", "s"])
    accion_eliminar_atributo(editor)
    with pytest.raises(Exception):
        editor.get_attribute("x")


def test_eliminar_se_puede_cancelar(monkeypatch, capsys):
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="x", name="X", type="numeric"))
    _simular_entradas(monkeypatch, ["x", "n"])
    accion_eliminar_atributo(editor)
    # No lanza, sigue existiendo
    assert editor.get_attribute("x").id == "x"


# ---------------------------------------------------------------------------
# Listar y validar
# ---------------------------------------------------------------------------


def test_listar_vacio(capsys):
    accion_listar_atributos(QuestionEditor())
    salida = capsys.readouterr().out
    assert "vacia" in salida.lower()


def test_listar_muestra_atributos(capsys):
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="Promedio",
                                   type="numeric", question="¿Promedio?"))
    accion_listar_atributos(editor)
    salida = capsys.readouterr().out
    assert "promedio" in salida
    assert "¿Promedio?" in salida


def test_validar_muestra_resultado_cuando_base_esta_vacia(capsys):
    """Antes esperabamos 'Pendiente' porque validate() no estaba hecho.
    Ahora validate() funciona y detecta que la base esta vacia."""
    accion_validar(QuestionEditor())
    salida = capsys.readouterr().out
    assert "La base" in salida and "vacía" in salida


def test_validar_muestra_ok_cuando_base_es_correcta(capsys):
    """Si la base tiene atributos validos, validate() no reporta errores."""
    editor = QuestionEditor()
    editor.add_attribute(Attribute(id="promedio", name="Promedio",
                                   type="numeric", range=[0.0, 3.0]))
    accion_validar(editor)
    salida = capsys.readouterr().out
    assert "valida" in salida.lower() or "✓" in salida


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------


def test_menu_principal_sale_con_cero(monkeypatch, capsys):
    _simular_entradas(monkeypatch, ["0"])
    editor = ejecutar_menu()
    assert editor.list_attributes() == []
    assert "Hasta pronto" in capsys.readouterr().out


def test_menu_rechaza_opcion_invalida_y_sale(monkeypatch, capsys):
    _simular_entradas(monkeypatch, ["abc", "99", "0"])
    ejecutar_menu()
    assert "invalida" in capsys.readouterr().out.lower()


def test_menu_lista_despues_de_agregar(monkeypatch, capsys):
    _simular_entradas(monkeypatch, [
        "1",                                     # agregar
        "promedio", "Promedio", "1",
        "s", "¿Promedio?", "",
        "n", "n",
        "4",                                     # listar
        "0",                                     # salir
    ])
    editor = ejecutar_menu()
    assert editor.get_attribute("promedio").name == "Promedio"
    salida = capsys.readouterr().out
    assert "promedio" in salida
