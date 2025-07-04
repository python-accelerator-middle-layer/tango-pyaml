import pyaml.control.readback_value
import yaml
import pytest
import tango
from unittest.mock import MagicMock, patch
from tango.pyaml.attribute import Attribute, ConfigModel

# YAML simulé pour configurer l'attribut
YAML_CONFIG = """
attribute: "sys/tg_test/1/float_scalar"
unit: "A"
"""

@pytest.fixture
def config():
    cfg_dict = yaml.safe_load(YAML_CONFIG)
    return ConfigModel(**cfg_dict)

@pytest.fixture
def mock_device():
    # Crée un mock d'attribut avec une valeur mutable
    mock = MagicMock()
    state = {"value": 43.0, "w_value": 42.0, "quality": tango.AttrQuality.ATTR_VALID, "time": tango.TimeVal.now()}

    # Simule read_attribute() → retourne un objet avec .value = state["value"]
    def read_attribute(name):
        result = MagicMock()
        result.value = state["value"]
        result.w_value = state["w_value"]
        result.quality = state["quality"]
        result.time = state["time"]
        return result

    # Simule write_attribute() → met à jour state["value"]
    def write_attribute(name, val):
        state["value"] = val
        state["w_value"] = val
        state["time"] = tango.TimeVal.now()

    mock.read_attribute.side_effect = read_attribute
    mock.write_attribute.side_effect = write_attribute

    return mock

def test_attribute_get_set(config, mock_device):
    with patch("tango.DeviceProxy", return_value=mock_device):
        attr = Attribute(config)

        # Test lecture
        assert attr.get() == 42.0
        assert attr.readback() == 43.0

        # Test écriture
        attr.set(123.4)
        assert attr.get() == 123.4
        assert attr.readback() == 123.4
        assert attr.readback().timestamp is not None
        assert attr.readback().quality is pyaml.control.readback_value.Quality.VALID

        # Test infos
        assert attr.unit() == "A"
        assert attr.name() == "sys/tg_test/1/float_scalar"
        assert attr.measure_name() == "float_scalar"
