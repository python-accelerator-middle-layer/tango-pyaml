import pytest
import yaml
from tango.pyaml.attribute_list import AttributeList, ConfigModel as GrpCM
from tango.pyaml.tango_attribute import ConfigModel as AttrCM


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
