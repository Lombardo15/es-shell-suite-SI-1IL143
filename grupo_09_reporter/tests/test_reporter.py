from grupo_09_reporter.esb_reporter import ReportGenerator


def test_se_puede_crear_el_generador():
    gen = ReportGenerator()
    assert gen is not None
