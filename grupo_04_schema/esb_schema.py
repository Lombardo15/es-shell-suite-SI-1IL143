import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

class SchemaManager:

    ESQUEMAS = {
        "conocimiento_dominio": "conocimiento_dominio.schema.json",
        "memoria_trabajo": "memoria_trabajo.schema.json",
        "dictamen_salida": "dictamen_salida.schema.json"
    }

    def __init__(self, carpeta_esquemas=None, versiones_admitidas=None):

        if carpeta_esquemas is None:
            self.carpeta_esquemas = Path(__file__).resolve().parent / "schemas"
        else:
            self.carpeta_esquemas = Path(carpeta_esquemas).resolve()

        self.versiones_admitidas = (
            set(versiones_admitidas)
            if versiones_admitidas is not None 
            else None)

    @staticmethod
    def cargar_json(ruta):

        with open(ruta, "r", encoding="utf-8-sig") as archivo:
            datos = json.load(archivo)

        return datos

    def validar_datos(self, datos, tipo):

        # Comprobar que conocemos el tipo de archivo.
        if tipo not in self.ESQUEMAS:
            raise ValueError(f"Tipo de contrato desconocido: {tipo}")

        # Buscar y cargar el esquema correspondiente.
        ruta_esquema = self.carpeta_esquemas / self.ESQUEMAS[tipo]
        esquema = self.cargar_json(ruta_esquema)

        # Verificar que el esquema esté bien definido.
        Draft202012Validator.check_schema(esquema)

        # Crear el validador.
        validador = Draft202012Validator(
            esquema,
            format_checker=FormatChecker()
        )

        errores = []

        # Revisar todos los errores encontrados.
        for error in validador.iter_errors(datos):

            ubicacion = "$"

            for parte in error.absolute_path:
                if isinstance(parte, int):
                    ubicacion += f"[{parte}]"
                else:
                    ubicacion += f".{parte}"

            errores.append(f"{ubicacion}: {error.message}")

        if not errores and tipo == "conocimiento_dominio":
            errores.extend(self.validar_conocimiento(datos))
            errores.extend(self.validar_version(datos))

        return {
            "valido": len(errores) == 0,
            "errores": sorted(errores)
        }

    @staticmethod
    def validar_conocimiento(datos):

        errores = []

        # Comprobar identificadores de atributos repetidos.
        atributos = set()

        for i, atributo in enumerate(datos["attributes"]):

            identificador = atributo["id"]

            if identificador in atributos:
                errores.append(
                    f"$.attributes[{i}].id: "
                    f"El atributo '{identificador}' está repetido."
                )

            atributos.add(identificador)

            # Comprobar que los rangos numéricos sean correctos.
            if atributo["type"] == "numeric":

                minimo, maximo = atributo["range"]

                if minimo > maximo:
                    errores.append(
                        f"$.attributes[{i}].range: "
                        "El valor mínimo no puede superar al máximo."
                    )

        # Comprobar identificadores de reglas repetidos.
        reglas = set()

        for i, regla in enumerate(datos["rules"]):

            identificador = regla["id"]

            if identificador in reglas:
                errores.append(
                    f"$.rules[{i}].id: "
                    f"La regla '{identificador}' está repetida."
                )

            reglas.add(identificador)

            # Comprobar las referencias de las condiciones.
            for j, condicion in enumerate(regla["conditions"]):

                atributo_id = condicion["attribute_id"]

                if atributo_id not in atributos:
                    errores.append(
                        f"$.rules[{i}].conditions[{j}].attribute_id: "
                        f"El atributo '{atributo_id}' no existe."
                    )

        return errores

    def validar_version(self, datos):

        errores = []

        # Obtener la versión de la base de conocimiento.
        version = datos.get("meta", {}).get("version")

        # Comprobar que exista una versión válida.
        if not isinstance(version, str) or not version.strip():
            errores.append(
                "$.meta.version: La versión debe ser un texto no vacío."
            )

            return errores

        # Comprobar si la versión está admitida.
        if self.versiones_admitidas is not None:

            if version not in self.versiones_admitidas:
                errores.append(
                    f"$.meta.version: La versión '{version}' "
                    "no está entre las versiones admitidas."
                )

        return errores
    
    def validar_memoria(self, memoria, conocimiento):

        errores = []

        # Primero comprobar las estructuras de ambos documentos.
        resultado_conocimiento = self.validar_datos(
            conocimiento, "conocimiento_dominio"
        )

        resultado_memoria = self.validar_datos(
            memoria, "memoria_trabajo"
        )

        if not resultado_conocimiento["valido"]:
            errores.extend(resultado_conocimiento["errores"])

        if not resultado_memoria["valido"]:
            errores.extend(resultado_memoria["errores"])

        # No continuar si existen errores estructurales.
        if errores:
            return {
                "valido": False,
                "errores": errores
            }

        # Crear un diccionario con los atributos declarados.
        atributos = {
            atributo["id"]: atributo
            for atributo in conocimiento["attributes"]
        }

        # Revisar cada hecho ingresado.
        for nombre, valor in memoria["facts"].items():

            ruta = f"$.facts.{nombre}"

            # Comprobar que el atributo exista.
            if nombre not in atributos:
                errores.append(
                    f"{ruta}: El atributo no está declarado "
                    "en la base de conocimiento."
                )
                continue

            atributo = atributos[nombre]
            tipo = atributo["type"]

            # Validar atributos numéricos.
            if tipo == "numeric":

                if type(valor) not in (int, float):
                    errores.append(
                        f"{ruta}: Se esperaba un número."
                    )
                    continue

                limites = atributo.get("range")

                if limites is not None:
                    minimo, maximo = limites

                    if not minimo <= valor <= maximo:
                        errores.append(
                            f"{ruta}: El valor {valor} está "
                            f"fuera del rango {limites}."
                        )

            # Validar atributos categóricos.
            elif tipo == "categorical":

                if not isinstance(valor, str):
                    errores.append(
                        f"{ruta}: Se esperaba un texto."
                    )

                elif valor not in atributo.get("options", []):
                    errores.append(
                        f"{ruta}: El valor '{valor}' no está "
                        "entre las opciones permitidas."
                    )

            # Soporte para atributos booleanos.
            elif tipo == "boolean":

                if not isinstance(valor, bool):
                    errores.append(
                        f"{ruta}: Se esperaba true o false."
                    )

            # Soporte para atributos de texto.
            elif tipo == "text":

                if not isinstance(valor, str):
                    errores.append(
                        f"{ruta}: Se esperaba un texto."
                    )

        return {
            "valido": len(errores) == 0,
            "errores": errores
        }
    
    
    def validar_traza(self, memoria, conocimiento):

        # Validar primero las estructuras y los hechos ingresados.
        resultado = self.validar_memoria(memoria, conocimiento)

        if not resultado["valido"]:
            return resultado

        errores = []

        # Obtener las reglas disponibles.
        reglas = {
            regla["id"]: regla
            for regla in conocimiento["rules"]
        }

        hechos_derivados = memoria["derived_facts"]
        traza = memoria["execution_trace"]

        # Comprobar los hechos derivados.
        for nombre, hecho in hechos_derivados.items():

            ruta = f"$.derived_facts.{nombre}"
            regla_id = hecho["derived_by_rule"]

            regla = reglas.get(regla_id)

            # Comprobar que la regla exista.
            if regla is None:
                errores.append(
                    f"{ruta}.derived_by_rule: "
                    f"La regla '{regla_id}' no existe."
                )

            else:
                conclusion = regla["conclusion"]

                # Comprobar el atributo producido.
                if conclusion["attribute_id"] != nombre:
                    errores.append(
                        f"{ruta}: La regla '{regla_id}' "
                        f"no produce el hecho '{nombre}'."
                    )

                # Comprobar el valor producido.
                if conclusion["value"] != hecho["value"]:
                    errores.append(
                        f"{ruta}.value: El valor no coincide "
                        f"con la conclusión de '{regla_id}'."
                    )

            # Comprobar que el hecho aparezca en la traza.
            registrado = any(
                paso["rule_fired"] == regla_id
                and paso["added_fact"] == nombre
                for paso in traza
            )

            if not registrado:
                errores.append(
                    f"{ruta}: Falta el registro "
                    "correspondiente en execution_trace."
                )

        # Comprobar los registros de la traza.
        for i, paso in enumerate(traza):

            regla_id = paso["rule_fired"]
            regla = reglas.get(regla_id)

            if regla is None:
                errores.append(
                    f"$.execution_trace[{i}].rule_fired: "
                    f"La regla '{regla_id}' no existe."
                )
                continue

            # Comprobar qué hecho produce la regla.
            atributo_producido = regla["conclusion"]["attribute_id"]

            if paso["added_fact"] != atributo_producido:
                errores.append(
                    f"$.execution_trace[{i}].added_fact: "
                    f"La regla '{regla_id}' no produce "
                    f"'{paso['added_fact']}'."
                )

        return {
            "valido": len(errores) == 0,
            "errores": errores
        }

    def validar_dictamen(
        self,
        dictamen,
        memoria,
        atributo_resultado=None
    ):

        errores = []

        # Validar las estructuras de ambos documentos.
        resultado_dictamen = self.validar_datos(
            dictamen, "dictamen_salida"
        )

        resultado_memoria = self.validar_datos(
            memoria, "memoria_trabajo"
        )

        if not resultado_dictamen["valido"]:
            errores.extend(resultado_dictamen["errores"])

        if not resultado_memoria["valido"]:
            errores.extend(resultado_memoria["errores"])

        # No continuar si existen errores estructurales.
        if errores:
            return {
                "valido": False,
                "errores": errores
            }

        # Comprobar que pertenezcan a la misma sesión.
        if dictamen["session_id"] != memoria["session_id"]:
            errores.append(
                "$.session_id: El dictamen y la memoria "
                "pertenecen a sesiones diferentes."
            )

        # Comprobar el resultado cuando se indique un atributo.
        if atributo_resultado is not None:

            hechos = memoria["derived_facts"]

            if atributo_resultado not in hechos:
                errores.append(
                    f"$.derived_facts.{atributo_resultado}: "
                    "No existe el hecho derivado indicado "
                    "como resultado final."
                )

            else:
                valor_derivado = hechos[atributo_resultado]["value"]
                resultado_final = dictamen["final_outcome"]

                if valor_derivado != resultado_final:
                    errores.append(
                        "$.final_outcome: El resultado final "
                        f"no coincide con el hecho derivado "
                        f"'{atributo_resultado}'."
                    )

        return {
            "valido": len(errores) == 0,
            "errores": errores
        }

    def validar_conjunto(
        self,
        conocimiento,
        memoria,
        dictamen,
        atributo_resultado=None
    ):

        # Validar la memoria, las reglas y sus trazas.
        resultado_traza = self.validar_traza(
            memoria,
            conocimiento
        )

        # Validar el dictamen y su relación con la memoria.
        resultado_dictamen = self.validar_dictamen(
            dictamen,
            memoria,
            atributo_resultado=atributo_resultado
        )

        # Reunir los errores de ambas validaciones.
        errores = (
            resultado_traza["errores"]
            + resultado_dictamen["errores"]
        )

        # Eliminar mensajes duplicados conservando el orden.
        errores = list(dict.fromkeys(errores))

        return {
            "valido": len(errores) == 0,
            "errores": errores
        }
    
    def validar_archivo(self, ruta, tipo):

        # Primero intentamos cargar el archivo JSON.
        try:
            datos = self.cargar_json(ruta)

        except FileNotFoundError:
            return {
                "valido": False,
                "errores": [f"No se encontró el archivo: {ruta}"]
            }

        except json.JSONDecodeError as error:
            return {
                "valido": False,
                "errores": [
                    f"JSON mal formado en la línea {error.lineno}, "
                    f"columna {error.colno}: {error.msg}"
                ]
            }

        except OSError as error:
            return {
                "valido": False,
                "errores": [f"No se pudo leer el archivo: {error}"]
            }

        # Si se cargó correctamente, validamos su contenido.
        try:
            return self.validar_datos(datos, tipo)

        except ValueError as error:
            return {
                "valido": False,
                "errores": [str(error)]
            }

        except FileNotFoundError:
            return {
                "valido": False,
                "errores": [
                    f"No se encontró el esquema correspondiente a '{tipo}'."
                ]
            }

        except json.JSONDecodeError as error:
            return {
                "valido": False,
                "errores": [
                    f"El esquema JSON está mal formado en la línea "
                    f"{error.lineno}, columna {error.colno}: {error.msg}"
                ]
            }

        except SchemaError as error:
            return {
                "valido": False,
                "errores": [
                    f"El esquema de validación es incorrecto: {error.message}"
                ]
            }

        except OSError as error:
            return {
                "valido": False,
                "errores": [
                    f"No se pudo cargar el esquema de validación: {error}"
                ]
            }