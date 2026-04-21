import logging

from pyaml.configuration.static_catalog import ConfigModel as StaticCatalogConfigModel
from pyaml.configuration.static_catalog import StaticCatalog
from pyaml.configuration.static_catalog_entry import (
    ConfigModel as StaticCatalogEntryConfigModel,
)
from pyaml.configuration.static_catalog_entry import StaticCatalogEntry

from tango.pyaml.controlsystem import ConfigModel, TangoControlSystem


from .mocked_device_proxy import MockedDeviceProxy
from unittest.mock import patch
from tango.pyaml.attribute import Attribute, ConfigModel as AttributeConfigModel
from tango.pyaml.attribute_read_only import AttributeReadOnly
from tango.pyaml import __version__


def test_init_cs(caplog, config_tango_cs):
    # Capture logs
    with caplog.at_level(logging.INFO):
        TangoControlSystem(config_tango_cs)

    expected_message = (
        f"PyAML Tango control system binding ({__version__}) initialized with name '{config_tango_cs.name}'"
        f" and TANGO_HOST={config_tango_cs.tango_host}"
    )

    # Check that the INFO init message was actually logged with correct values
    assert any(expected_message == record.message for record in caplog.records)


def test_laziness_init_cs_attribute(config_tango_cs_lazy_default, config):
    with patch("tango.DeviceProxy", side_effect=MockedDeviceProxy) as mock_ctor:
        attr = Attribute(config)
        mock_ctor.assert_not_called()
        attr.set_and_wait(42.0)
        mock_ctor.assert_called_once()
        attr.set_and_wait(42.0)
        mock_ctor.assert_called_once()
        assert attr.get() == 42.0


def test_catalog_can_be_configured_and_resolved():
    device = AttributeReadOnly(
        AttributeConfigModel(attribute="sys/tg_test/1/float_scalar", unit="A")
    )
    catalog = StaticCatalog(
        StaticCatalogConfigModel(
            name="device-catalog",
            entries=[
                StaticCatalogEntry(
                    StaticCatalogEntryConfigModel(
                        key="BPM_C01-01/x",
                        device=device,
                    )
                )
            ],
        )
    )
    cs = TangoControlSystem(
        ConfigModel(
            name="test_tango_cs",
            tango_host="tangodb:10000",
            catalog=catalog,
        )
    )

    cs.set_catalog(catalog)
    resolved = cs.resolve_device("BPM_C01-01/x")
    attached = cs.attach([resolved])[0]

    assert cs.get_catalog_config() is catalog
    assert cs.get_catalog() is catalog
    assert resolved is device
    assert attached.name() == "//tangodb:10000/sys/tg_test/1/float_scalar"


def test_named_catalog_config_is_accepted():
    cfg = ConfigModel(name="test_tango_cs", catalog="device-catalog")

    assert cfg.catalog == "device-catalog"
