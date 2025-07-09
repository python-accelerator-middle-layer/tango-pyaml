from pydantic import BaseModel

PYAMLCLASS : str = "AttributeList"

class ConfigModel(BaseModel):
    """Name of tango attribute (i.e. my/ps/device/current) and optionally, the units"""
    attribute: str
    unit: str = ""

class AttributeList:
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)
