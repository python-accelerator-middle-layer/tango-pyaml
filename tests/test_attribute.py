import pyaml.control.readback_value
import yaml
import pytest
import tango

from tango.pyaml.attribute_read_only import AttributeReadOnly
from .mocked_device_proxy import *
from .mocked_group import MockedGroup
from unittest.mock import MagicMock, patch
from tango.pyaml.attribute import Attribute
from tango.pyaml.attribute_list import AttributeList, ConfigModel as GrpCM
from tango.pyaml.tango_attribute import ConfigModel as AttrCM

# YAML simulé pour configurer l'attribut
YAML_CONFIG = """
attribute: "sys/tg_test/1/float_scalar"
unit: "A"
"""

YAML_CONFIG_GRP = """
attributes:
    - "sys/tg_test/1/float_scalar"
    - "sys/tg_test/2/float_scalar"
    - "sys/tg_test/3/float_scalar"
    - "sys/tg_test/4/float_scalar"
unit: "A"
"""


@pytest.fixture
def config():
    cfg_dict = yaml.safe_load(YAML_CONFIG)
    return AttrCM(**cfg_dict)

@pytest.fixture
def config_group():
    cfg_dict = yaml.safe_load(YAML_CONFIG_GRP)
    return GrpCM(**cfg_dict)


class MockedReadExceptDeviceProxy(MockedDeviceProxy):
    def read_attribute(self, name):
        raise tango.Except.throw_exception("mocked reason", f"mocked desc for attr {name}", "mocked origin")

class MockedROAttrDeviceProxy(MockedDeviceProxy):
    def attribute_query(self, name):
        attr_ro_info = MockedAttributeInfoEx(name, tango._tango.AttrWriteType.READ)
        return attr_ro_info


def test_attribute_get_set(config):
    with patch("tango.DeviceProxy", new=MockedDeviceProxy):
        attr = Attribute(config)
        attr.set(42.0)
        assert attr.get() == 42.0
        assert attr.readback() == 42.0
        assert attr.readback().timestamp is not None
        assert attr.readback().quality is pyaml.control.readback_value.Quality.VALID

        # Test infos
        assert attr.unit() == "A"
        assert attr.name() == "sys/tg_test/1/float_scalar"
        assert attr.measure_name() == "float_scalar"


def test_attribute_except(config):
    with patch("tango.DeviceProxy", new=MockedReadExceptDeviceProxy):
        attr = Attribute(config)
        try:
            attr.readback()
            assert False
        except pyaml.PyAMLException as ex:
            assert type(ex)==pyaml.PyAMLException
        except:
            assert False


def test_attribute_read_only(config):
    with patch("tango.DeviceProxy", new=MockedROAttrDeviceProxy):
        # Cannot create an attribute with a read-only tango attribute.
        try:
            Attribute(config)
            assert False
        except pyaml.PyAMLException as ex:
            assert type(ex)==pyaml.PyAMLException
        except:
            assert False

        # Read-only attributes cannot be sets.
        try:
            attr = AttributeReadOnly(config)
            try:
                attr.set(10)
                assert False
            except pyaml.PyAMLException as ex:
                assert type(ex) == pyaml.PyAMLException
            except:
                assert False
            try:
                attr.get()
                assert False
            except pyaml.PyAMLException as ex:
                assert type(ex) == pyaml.PyAMLException
            except:
                assert False
        except:
            assert False

def test_group_read_write(config_group):
    with patch("tango.Group", new=MockedGroup):
        try:
            attr_list = AttributeList(config_group)
            attr_list.set(10)
            vals = attr_list.readback()
            for val in vals:
                assert val.value == 10
        except:
            assert False
