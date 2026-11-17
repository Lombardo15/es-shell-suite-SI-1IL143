"""Validación de contratos JSON y consistencia de sesiones de ES-Shell Suite.

La clase no ejecuta reglas ni decide qué preguntas debe hacer el sistema.
Los esquemas compartidos se mantienen en archivos JSON independientes.
"""

import json
import math
from pathlib import Path
from threading import RLock

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


class SchemaManager:
    """Carga y valida conocimiento, memoria de trabajo y dictámenes."""

    ESQUEMAS = {
        "conocimiento_dominio": "conocimiento_dominio.schema.json",
        "memoria_trabajo": "memoria_trabajo.schema.json",
        "dictamen_salida": "dictamen_salida.schema.json",
    }
    OPERADORES_ORDEN = frozenset({">", "<", ">=", "<="})

    def __init__(self, carpeta_esquemas=None, versiones_admitidas=None):
        carpeta = (
            Path(carpeta_esquemas)
            if carpeta_esquemas is not None
            else Path(__file__).resolve().parent / "schemas"
        )
        self.carpeta_esquemas = carpeta.resolve()
        # Máximo tres esquemas en memoria. Se regeneran si cambia el archivo.
        self._cache_validadores = {}
        self._cache_lock = RLock()

        if isinstance(versiones_admitidas, str):
            self.versiones_admitidas = {versiones_admitidas}
        elif versiones_admitidas is None:
            self.versiones_admitidas = None
        else:
            self.versiones_admitidas = set(versiones_admitidas)

    @staticmethod
    def cargar_json(ruta):
        """Carga un JSON en UTF-8 (también acepta BOM)."""
        def rechazar_constante(valor):
            # json.load() admite NaN e Infinity por defecto, pero no son JSON estándar.
            raise ValueError(f"Constante numérica no válida en JSON: {valor}")

        with open(ruta, "r", encoding="utf-8-sig") as archivo:
            return json.load(archivo, parse_constant=rechazar_constante)

    @staticmethod
    def _resultado(errores):
        """Estructura pública común de resultados de validación."""
        errores = list(dict.fromkeys(errores))
        return {"valido": not errores, "errores": errores}

    @staticmethod
    def _ruta_error(error):
        """Representa la ubicación de un error de JSON Schema."""
        ruta = "$"
        for segmento in error.absolute_path:
            if isinstance(segmento, int):
                ruta += f"[{segmento}]"
            else:
                ruta += f".{segmento}"
        return ruta

    def _obtener_validador(self, tipo):
        """Reutiliza el esquema compilado y lo recarga si cambia en disco.

        La firma (mtime_ns, tamaño) evita reabrir el JSON y ejecutar
        check_schema() en cada validación. El bloqueo protege la caché
        cuando distintos módulos llaman al gestor desde varios hilos.
        """
        ruta = self.carpeta_esquemas / self.ESQUEMAS[tipo]

        with self._cache_lock:
            estado = ruta.stat()  # FileNotFoundError se propaga al llamador.
            firma = (estado.st_mtime_ns, estado.st_size)
            entrada = self._cache_validadores.get(tipo)
            if entrada is not None and entrada[0] == (ruta, firma):
                return entrada[1]

            esquema = self.cargar_json(ruta)
            Draft202012Validator.check_schema(esquema)
            validador = Draft202012Validator(
                esquema, format_checker=FormatChecker()
            )
            self._cache_validadores[tipo] = ((ruta, firma), validador)
            return validador

    def limpiar_cache_esquemas(self):
        """Invalida la caché cuando se necesita recargar manualmente."""
        with self._cache_lock:
            self._cache_validadores.clear()

    def validar_datos(self, datos, tipo):
        """Valida un documento mediante su esquema y reglas semánticas.

        Devuelve {'valido': bool, 'errores': list[str]}.
        Los validadores se guardan en caché y se renuevan al cambiar
        el archivo del esquema (fecha de modificación o tamaño).
        Los errores de configuración del esquema se propagan al llamador;
        validar_archivo() los convierte a mensajes para el usuario.
        """
        if tipo not in self.ESQUEMAS:
            raise ValueError(f"Tipo de contrato desconocido: {tipo}")

        validador = self._obtener_validador(tipo)

        errores = sorted(
            f"{self._ruta_error(error)}: {error.message}"
            for error in validador.iter_errors(datos)
        )

        # Evita acceder a campos que podrían faltar o tener tipos incorrectos.
        if not errores and tipo == "conocimiento_dominio":
            errores.extend(self.validar_conocimiento(datos))
            errores.extend(self.validar_condiciones(datos))
            errores.extend(self.validar_dependencias_circulares(datos))
            errores.extend(self.validar_version(datos))

        return self._resultado(sorted(errores))

    @staticmethod
    def validar_conocimiento(datos):
        """Comprueba identificadores, referencias y rangos numéricos."""
        errores = []
        atributos = set()

        for i, atributo in enumerate(datos["attributes"]):
            identificador = atributo["id"]
            if identificador in atributos:
                errores.append(
                    f"$.attributes[{i}].id: El atributo '{identificador}' está repetido."
                )
            atributos.add(identificador)

            if atributo["type"] == "numeric":
                rango = atributo.get("range")
                if rango is not None:
                    minimo, maximo = rango
                    if minimo >= maximo:
                        errores.append(
                            f"$.attributes[{i}].range: "
                            "El valor mínimo debe ser menor que el máximo."
                        )

        reglas = set()
        for i, regla in enumerate(datos["rules"]):
            identificador = regla["id"]
            if identificador in reglas:
                errores.append(
                    f"$.rules[{i}].id: La regla '{identificador}' está repetida."
                )
            reglas.add(identificador)

            for j, condicion in enumerate(regla["conditions"]):
                atributo_id = condicion["attribute_id"]
                if atributo_id not in atributos:
                    errores.append(
                        f"$.rules[{i}].conditions[{j}].attribute_id: "
                        f"El atributo '{atributo_id}' no existe."
                    )
        return errores

    @staticmethod
    def _comprobar_valor(atributo, valor, ruta, comprobar_rango=False):
        """Comprueba un valor sin ejecutar reglas de inferencia."""
        tipo = atributo["type"]
        if tipo == "numeric":
            if type(valor) not in (int, float):
                return [f"{ruta}: Se esperaba un número."]
            if isinstance(valor, float) and not math.isfinite(valor):
                return [f"{ruta}: Se esperaba un número finito."]
            if comprobar_rango:
                limites = atributo.get("range")
                if limites is not None and not limites[0] <= valor <= limites[1]:
                    return [
                        f"{ruta}: El valor {valor} está fuera del rango {limites}."
                    ]
        elif tipo == "categorical":
            if not isinstance(valor, str):
                return [f"{ruta}: Se esperaba un texto."]
            if valor not in atributo["options"]:
                return [
                    f"{ruta}: El valor '{valor}' no está entre las opciones permitidas."
                ]
        elif tipo == "boolean" and not isinstance(valor, bool):
            return [f"{ruta}: Se esperaba true o false."]
        elif tipo == "text" and not isinstance(valor, str):
            return [f"{ruta}: Se esperaba un texto."]
        return []

    def validar_condiciones(self, conocimiento):
        """Comprueba tipos y referencias en reglas y preguntas condicionales."""
        errores = []
        atributos = {a["id"]: a for a in conocimiento["attributes"]}

        def comprobar_condicion(condicion, ruta):
            atributo_id = condicion["attribute_id"]
            if atributo_id not in atributos:
                errores.append(
                    f"{ruta}.attribute_id: El atributo '{atributo_id}' no existe."
                )
                return

            atributo = atributos[atributo_id]
            operador = condicion["operator"]
            if operador in self.OPERADORES_ORDEN and atributo["type"] != "numeric":
                errores.append(
                    f"{ruta}.operator: El operador '{operador}' "
                    "requiere un atributo numérico."
                )

            valor = condicion["value"]
            valores = valor if operador == "in" else [valor]
            for indice, elemento in enumerate(valores):
                ruta_valor = (
                    f"{ruta}.value[{indice}]" if operador == "in" else f"{ruta}.value"
                )
                errores.extend(self._comprobar_valor(atributo, elemento, ruta_valor))

        for i, regla in enumerate(conocimiento["rules"]):
            for j, condicion in enumerate(regla["conditions"]):
                comprobar_condicion(condicion, f"$.rules[{i}].conditions[{j}]")

        for i, atributo in enumerate(conocimiento["attributes"]):
            dependencia = atributo.get("depends_on")
            if dependencia is None:
                continue
            ruta = f"$.attributes[{i}].depends_on"
            if dependencia["attribute_id"] == atributo["id"]:
                errores.append(f"{ruta}: Un atributo no puede depender de sí mismo.")
            comprobar_condicion(dependencia, ruta)
        return errores

    @staticmethod
    def validar_dependencias_circulares(conocimiento):
        """Detecta ciclos en depends_on, incluso de tres o más atributos."""
        errores = []
        ids = {atributo["id"] for atributo in conocimiento["attributes"]}
        dependencias = {}

        for atributo in conocimiento["attributes"]:
            dependencia = atributo.get("depends_on")
            if dependencia is None:
                continue
            origen, destino = atributo["id"], dependencia["attribute_id"]
            if destino in ids and origen != destino:
                dependencias[origen] = destino

        revisados = set()
        for inicio in dependencias:
            if inicio in revisados:
                continue
            camino, posiciones = [], {}
            actual = inicio
            while actual in dependencias and actual not in revisados:
                if actual in posiciones:
                    ciclo = camino[posiciones[actual]:] + [actual]
                    errores.append(
                        "$.attributes: Dependencia circular detectada: "
                        + " -> ".join(ciclo) + "."
                    )
                    break
                posiciones[actual] = len(camino)
                camino.append(actual)
                actual = dependencias[actual]
            revisados.update(camino)
        return errores

    def validar_version(self, datos):
        """Comprueba meta.version y, opcionalmente, versiones admitidas."""
        version = datos.get("meta", {}).get("version")
        if not isinstance(version, str) or not version.strip():
            return ["$.meta.version: La versión debe ser un texto no vacío."]
        if (self.versiones_admitidas is not None
                and version not in self.versiones_admitidas):
            return [
                f"$.meta.version: La versión '{version}' "
                "no está entre las versiones admitidas."
            ]
        return []

    def _validar_hechos(self, memoria, conocimiento):
        """Valida hechos de una memoria ya verificada estructuralmente."""
        errores = []
        atributos = {a["id"]: a for a in conocimiento["attributes"]}
        for nombre, valor in memoria["facts"].items():
            ruta = f"$.facts.{nombre}"
            atributo = atributos.get(nombre)
            if atributo is None:
                errores.append(
                    f"{ruta}: El atributo no está declarado en la base de conocimiento."
                )
            else:
                errores.extend(
                    self._comprobar_valor(
                        atributo, valor, ruta, comprobar_rango=True
                    )
                )
        return errores

    def validar_memoria(self, memoria, conocimiento):
        """Valida hechos existentes; no exige una sesión completa."""
        errores = (
            self.validar_datos(conocimiento, "conocimiento_dominio")["errores"]
            + self.validar_datos(memoria, "memoria_trabajo")["errores"]
        )
        if errores:
            return self._resultado(errores)
        return self._resultado(self._validar_hechos(memoria, conocimiento))

    @staticmethod
    def validar_completitud(memoria, atributos_requeridos):
        """Comprueba presencia de claves en facts; no valida sus valores.

        El módulo que gestiona la consulta decide qué atributos son requeridos.
        """
        hechos = memoria["facts"]
        faltantes = list(dict.fromkeys(
            atributo for atributo in atributos_requeridos if atributo not in hechos
        ))
        return {"completa": not faltantes, "faltantes": faltantes}

    @staticmethod
    def _validar_relaciones_traza(memoria, conocimiento):
        """Valida trazas y hechos derivados de documentos estructuralmente válidos."""
        errores = []
        reglas = {r["id"]: r for r in conocimiento["rules"]}
        derivados = memoria["derived_facts"]
        traza = memoria["execution_trace"]
        disparos = {(paso["rule_fired"], paso["added_fact"]) for paso in traza}

        for nombre, hecho in derivados.items():
            ruta = f"$.derived_facts.{nombre}"
            regla_id = hecho["derived_by_rule"]
            regla = reglas.get(regla_id)
            if regla is None:
                errores.append(
                    f"{ruta}.derived_by_rule: La regla '{regla_id}' no existe."
                )
            else:
                conclusion = regla["conclusion"]
                if conclusion["attribute_id"] != nombre:
                    errores.append(
                        f"{ruta}: La regla '{regla_id}' no produce el hecho '{nombre}'."
                    )
                if conclusion["value"] != hecho["value"]:
                    errores.append(
                        f"{ruta}.value: El valor no coincide con la conclusión de '{regla_id}'."
                    )

            if (regla_id, nombre) not in disparos:
                errores.append(
                    f"{ruta}: Falta el registro correspondiente en execution_trace."
                )

        for i, paso in enumerate(traza):
            regla_id = paso["rule_fired"]
            regla = reglas.get(regla_id)
            if regla is None:
                errores.append(
                    f"$.execution_trace[{i}].rule_fired: La regla '{regla_id}' no existe."
                )
                continue
            if paso["added_fact"] != regla["conclusion"]["attribute_id"]:
                errores.append(
                    f"$.execution_trace[{i}].added_fact: La regla '{regla_id}' "
                    f"no produce '{paso['added_fact']}'."
                )
        return errores

    def validar_traza(self, memoria, conocimiento):
        """Valida una memoria y sus relaciones con las reglas disparadas."""
        previo = self.validar_memoria(memoria, conocimiento)
        if not previo["valido"]:
            return previo
        return self._resultado(self._validar_relaciones_traza(memoria, conocimiento))

    @staticmethod
    def _validar_relacion_dictamen(dictamen, memoria, atributo_resultado):
        """Compara sesiones y opcionalmente el hecho final seleccionado."""
        errores = []
        if dictamen["session_id"] != memoria["session_id"]:
            errores.append(
                "$.session_id: El dictamen y la memoria pertenecen a sesiones diferentes."
            )
        if atributo_resultado is not None:
            hecho = memoria["derived_facts"].get(atributo_resultado)
            if hecho is None:
                errores.append(
                    f"$.derived_facts.{atributo_resultado}: No existe el hecho "
                    "derivado indicado como resultado final."
                )
            elif hecho["value"] != dictamen["final_outcome"]:
                errores.append(
                    "$.final_outcome: El resultado final no coincide con el "
                    f"hecho derivado '{atributo_resultado}'."
                )
        return errores

    def validar_dictamen(self, dictamen, memoria, atributo_resultado=None):
        """Valida un dictamen y su relación con la memoria de una sesión."""
        errores = (
            self.validar_datos(dictamen, "dictamen_salida")["errores"]
            + self.validar_datos(memoria, "memoria_trabajo")["errores"]
        )
        if errores:
            return self._resultado(errores)
        return self._resultado(
            self._validar_relacion_dictamen(dictamen, memoria, atributo_resultado)
        )

    def validar_conjunto(self, conocimiento, memoria, dictamen, atributo_resultado=None):
        """Valida los tres documentos evitando validar el esquema repetidamente."""
        errores = (
            self.validar_datos(conocimiento, "conocimiento_dominio")["errores"]
            + self.validar_datos(memoria, "memoria_trabajo")["errores"]
            + self.validar_datos(dictamen, "dictamen_salida")["errores"]
        )
        if errores:
            return self._resultado(errores)

        errores_hechos = self._validar_hechos(memoria, conocimiento)
        errores.extend(errores_hechos)
        if not errores_hechos:
            errores.extend(self._validar_relaciones_traza(memoria, conocimiento))
        errores.extend(
            self._validar_relacion_dictamen(dictamen, memoria, atributo_resultado)
        )
        return self._resultado(errores)

    def validar_archivo(self, ruta, tipo):
        """Valida un archivo y convierte errores de lectura/esquema a mensajes."""
        try:
            datos = self.cargar_json(ruta)
        except FileNotFoundError:
            return self._resultado([f"No se encontró el archivo: {ruta}"])
        except json.JSONDecodeError as error:
            return self._resultado([
                f"JSON mal formado en la línea {error.lineno}, "
                f"columna {error.colno}: {error.msg}"
            ])
        except ValueError as error:
            return self._resultado([f"JSON inválido: {error}"])
        except OSError as error:
            return self._resultado([f"No se pudo leer el archivo: {error}"])

        try:
            return self.validar_datos(datos, tipo)
        except ValueError as error:
            return self._resultado([str(error)])
        except FileNotFoundError:
            return self._resultado([
                f"No se encontró el esquema correspondiente a '{tipo}'."
            ])
        except json.JSONDecodeError as error:
            return self._resultado([
                f"El esquema JSON está mal formado en la línea "
                f"{error.lineno}, columna {error.colno}: {error.msg}"
            ])
        except SchemaError as error:
            return self._resultado([
                f"El esquema de validación es incorrecto: {error.message}"
            ])
        except OSError as error:
            return self._resultado([
                f"No se pudo cargar el esquema de validación: {error}"
            ])
