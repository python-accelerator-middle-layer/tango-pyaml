import pytest
import yaml

from tango.pyaml.attribute_list import AttributeList, ConfigModel as GrpCM
from tango.pyaml.attribute import ConfigModel as AttrCM
from tango.pyaml.multi_attribute import ConfigModel as MultiAttrCM
from tango.pyaml.controlsystem import ConfigModel as CsCM, TangoControlSystem
from tango.pyaml.device_factory import DeviceFactory


@pytest.fixture(autouse=True)
def clear_device_factory_cache():
    DeviceFactory()._elements.clear()
    TangoControlSystem._instance = None


@pytest.fixture
def config():
    conf = """
attribute: "sys/tg_test/1/float_scalar"
unit: "A"
"""
    cfg_dict = yaml.safe_load(conf)
    return AttrCM(**cfg_dict)

@pytest.fixture
def config_group():
    conf = """
attributes:
    - "sys/tg_test/1/float_scalar"
    - "sys/tg_test/2/float_scalar"
    - "sys/tg_test/3/float_scalar"
    - "sys/tg_test/4/float_scalar"
unit: "A"
"""
    cfg_dict = yaml.safe_load(conf)
    return GrpCM(**cfg_dict)

@pytest.fixture
def config_multi():
    conf = """
attributes:
    - "sys/tg_test/1/float_scalar"
    - "sys/tg_test/2/float_scalar"
    - "sys/tg_test/3/float_scalar"
    - "sys/tg_test/4/float_scalar"
unit: "A"
"""
    cfg_dict = yaml.safe_load(conf)
    return MultiAttrCM(**cfg_dict)

@pytest.fixture
def config_tango_cs():
    conf = """
name: test_tango_cs
tango_host: tangodb:10000
debug_level: INFO
lazy_devices: false
"""
    cfg_dict = yaml.safe_load(conf)
    return CsCM(**cfg_dict)

@pytest.fixture
def config_tango_cs_lazy_default():
    conf = """
name: test_tango_cs
tango_host: tangodb:10000
debug_level: INFO
"""
    cfg_dict = yaml.safe_load(conf)
    return CsCM(**cfg_dict)

@pytest.fixture
def config_tango_cs_false():
    conf = """
name: test_tango_cs_false
tango_host: this_is_an_error
debug_level: nope
"""
    cfg_dict = yaml.safe_load(conf)
    return CsCM(**cfg_dict)
