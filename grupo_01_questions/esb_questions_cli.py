"""Interfaz de linea de comandos del QuestionEditor (Grupo 1).

Envuelve ``QuestionEditor`` y le permite al experto del dominio crear, editar,
listar y eliminar atributos y preguntas sin escribir codigo Python.

Ejecucion desde la raiz del repositorio:

    python -m grupo_01_questions.esb_questions_cli

O bien:

    python grupo_01_questions/esb_questions_cli.py

Diseño: la CLI es una capa fina sobre ``QuestionEditor`` y no duplica logica.
Los metodos del editor se llaman tal cual; esta capa solo se ocupa de dialogar
con el usuario, validar sus entradas y mostrar resultados.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional

from .esb_questions import (
    OPERADORES_VALIDOS,
    TIPOS_VALIDOS,
    Attribute,
    AttributeExistsError,
    AttributeNotFoundError,
    DependsOn,
    QuestionEditor,
)


# ---------------------------------------------------------------------------
# Utilidades de entrada y salida
# ---------------------------------------------------------------------------

BANNER = r"""
=================================================================
 ES-Shell Suite - Editor de preguntas y atributos (Grupo 1)
=================================================================
"""


def _preguntar(texto: str, obligatorio: bool = True,
               por_defecto: Optional[str] = None) -> str:
    """Pide una cadena por consola.

    Si ``obligatorio`` es ``False`` y el usuario deja vacio, devuelve
    ``por_defecto`` (o ``""`` si no se indica). Si es obligatorio, repite
    hasta que ingrese algo no vacio.
    """
    sufijo = ""
    if not obligatorio:
        sufijo = f" [Enter para dejar vacio]" if por_defecto is None else f" [Enter = {por_defecto}]"
    while True:
        respuesta = input(f"{texto}{sufijo}: ").strip()
        if respuesta:
            return respuesta
        if not obligatorio:
            return por_defecto if por_defecto is not None else ""
        print("  (Este campo es obligatorio.)")


def _preguntar_opcion(texto: str, opciones: list[str]) -> str:
    """Pide elegir una de varias opciones; repite hasta acertar."""
    while True:
        print(texto)
        for i, op in enumerate(opciones, 1):
            print(f"  {i}) {op}")
        respuesta = input("Numero de opcion: ").strip()
        if respuesta.isdigit() and 1 <= int(respuesta) <= len(opciones):
            return opciones[int(respuesta) - 1]
        print(f"  (Entrada invalida. Ingresa un numero entre 1 y {len(opciones)}.)")


def _preguntar_si_no(texto: str, por_defecto: bool = False) -> bool:
    default_texto = "s/N" if not por_defecto else "S/n"
    while True:
        respuesta = input(f"{texto} [{default_texto}]: ").strip().lower()
        if not respuesta:
            return por_defecto
        if respuesta in ("s", "si", "sí", "y", "yes"):
            return True
        if respuesta in ("n", "no"):
            return False
        print("  (Responde 's' o 'n'.)")


def _preguntar_numero(texto: str, obligatorio: bool = True) -> Optional[float]:
    while True:
        respuesta = input(f"{texto}: ").strip()
        if not respuesta:
            if obligatorio:
                print("  (Este campo es obligatorio.)")
                continue
            return None
        try:
            return float(respuesta)
        except ValueError:
            print("  (Ingresa un numero valido, por ejemplo 2.5.)")


def _mostrar_atributo(attr: Attribute, prefijo: str = "") -> None:
    print(f"{prefijo}- id: {attr.id}")
    print(f"{prefijo}  name: {attr.name}")
    print(f"{prefijo}  type: {attr.type}")
    if attr.question:
        print(f"{prefijo}  question: {attr.question}")
    if attr.range:
        print(f"{prefijo}  range: {attr.range}")
    if attr.options:
        print(f"{prefijo}  options: {attr.options}")
    if attr.help_text:
        print(f"{prefijo}  help_text: {attr.help_text}")
    if attr.depends_on:
        d = attr.depends_on
        print(f"{prefijo}  depends_on: {d.attribute_id} {d.operator} {d.value!r}")


# ---------------------------------------------------------------------------
# Acciones del menu
# ---------------------------------------------------------------------------


def accion_agregar_atributo(editor: QuestionEditor) -> None:
    """Dialoga paso a paso con el usuario para crear un atributo nuevo."""
    print("\n--- Agregar atributo ---")
    attr_id = _preguntar("ID unico del atributo (ej. 'promedio')")
    name = _preguntar("Nombre legible (ej. 'Promedio Ponderado Acumulado')")
    tipo = _preguntar_opcion("Tipo:", list(TIPOS_VALIDOS))

    # Pregunta al usuario solo si el atributo se preguntara durante la consulta.
    es_pregunta = _preguntar_si_no("¿Este atributo se le preguntara al usuario?",
                                   por_defecto=True)
    question: Optional[str] = None
    help_text: Optional[str] = None
    if es_pregunta:
        question = _preguntar("Texto de la pregunta")
        help_text = _preguntar("Texto de ayuda adicional", obligatorio=False) or None

    # Campos segun el tipo.
    rango: Optional[list[float]] = None
    opciones: list = []
    if tipo == "numeric":
        if _preguntar_si_no("¿Quieres definir un rango [min, max]?", por_defecto=False):
            minimo = _preguntar_numero("  Valor minimo")
            maximo = _preguntar_numero("  Valor maximo")
            rango = [minimo, maximo]
    elif tipo == "categorical":
        print("Ingresa las opciones una por una. Enter vacio para terminar.")
        while True:
            op = input(f"  Opcion {len(opciones) + 1}: ").strip()
            if not op:
                if opciones:
                    break
                print("  (Al menos una opcion es obligatoria para 'categorical'.)")
                continue
            if op in opciones:
                print("  (Opcion repetida, ignorada.)")
                continue
            opciones.append(op)

    # Pregunta condicional (opcional).
    depends_on: Optional[DependsOn] = None
    if _preguntar_si_no("¿Esta pregunta es condicional (depende de otro atributo)?",
                        por_defecto=False):
        depends_on = _dialogar_depends_on(editor)

    attr = Attribute(id=attr_id, name=name, type=tipo, question=question,
                     range=rango, options=opciones, help_text=help_text,
                     depends_on=depends_on)
    try:
        editor.add_attribute(attr)
        print(f"\n✓ Atributo '{attr.id}' agregado.")
    except AttributeExistsError as e:
        print(f"\n✗ Error: {e}")


def _dialogar_depends_on(editor: QuestionEditor) -> Optional[DependsOn]:
    """Dialogo pequeño para construir una condicion ``DependsOn``."""
    atributos_disponibles = [a.id for a in editor.list_attributes()]
    if not atributos_disponibles:
        print("  (No hay atributos previos sobre los que depender. Se omite.)")
        return None
    print(f"  Atributos disponibles: {', '.join(atributos_disponibles)}")
    attribute_id = _preguntar("  ID del atributo del que depende")
    operador = _preguntar_opcion("  Operador:", list(OPERADORES_VALIDOS))
    valor_texto = _preguntar("  Valor con el que se compara (como texto)")
    # Intentamos convertir a numero si procede; si no, se queda como texto.
    valor: object = valor_texto
    try:
        valor = float(valor_texto)
        if valor.is_integer():
            valor = int(valor)
    except ValueError:
        pass
    return DependsOn(attribute_id=attribute_id, operator=operador, value=valor)


def accion_editar_atributo(editor: QuestionEditor) -> None:
    print("\n--- Editar atributo ---")
    attr_id = _preguntar("ID del atributo a editar")
    try:
        attr = editor.get_attribute(attr_id)
    except AttributeNotFoundError as e:
        print(f"✗ Error: {e}")
        return
    print("Atributo actual:")
    _mostrar_atributo(attr, prefijo="  ")
    print("\nCampos editables: name, question, help_text")
    campo = _preguntar_opcion("¿Que campo quieres cambiar?",
                              ["name", "question", "help_text"])
    nuevo_valor = _preguntar(f"Nuevo valor para '{campo}'", obligatorio=False)
    try:
        editor.edit_attribute(attr_id, **{campo: nuevo_valor or None})
        print(f"✓ Atributo '{attr_id}' actualizado.")
    except Exception as e:
        print(f"✗ Error: {e}")


def accion_eliminar_atributo(editor: QuestionEditor) -> None:
    print("\n--- Eliminar atributo ---")
    attr_id = _preguntar("ID del atributo a eliminar")
    try:
        editor.get_attribute(attr_id)
    except AttributeNotFoundError as e:
        print(f"✗ Error: {e}")
        return
    if _preguntar_si_no(f"¿Seguro que quieres eliminar '{attr_id}'?", por_defecto=False):
        editor.delete_attribute(attr_id)
        print(f"✓ Atributo '{attr_id}' eliminado.")
    else:
        print("Cancelado.")


def accion_listar_atributos(editor: QuestionEditor) -> None:
    print("\n--- Listado de atributos ---")
    atributos = editor.list_attributes()
    if not atributos:
        print("(La base esta vacia.)")
        return
    print(f"Total: {len(atributos)} atributo(s), en orden de insercion.\n")
    for attr in atributos:
        _mostrar_atributo(attr)
        print()


def accion_validar(editor: QuestionEditor) -> None:
    print("\n--- Validar base de atributos ---")
    try:
        resultado = editor.validate()
    except NotImplementedError:
        print("  (Pendiente de implementacion en Sprint 1 por el Integrante B.)")
        return
    if resultado.get("valido"):
        print("✓ La base es valida.")
    else:
        print("✗ La base tiene errores:")
        for error in resultado.get("errores", []):
            print(f"  - {error}")


def accion_cargar(editor: QuestionEditor) -> None:
    print("\n--- Cargar desde archivo JSON ---")
    ruta = _preguntar("Ruta del archivo a cargar")
    if not Path(ruta).exists():
        print(f"✗ Error: el archivo '{ruta}' no existe.")
        return
    try:
        editor.load_from_json(ruta)
        print(f"✓ Archivo '{ruta}' cargado.")
    except NotImplementedError:
        print("  (Pendiente de implementacion en Sprint 1 por el Integrante A.)")
    except Exception as e:
        print(f"✗ Error: {e}")


def accion_guardar(editor: QuestionEditor) -> None:
    print("\n--- Guardar a archivo JSON ---")
    ruta = _preguntar("Ruta de salida")
    try:
        editor.save_to_json(ruta)
        print(f"✓ Guardado en '{ruta}'.")
    except NotImplementedError:
        print("  (Pendiente de implementacion en Sprint 1 por el Integrante A.)")
    except Exception as e:
        print(f"✗ Error: {e}")


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------


OPCIONES_MENU: list[tuple[str, Callable[[QuestionEditor], None]]] = [
    ("Agregar atributo", accion_agregar_atributo),
    ("Editar atributo", accion_editar_atributo),
    ("Eliminar atributo", accion_eliminar_atributo),
    ("Listar atributos", accion_listar_atributos),
    ("Validar base", accion_validar),
    ("Cargar desde archivo JSON", accion_cargar),
    ("Guardar a archivo JSON", accion_guardar),
]


def _mostrar_menu() -> None:
    print("\n----- Menu principal -----")
    for i, (etiqueta, _) in enumerate(OPCIONES_MENU, 1):
        print(f"  {i}) {etiqueta}")
    print("  0) Salir")


def ejecutar_menu(editor: Optional[QuestionEditor] = None,
                  entrada_salir: str = "0") -> QuestionEditor:
    """Corre el loop del menu interactivo.

    Devuelve el editor con todo lo que el usuario haya agregado, para que
    las pruebas puedan inspeccionar el estado final.
    """
    editor = editor or QuestionEditor()
    print(BANNER)
    while True:
        _mostrar_menu()
        eleccion = input("Opcion: ").strip()
        if eleccion == entrada_salir:
            print("Hasta pronto.")
            return editor
        if not eleccion.isdigit() or not 1 <= int(eleccion) <= len(OPCIONES_MENU):
            print("  (Opcion invalida.)")
            continue
        _, accion = OPCIONES_MENU[int(eleccion) - 1]
        try:
            accion(editor)
        except KeyboardInterrupt:
            print("\n(Operacion cancelada.)")


def main() -> int:
    try:
        ejecutar_menu()
    except (KeyboardInterrupt, EOFError):
        print("\nHasta pronto.")
        return 0
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
