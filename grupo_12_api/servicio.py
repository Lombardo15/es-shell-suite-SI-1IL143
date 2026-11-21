"""Logica de servicio de la API del Grupo 12.

ServicioESB orquesta las operaciones que expone la API (cargar conocimiento,
consultar y explicar) sin depender de FastAPI, para mantener separada la
logica de negocio de la capa HTTP.

Estado: stub del 14 de noviembre. Las bases de conocimiento y las sesiones se
guardan en memoria. La inferencia, el dictamen y la explicacion HOW devuelven
los ejemplos de la seccion 4.2 de la guia, guardados en datos_ejemplo/. A
partir del 17 de noviembre cada metodo marcado como "simulado" se conectara al
modulo del grupo correspondiente:

- inferir: ForwardEngine (G5), BackwardEngine (G6), UncertaintyEngine (G7).
- siguiente_pregunta: BackwardEngine (G6) y XAIExplainer.explain_why (G8).
- explicar_how / explicar_why / obtener_traza: XAIExplainer (G8).
- obtener_dictamen: G7 para la certeza y G8 para las explicaciones.
- generar_reporte: ReportGenerator (G9).
- cargar_conocimiento: SchemaManager (G4) para validar y ESBConverter (G11)
  para persistir.
"""

from __future__ import annotations

import copy
import html
import json
from datetime import datetime
from itertools import count
from pathlib import Path
from typing import Any

from .modelos import ConocimientoDominio, Motor

DATOS_EJEMPLO = Path(__file__).parent / "datos_ejemplo"
KB_EJEMPLO = "kb_ejemplo"

MODULOS = {
    "G4 SchemaManager": "simulado",
    "G5 ForwardEngine": "simulado",
    "G6 BackwardEngine": "simulado",
    "G7 UncertaintyEngine": "simulado",
    "G8 XAIExplainer": "simulado",
    "G9 ReportGenerator": "simulado",
    "G11 ESBConverter": "simulado",
}


class NoEncontrado(LookupError):
    """La base de conocimiento, la sesion, el atributo o la regla no existe."""


class EstadoInvalido(RuntimeError):
    """La operacion no se puede hacer en el estado actual de la sesion."""


def cargar_ejemplo(nombre: str) -> dict:
    """Lee uno de los JSON de ejemplo de la seccion 4.2."""
    with open(DATOS_EJEMPLO / f"{nombre}.json", encoding="utf-8") as f:
        return json.load(f)


class ServicioESB:
    """Fachada de la suite que usa la API REST."""

    def __init__(self, precargar_ejemplo: bool = True):
        self._bases: dict[str, dict] = {}
        self._sesiones: dict[str, dict] = {}
        self._kb_ids = count(1)
        self._session_ids = count(1)
        if precargar_ejemplo:
            self._bases[KB_EJEMPLO] = cargar_ejemplo("conocimiento_dominio")

    # --- Conocimiento ---

    def cargar_conocimiento(self, base: ConocimientoDominio) -> tuple[str, dict]:
        """Registra una base ya validada contra el contrato y devuelve su kb_id."""
        kb_id = f"kb_{next(self._kb_ids):03d}"
        self._bases[kb_id] = base.model_dump()
        return kb_id, self._bases[kb_id]

    def obtener_conocimiento(self, kb_id: str) -> dict:
        if kb_id not in self._bases:
            raise NoEncontrado(f"No existe la base de conocimiento '{kb_id}'.")
        return self._bases[kb_id]

    def listar_preguntas(self, kb_id: str) -> list[dict]:
        """Atributos que se le pueden preguntar al usuario, en el orden de la base."""
        return [self._pregunta(a) for a in self.obtener_conocimiento(kb_id)["attributes"]]

    # --- Consultas ---

    def iniciar_consulta(self, kb_id: str, motor: Motor, hechos: dict[str, Any]) -> dict:
        """Crea una sesion con su memoria de trabajo vacia y los hechos iniciales."""
        self.obtener_conocimiento(kb_id)
        session_id = f"sess_{datetime.now().year}_{next(self._session_ids):05d}"
        self._sesiones[session_id] = {
            "kb_id": kb_id,
            "motor": motor,
            "memoria": {
                "session_id": session_id,
                "facts": dict(hechos),
                "derived_facts": {},
                "execution_trace": [],
            },
        }
        return {"session_id": session_id, "kb_id": kb_id, "motor": motor}

    def registrar_hechos(self, session_id: str, hechos: dict[str, Any]) -> dict:
        """Agrega o reemplaza hechos ingresados por el usuario."""
        memoria = self.obtener_memoria(session_id)
        memoria["facts"].update(hechos)
        return memoria

    def siguiente_pregunta(self, session_id: str) -> dict:
        """Proximo dato que necesita el motor. Simulado: primer atributo sin valor."""
        memoria = self.obtener_memoria(session_id)
        kb = self._kb_de(session_id)
        for atributo in kb["attributes"]:
            if atributo["id"] not in memoria["facts"]:
                return {
                    "session_id": session_id,
                    "completa": False,
                    "pregunta": self._pregunta(atributo),
                    "explanation_why": self._texto_why(kb, atributo["id"], None)[1],
                }
        return {"session_id": session_id, "completa": True, "pregunta": None,
                "explanation_why": None}

    def inferir(self, session_id: str) -> dict:
        """Ejecuta el motor. Simulado: copia los hechos derivados y la traza de 4.2."""
        memoria = self.obtener_memoria(session_id)
        if not memoria["facts"]:
            raise EstadoInvalido("La sesión no tiene hechos ingresados; registre datos antes de inferir.")
        ejemplo = cargar_ejemplo("memoria_trabajo")
        memoria["derived_facts"] = ejemplo["derived_facts"]
        memoria["execution_trace"] = ejemplo["execution_trace"]
        return memoria

    def obtener_memoria(self, session_id: str) -> dict:
        return self._sesion(session_id)["memoria"]

    def obtener_dictamen(self, session_id: str) -> dict:
        """dictamen_salida.json de la sesion. Simulado: el ejemplo de 4.2."""
        self._exigir_inferencia(session_id)
        dictamen = cargar_ejemplo("dictamen_salida")
        dictamen["session_id"] = session_id
        return dictamen

    # --- Explicacion ---

    def explicar_how(self, session_id: str, attribute_id: str) -> list[str]:
        """Como se obtuvo el valor de attribute_id. Simulado para hechos derivados."""
        memoria = self.obtener_memoria(session_id)
        if attribute_id in memoria["derived_facts"]:
            return cargar_ejemplo("dictamen_salida")["explanation_how"]
        if attribute_id in memoria["facts"]:
            return [f"'{attribute_id}' fue ingresado por el usuario: {memoria['facts'][attribute_id]!r}."]
        raise NoEncontrado(f"'{attribute_id}' no tiene valor en la memoria de trabajo.")

    def explicar_why(self, session_id: str, attribute_id: str,
                     rule_id: str | None = None) -> tuple[str, str]:
        """Por que se solicita attribute_id. Devuelve (rule_id, explicacion)."""
        return self._texto_why(self._kb_de(session_id), attribute_id, rule_id)

    def obtener_traza(self, session_id: str) -> list[str]:
        """Una linea por regla aplicada, en orden de ejecucion."""
        memoria = self.obtener_memoria(session_id)
        derivados = memoria["derived_facts"]
        return [
            f"Paso {p['step']}: {p['rule_fired']} agregó {p['added_fact']} = "
            f"{derivados.get(p['added_fact'], {}).get('value')!r}"
            for p in memoria["execution_trace"]
        ]

    def generar_reporte(self, session_id: str, formato: str) -> str:
        """Reporte del dictamen en Markdown o HTML. Simulado hasta integrar G9."""
        d = self.obtener_dictamen(session_id)
        if formato == "html":
            items = "".join(f"<li>{html.escape(l)}</li>" for l in d["explanation_how"])
            return (f"<h1>Dictamen {html.escape(session_id)}</h1>"
                    f"<p><strong>Resultado:</strong> {html.escape(str(d['final_outcome']))}</p>"
                    f"<p><strong>Certeza:</strong> {d['certainty_score']}</p>"
                    f"<h2>¿Cómo?</h2><ul>{items}</ul>"
                    f"<h2>¿Por qué?</h2><p>{html.escape(d['explanation_why'])}</p>")
        lineas = "\n".join(f"- {l}" for l in d["explanation_how"])
        return (f"# Dictamen {session_id}\n\n"
                f"**Resultado:** {d['final_outcome']}\n\n"
                f"**Certeza:** {d['certainty_score']}\n\n"
                f"## ¿Cómo?\n\n{lineas}\n\n"
                f"## ¿Por qué?\n\n{d['explanation_why']}\n")

    # --- internos ---

    def _sesion(self, session_id: str) -> dict:
        if session_id not in self._sesiones:
            raise NoEncontrado(f"No existe la sesión '{session_id}'.")
        return self._sesiones[session_id]

    def _kb_de(self, session_id: str) -> dict:
        return self.obtener_conocimiento(self._sesion(session_id)["kb_id"])

    def _exigir_inferencia(self, session_id: str) -> None:
        if not self.obtener_memoria(session_id)["derived_facts"]:
            raise EstadoInvalido("La sesión todavía no tiene conclusiones; ejecute la inferencia primero.")

    @staticmethod
    def _pregunta(atributo: dict) -> dict:
        return {
            "attribute_id": atributo["id"],
            "question": atributo.get("question"),
            "type": atributo["type"],
            "options": copy.deepcopy(atributo.get("options", [])),
            "range": atributo.get("range"),
        }

    @staticmethod
    def _texto_why(kb: dict, attribute_id: str, rule_id: str | None) -> tuple[str, str]:
        reglas = {r["id"]: r for r in kb["rules"]}
        if rule_id is None:
            candidatas = [r for r in kb["rules"]
                          if any(c["attribute_id"] == attribute_id for c in r["conditions"])]
            if not candidatas:
                raise NoEncontrado(f"Ninguna regla usa el atributo '{attribute_id}'.")
            rule_id = max(candidatas, key=lambda r: r.get("priority", 0))["id"]
        elif rule_id not in reglas:
            raise NoEncontrado(f"La regla '{rule_id}' no está en la base de conocimiento.")
        return rule_id, f"Se solicitó '{attribute_id}' para evaluar la condición de la regla {rule_id}."
