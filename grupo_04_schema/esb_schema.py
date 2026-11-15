import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


class SchemaManager:

    ESQUEMAS = {
        "conocimiento_dominio": "conocimiento_dominio.schema.json",
        "memoria_trabajo": "memoria_trabajo.schema.json",
        "dictamen_salida": "dictamen_salida.schema.json"
    }

    def __init__(self, carpeta_esquemas=None):

        if carpeta_esquemas is None:
            self.carpeta_esquemas = Path(__file__).resolve().parent / "schemas"
        else:
            self.carpeta_esquemas = Path(carpeta_esquemas).resolve()

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

    def validar_archivo(self, ruta, tipo):

        try:
            datos = self.cargar_json(ruta)

            return self.validar_datos(datos, tipo)

        except (OSError, json.JSONDecodeError) as error:

            return {
                "valido": False,
                "errores": [str(error)]
            }