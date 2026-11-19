"""Tests del aviso de entorno (issue #3).

La funcion es pura: recibe version de Python y de Tk y devuelve un mensaje
o None, sin abrir ventanas ni tocar el sistema.
"""

from src.infrastructure.environment import get_environment_warning


class TestGetEnvironmentWarning:
    def test_python_312_con_tk_86_no_avisa(self):
        assert get_environment_warning((3, 12, 0), 8.6) is None

    def test_python_313_con_tk_86_no_avisa(self):
        assert get_environment_warning((3, 13, 0), 8.6) is None

    def test_python_314_con_tk_90_avisa_ambos(self):
        aviso = get_environment_warning((3, 14, 0), 9.0)
        assert aviso is not None
        assert "Entorno no recomendado:" in aviso
        assert "3.14" in aviso
        assert "9.0" in aviso

    def test_python_311_avisa_python(self):
        aviso = get_environment_warning((3, 11, 0), 8.6)
        assert aviso is not None
        assert "3.11" in aviso

    def test_python_312_con_tk_90_avisa_tk(self):
        aviso = get_environment_warning((3, 12, 0), 9.0)
        assert aviso is not None
        assert "9.0" in aviso
