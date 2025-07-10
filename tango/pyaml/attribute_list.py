from numpy import array
from pydantic import BaseModel
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value, Quality
import tango

PYAMLCLASS : str = "AttributeList"

class ConfigModel(BaseModel):
    """Name of tango attribute (i.e. my/ps/device/current) and optionally, the units"""
    attributes: list[str]
    name: str = ""
    unit: str = ""

class AttributeList(DeviceAccess):

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        self._tango_groups = {}
        attr_dev = {}
        for attribute in self._cfg.attributes:
            attribute_dev_name, attr_name = attribute.rsplit("/", 1)
            if attr_name not in attr_dev.keys():
                attr_dev[attr_name] = []
            if attribute_dev_name not in attr_dev[attr_name]:
                attr_dev[attr_name].append(attribute_dev_name)

        for attr_name, dev_list in attr_dev.items():
            self._tango_groups[attr_name] = tango.Group(self._cfg.name)
            [self._tango_groups[attr_name].add(dev) for dev in dev_list]

    def name(self) -> str:
        return self._cfg.name

    def measure_name(self) -> str:
        return self._cfg.name

    def set(self, value: float):
        [group.write_attribute_asynch(attr_name, value) for attr_name, group in self._tango_groups.items()]

    def set_and_wait(self, value: float):
        [group.write_attribute(attr_name, value) for attr_name, group in self._tango_groups.items()]

    def get(self) -> array:
        """

        :return: The last written value as an array in the same order than the configuration
        """
        result = {}
        grp_vals = [group.read_attribute(attr_name) for attr_name, group in self._tango_groups.items()]
        for vals in grp_vals:
            for val in vals:
                attr_value = val.data
                if attr_value is not None:
                    result[val.dev_name + '/' + val.obj_name] = attr_value.w_value
                else:
                    result[val.dev_name + '/'+ val.obj_name] = None
        return array([result[attribute] for attribute in self._cfg.attributes])

    def readback(self) -> array:
        result = {}
        grp_vals = [group.read_attribute(attr_name) for attr_name, group in self._tango_groups.items()]
        for vals in grp_vals:
            for val in vals:
                attr_value = val.data
                if attr_value is not None:
                    quality = Quality[attr_value.quality.name.rsplit('_', 1)[1]] # AttrQuality.ATTR_VALID gives Quality.VALID
                    value = Value(attr_value.value, quality, attr_value.time.todatetime() )
                    result[val.dev_name + '/' + val.obj_name] = value
                else:
                    result[val.dev_name + '/' + val.obj_name] = None
        return array([result[attribute] for attribute in self._cfg.attributes])

    def unit(self) -> str:
        return self._cfg.unit

