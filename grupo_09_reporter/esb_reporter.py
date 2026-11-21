"""esb_reporter.py, Grupo 9: generador de reportes y dictámenes (stub)."""


class ReportGenerator:
    """Genera el informe final de una consulta del sistema experto."""

    def __init__(self, ruta_conocimiento=None, ruta_memoria=None, ruta_dictamen=None):
        self.ruta_conocimiento = ruta_conocimiento  # conocimiento_dominio.json
        self.ruta_memoria = ruta_memoria            # memoria_trabajo.json
        self.ruta_dictamen = ruta_dictamen          # dictamen_salida.json

    def cargar_json(self, ruta):
        """Lee un archivo JSON y devuelve su contenido."""
        raise NotImplementedError

    def generar_markdown(self):
        """Devuelve el informe completo como texto en Markdown."""
        raise NotImplementedError

    def guardar_reporte(self, ruta_salida):
        """Guarda el informe en un archivo."""
        raise NotImplementedError
