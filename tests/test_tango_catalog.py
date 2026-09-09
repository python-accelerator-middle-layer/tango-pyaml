from unittest.mock import call, patch

import pyaml
import pytest
from pyaml.control.controlsystem import ControlSystemAdapter

import tango
from tango.pyaml.attribute import Attribute
from tango.pyaml.attribute_read_only import AttributeReadOnly
from tango.pyaml.controlsystem import TangoControlSystem
from tango.pyaml.tango_catalog import TangoCatalog

from .mocked_device_proxy import MockedAttributeInfoEx, MockedAttributeProxy


def build_control_system(catalog: TangoCatalog, name="live"):
    control_system = TangoControlSystem(name=name, catalog=catalog)
    return control_system


def test_tango_catalog_disconnected_resolves_without_querying_tango():
    catalog = TangoCatalog(disconnected=True)
    control_system = build_control_system(catalog)

    with patch("tango.AttributeProxy") as attr_proxy:
        device = catalog.resolve("domain/family/member/attribute", control_system)

    attr_proxy.assert_not_called()
    assert isinstance(device, Attribute)
    assert device.name() == "domain/family/member/attribute"
    assert device.unit() == ""
    assert device.get_range() == [None, None]


def test_tango_catalog_connected_resolves_writable_attribute():
    attr_config = MockedAttributeInfoEx(
        name="current",
        writable=tango.AttrWriteType.READ_WRITE,
        unit="A",
        min_value="-10.5",
        max_value="12.0",
        data_format=tango.AttrDataFormat.SPECTRUM,
    )
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/current", attr_config),
    ):
        device = catalog.resolve("domain/family/member/current", control_system)

    assert isinstance(device, Attribute)
    assert not isinstance(device, AttributeReadOnly)
    assert device.name() == "domain/family/member/current"
    assert device.unit() == "A"
    assert device.get_range() == [-10.5, 12.0]
    assert (
        catalog.get_data_format("domain/family/member/current", control_system)
        == tango.AttrDataFormat.SPECTRUM
    )


def test_tango_catalog_connected_resolves_read_only_attribute():
    attr_config = MockedAttributeInfoEx(
        name="position", writable=tango.AttrWriteType.READ, unit="mm"
    )
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/position", attr_config),
    ):
        device = catalog.resolve("domain/family/member/position", control_system)

    assert isinstance(device, AttributeReadOnly)
    assert device.unit() == "mm"


def test_tango_catalog_caches_resolved_devices():
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/attribute"),
    ) as attr_proxy:
        first = catalog.resolve("domain/family/member/attribute", control_system)
        second = catalog.resolve("domain/family/member/attribute", control_system)

    attr_proxy.assert_called_once_with("domain/family/member/attribute")
    assert first is second


def test_tango_catalog_cache_is_bound_to_control_system_resolver():
    catalog = TangoCatalog()
    live = build_control_system(catalog, name="live")
    ops = build_control_system(catalog, name="ops")

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/attribute"),
    ) as attr_proxy:
        live_first = catalog.resolve("domain/family/member/attribute", live)
        live_second = catalog.resolve("domain/family/member/attribute", live)
        ops_device = catalog.resolve("domain/family/member/attribute", ops)

    assert attr_proxy.call_count == 2
    assert live_first is live_second
    assert ops_device is not live_first


def test_tango_catalog_connected_metadata_uses_control_system_tango_host():
    key = "domain/family/member/current"
    catalog = TangoCatalog()
    live = TangoControlSystem(name="live", tango_host="live-db:10000", catalog=catalog)
    ops = TangoControlSystem(name="ops", tango_host="ops-db:10000", catalog=catalog)

    attr_configs = {
        "//live-db:10000/domain/family/member/current": MockedAttributeInfoEx(
            name="current",
            min_value="-10.0",
            max_value="10.0",
        ),
        "//ops-db:10000/domain/family/member/current": MockedAttributeInfoEx(
            name="current",
            min_value="-2.5",
            max_value="2.5",
        ),
    }

    def attribute_proxy(attr_full_name):
        return MockedAttributeProxy(attr_full_name, attr_configs[attr_full_name])

    with patch("tango.AttributeProxy", side_effect=attribute_proxy) as attr_proxy:
        live_device = live.get_device_access(key)
        ops_device = ops.get_device_access(key)

    assert attr_proxy.call_args_list == [
        call("//live-db:10000/domain/family/member/current"),
        call("//ops-db:10000/domain/family/member/current"),
    ]
    assert live_device.name() == "//live-db:10000/domain/family/member/current"
    assert ops_device.name() == "//ops-db:10000/domain/family/member/current"
    assert live_device.get_range() == [-10.0, 10.0]
    assert ops_device.get_range() == [-2.5, 2.5]


def test_tango_catalog_can_be_used_through_tango_control_system():
    catalog = TangoCatalog(disconnected=True)
    control_system = TangoControlSystem(name="live", catalog=catalog)

    device = control_system.get_device_access("domain/family/member/attribute")

    assert isinstance(device, Attribute)
    assert control_system.get_catalog() is catalog


def test_tango_catalog_rejects_non_tango_control_system():
    catalog = TangoCatalog()

    with pytest.raises(
        pyaml.PyAMLException, match="can only resolve through TangoControlSystem"
    ):
        catalog.resolve("domain/family/member/attribute", ControlSystemAdapter())


def test_tango_catalog_rejects_external_tango_control_system_class():
    class TangoControlSystem:
        pass

    catalog = TangoCatalog()

    with pytest.raises(
        pyaml.PyAMLException, match="can only resolve through TangoControlSystem"
    ):
        catalog.resolve("domain/family/member/attribute", TangoControlSystem())


def test_tango_catalog_requires_control_system_attachment():
    catalog = TangoCatalog()

    with pytest.raises(
        pyaml.PyAMLException, match="needs a TangoControlSystem context"
    ):
        catalog.resolve("domain/family/member/attribute")


def test_tango_catalog_rejects_invalid_tango_reference():
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with pytest.raises(
        pyaml.PyAMLException, match="Expected 'domain/family/member/attribute'"
    ):
        catalog.resolve("domain/family/member", control_system)


def test_tango_catalog_rejects_invalid_index():
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with pytest.raises(pyaml.PyAMLException, match="invalid index"):
        catalog.resolve("domain/family/member/attribute@notanint", control_system)


def test_tango_catalog_disconnected_resolves_indexed_attribute():
    catalog = TangoCatalog(disconnected=True)
    control_system = build_control_system(catalog)

    with patch("tango.AttributeProxy") as attr_proxy:
        device = catalog.resolve("domain/family/member/attribute@1", control_system)

    attr_proxy.assert_not_called()
    assert isinstance(device, Attribute) and device._index is not None
    assert device.name() == "domain/family/member/attribute[1]"
    assert device.unit() == ""
    assert device.get_range() == [None, None]


def test_tango_catalog_connected_resolves_indexed_writable_spectrum():
    attr_config = MockedAttributeInfoEx(
        name="position",
        writable=tango.AttrWriteType.READ_WRITE,
        unit="mm",
        data_format=tango.AttrDataFormat.SPECTRUM,
    )
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/position", attr_config),
    ):
        device = catalog.resolve("domain/family/member/position@0", control_system)

    assert isinstance(device, Attribute) and device._index is not None
    assert not isinstance(device, AttributeReadOnly)
    assert device.name() == "domain/family/member/position[0]"
    assert device.unit() == "mm"
    assert (
        catalog.get_data_format("domain/family/member/position@0", control_system)
        == tango.AttrDataFormat.SPECTRUM
    )


def test_tango_catalog_connected_resolves_indexed_read_only_spectrum():
    attr_config = MockedAttributeInfoEx(
        name="position",
        writable=tango.AttrWriteType.READ,
        unit="mm",
        data_format=tango.AttrDataFormat.SPECTRUM,
    )
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/position", attr_config),
    ):
        device = catalog.resolve("domain/family/member/position@2", control_system)

    assert isinstance(device, AttributeReadOnly) and device._index is not None
    assert device.unit() == "mm"


def test_tango_catalog_connected_rejects_indexed_scalar_attribute():
    attr_config = MockedAttributeInfoEx(
        name="current",
        writable=tango.AttrWriteType.READ_WRITE,
        data_format=tango.AttrDataFormat.SCALAR,
    )
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with (
        patch(
            "tango.AttributeProxy",
            return_value=MockedAttributeProxy(
                "domain/family/member/current", attr_config
            ),
        ),
        pytest.raises(pyaml.PyAMLException, match="not a SPECTRUM"),
    ):
        catalog.resolve("domain/family/member/current@0", control_system)


def test_tango_catalog_indexed_caches_resolved_devices():
    attr_config = MockedAttributeInfoEx(
        name="position",
        data_format=tango.AttrDataFormat.SPECTRUM,
    )
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/position", attr_config),
    ) as attr_proxy:
        first = catalog.resolve("domain/family/member/position@1", control_system)
        second = catalog.resolve("domain/family/member/position@1", control_system)

    attr_proxy.assert_called_once_with("domain/family/member/position")
    assert first is second


def test_tango_catalog_wraps_tango_errors():
    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with (
        patch("tango.AttributeProxy", side_effect=tango.DevFailed()),
        pytest.raises(
            pyaml.PyAMLException,
            match="Tango catalog cannot resolve 'domain/family/member/attribute'",
        ),
    ):
        catalog.resolve("domain/family/member/attribute", control_system)


def test_tango_catalog_rejects_incomplete_tango_config():
    class IncompleteAttributeConfig:
        unit = "A"
        min_value = "-1"
        max_value = "1"
        data_format = tango.AttrDataFormat.SCALAR

    catalog = TangoCatalog()
    control_system = build_control_system(catalog)

    with (
        patch(
            "tango.AttributeProxy",
            return_value=MockedAttributeProxy(
                "domain/family/member/attribute", IncompleteAttributeConfig()
            ),
        ),
        pytest.raises(
            pyaml.PyAMLException,
            match="incomplete Tango attribute config, missing 'writable'",
        ),
    ):
        catalog.resolve("domain/family/member/attribute", control_system)
