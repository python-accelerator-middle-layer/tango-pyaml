import logging
from unittest.mock import patch

import pyaml
import pytest

from tango.pyaml import __version__
from tango.pyaml.attribute import Attribute, AttributeConfig
from tango.pyaml.attribute_list import AttributeList, AttributeListConfig
from tango.pyaml.attribute_list_read_only import (
    AttributeListReadOnly,
    AttributeListReadOnlyConfig,
)
from tango.pyaml.attribute_read_only import AttributeReadOnly, AttributeReadOnlyConfig
from tango.pyaml.controlsystem import TangoControlSystem
from tango.pyaml.static_catalog import StaticCatalog
from tango.pyaml.static_catalog_entry import StaticCatalogEntry

from .mocked_device_proxy import MockedDeviceProxy


def test_init_cs(caplog, config_tango_cs):
    # Capture logs
    with caplog.at_level(logging.INFO):
        TangoControlSystem(**config_tango_cs)

    expected_message = (
        f"PyAML Tango control system binding ({__version__}) initialized with name '{config_tango_cs['name']}'"
        f" and TANGO_HOST={config_tango_cs['tango_host']}"
    )

    # Check that the INFO init message was actually logged with correct values
    assert any(expected_message == record.message for record in caplog.records)


def test_laziness_init_cs_attribute(config_tango_cs_lazy_default, config):
    with patch("tango.DeviceProxy", side_effect=MockedDeviceProxy) as mock_ctor:
        attr = Attribute(**config.model_dump())
        mock_ctor.assert_not_called()
        attr.set_and_wait(42.0)
        mock_ctor.assert_called_once()
        attr.set_and_wait(42.0)
        mock_ctor.assert_called_once()
        assert attr.get() == 42.0


def test_catalog_can_be_configured_and_resolved():
    device = AttributeReadOnly(attribute="sys/tg_test/1/float_scalar", unit="A")
    catalog = StaticCatalog(
        entries=[
            StaticCatalogEntry(
                key="BPM_C01-01/x",
                device=device,
            )
        ],
    )
    cs = TangoControlSystem(
        name="test_tango_cs",
        tango_host="tangodb:10000",
        catalog=catalog,
    )

    resolved = cs.get_device_access("BPM_C01-01/x")

    assert cs.get_catalog() is catalog
    assert catalog.resolve("BPM_C01-01/x") is device
    assert resolved.name() == "//tangodb:10000/sys/tg_test/1/float_scalar"


def test_get_device_builds_attribute_from_config_model():
    cs = TangoControlSystem(name="test_tango_cs", tango_host="tangodb:10000")

    resolved = cs.get_device_access(
        AttributeConfig(attribute="sys/tg_test/1/float_scalar", unit="A")
    )

    assert isinstance(resolved, Attribute)
    assert resolved.name() == "//tangodb:10000/sys/tg_test/1/float_scalar"
    assert resolved.unit() == "A"


def test_get_device_builds_read_only_attribute_from_config_model():
    cs = TangoControlSystem(name="test_tango_cs", tango_host="tangodb:10000")

    resolved = cs.get_device_access(
        AttributeReadOnlyConfig(attribute="sys/tg_test/1/float_scalar", unit="A")
    )

    assert isinstance(resolved, AttributeReadOnly)
    assert resolved.name() == "//tangodb:10000/sys/tg_test/1/float_scalar"
    assert resolved.unit() == "A"


def test_get_device_builds_attribute_list_from_config_model():
    cs = TangoControlSystem(name="test_tango_cs", tango_host="tangodb:10000")
    resolved = cs.get_device_access(
        AttributeListConfig(
            name="group",
            attributes=[
                "sys/tg_test/1/float_scalar",
                "sys/tg_test/2/float_scalar",
            ],
            unit="A",
        )
    )

    assert isinstance(resolved, AttributeList)
    assert not isinstance(resolved, AttributeListReadOnly)
    assert resolved.name() == "group"
    assert resolved.unit() == "A"
    assert resolved.get_tango_attributes() == [
        "//tangodb:10000/sys/tg_test/1/float_scalar",
        "//tangodb:10000/sys/tg_test/2/float_scalar",
    ]


def test_get_device_builds_read_only_attribute_list_from_config_model():
    cs = TangoControlSystem(name="test_tango_cs", tango_host="tangodb:10000")

    resolved = cs.get_device_access(
        AttributeListReadOnlyConfig(
            name="group",
            attributes=[
                "sys/tg_test/1/float_scalar",
                "sys/tg_test/2/float_scalar",
            ],
            unit="A",
        )
    )

    assert isinstance(resolved, AttributeListReadOnly)
    assert resolved.name() == "group"
    assert resolved.unit() == "A"
    assert resolved.get_tango_attributes() == [
        "//tangodb:10000/sys/tg_test/1/float_scalar",
        "//tangodb:10000/sys/tg_test/2/float_scalar",
    ]


def test_get_device_none_returns_none():
    cs = TangoControlSystem(name="test_tango_cs")

    assert cs.get_device_access(None) is None


def test_get_device_rejects_preconstructed_device_access(config):
    cs = TangoControlSystem(name="test_tango_cs")

    with pytest.raises(pyaml.PyAMLException, match="Use attach\\(\\)"):
        cs.get_device_access(Attribute(**config.model_dump()))


def test_get_device_requires_catalog_for_string_key():
    cs = TangoControlSystem(name="test_tango_cs")

    with pytest.raises(pyaml.PyAMLException, match="has no catalog configured"):
        cs.get_device_access("BPM_C01-01/x")


def test_get_device_reports_unknown_catalog_key():
    device = Attribute(attribute="sys/tg_test/1/float_scalar")
    catalog = StaticCatalog(
        entries=[StaticCatalogEntry(key="BPM_C01-01/x", device=device)],
    )
    cs = TangoControlSystem(name="test_tango_cs", catalog=catalog)

    with pytest.raises(pyaml.PyAMLException, match="cannot resolve key 'BPM_C01-02/x'"):
        cs.get_device_access("BPM_C01-02/x")


def test_get_device_rejects_unknown_reference_type():
    cs = TangoControlSystem(name="test_tango_cs")

    with pytest.raises(pyaml.PyAMLException, match="type int"):
        cs.get_device_access(42)


def test_tango_control_system_exposes_tango_host():
    cs = TangoControlSystem(name="test_tango_cs", tango_host="tangodb:10000")

    assert cs.get_tango_host() == "tangodb:10000"
