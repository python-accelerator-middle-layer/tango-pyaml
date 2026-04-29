from unittest.mock import call, patch

import pyaml
import pytest
import tango
from pyaml.control.controlsystem import ControlSystemAdapter

from .mocked_device_proxy import MockedAttributeInfoEx, MockedAttributeProxy
from tango.pyaml.attribute import Attribute
from tango.pyaml.attribute_read_only import AttributeReadOnly
from tango.pyaml.controlsystem import ConfigModel as TangoControlSystemConfigModel
from tango.pyaml.controlsystem import TangoControlSystem
from tango.pyaml.tango_catalog import ConfigModel, TangoCatalog


def build_resolver(catalog: TangoCatalog, name="live"):
    control_system = TangoControlSystem(TangoControlSystemConfigModel(name=name))
    return catalog.attach_control_system(control_system)


def test_tango_catalog_disconnected_resolves_without_querying_tango():
    catalog = TangoCatalog(ConfigModel(name="tango-direct", disconnected=True))
    resolver = build_resolver(catalog)

    with patch("tango.AttributeProxy") as attr_proxy:
        device = resolver.resolve("domain/family/member/attribute")

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
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/current", attr_config),
    ):
        device = resolver.resolve("domain/family/member/current")

    assert isinstance(device, Attribute)
    assert not isinstance(device, AttributeReadOnly)
    assert device.name() == "domain/family/member/current"
    assert device.unit() == "A"
    assert device.get_range() == [-10.5, 12.0]
    assert (
        resolver.get_data_format("domain/family/member/current")
        == tango.AttrDataFormat.SPECTRUM
    )


def test_tango_catalog_connected_resolves_read_only_attribute():
    attr_config = MockedAttributeInfoEx(
        name="position", writable=tango.AttrWriteType.READ, unit="mm"
    )
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/position", attr_config),
    ):
        device = resolver.resolve("domain/family/member/position")

    assert isinstance(device, AttributeReadOnly)
    assert device.unit() == "mm"


def test_tango_catalog_caches_resolved_devices():
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/attribute"),
    ) as attr_proxy:
        first = resolver.resolve("domain/family/member/attribute")
        second = resolver.resolve("domain/family/member/attribute")

    attr_proxy.assert_called_once_with("domain/family/member/attribute")
    assert first is second


def test_tango_catalog_cache_is_bound_to_control_system_resolver():
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    live_resolver = build_resolver(catalog, name="live")
    ops_resolver = build_resolver(catalog, name="ops")

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/attribute"),
    ) as attr_proxy:
        live_first = live_resolver.resolve("domain/family/member/attribute")
        live_second = live_resolver.resolve("domain/family/member/attribute")
        ops_device = ops_resolver.resolve("domain/family/member/attribute")

    assert attr_proxy.call_count == 2
    assert live_first is live_second
    assert ops_device is not live_first


def test_tango_catalog_connected_metadata_uses_control_system_tango_host():
    key = "domain/family/member/current"
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    live = TangoControlSystem(
        TangoControlSystemConfigModel(name="live", tango_host="live-db:10000")
    )
    ops = TangoControlSystem(
        TangoControlSystemConfigModel(name="ops", tango_host="ops-db:10000")
    )
    live.set_catalog(catalog)
    ops.set_catalog(catalog)

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
        live_device = live.get_device(key)
        ops_device = ops.get_device(key)

    assert attr_proxy.call_args_list == [
        call("//live-db:10000/domain/family/member/current"),
        call("//ops-db:10000/domain/family/member/current"),
    ]
    assert live_device.name() == "//live-db:10000/domain/family/member/current"
    assert ops_device.name() == "//ops-db:10000/domain/family/member/current"
    assert live_device.get_range() == [-10.0, 10.0]
    assert ops_device.get_range() == [-2.5, 2.5]


def test_tango_catalog_can_be_used_through_tango_control_system():
    catalog = TangoCatalog(ConfigModel(name="tango-direct", disconnected=True))
    control_system = TangoControlSystem(TangoControlSystemConfigModel(name="live"))
    control_system.set_catalog(catalog)

    device = control_system.get_device("domain/family/member/attribute")

    assert isinstance(device, Attribute)
    assert control_system.get_catalog() is catalog


def test_tango_catalog_rejects_non_tango_control_system():
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))

    with pytest.raises(
        pyaml.PyAMLException, match="can only be attached to TangoControlSystem"
    ):
        catalog.attach_control_system(ControlSystemAdapter())


def test_tango_catalog_rejects_external_tango_control_system_class():
    class TangoControlSystem:
        pass

    catalog = TangoCatalog(ConfigModel(name="tango-direct"))

    with pytest.raises(
        pyaml.PyAMLException, match="can only be attached to TangoControlSystem"
    ):
        catalog.attach_control_system(TangoControlSystem())


def test_tango_catalog_requires_control_system_attachment():
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))

    with pytest.raises(
        pyaml.PyAMLException, match="must be attached to a TangoControlSystem"
    ):
        catalog.resolve("domain/family/member/attribute")


def test_tango_catalog_rejects_invalid_tango_reference():
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with pytest.raises(
        pyaml.PyAMLException, match="Expected 'domain/family/member/attribute'"
    ):
        resolver.resolve("domain/family/member")


def test_tango_catalog_rejects_invalid_index():
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with pytest.raises(pyaml.PyAMLException, match="invalid index"):
        resolver.resolve("domain/family/member/attribute@notanint")


def test_tango_catalog_disconnected_resolves_indexed_attribute():
    catalog = TangoCatalog(ConfigModel(name="tango-direct", disconnected=True))
    resolver = build_resolver(catalog)

    with patch("tango.AttributeProxy") as attr_proxy:
        device = resolver.resolve("domain/family/member/attribute@1")

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
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/position", attr_config),
    ):
        device = resolver.resolve("domain/family/member/position@0")

    assert isinstance(device, Attribute) and device._index is not None
    assert not isinstance(device, AttributeReadOnly)
    assert device.name() == "domain/family/member/position[0]"
    assert device.unit() == "mm"
    assert (
        resolver.get_data_format("domain/family/member/position@0")
        == tango.AttrDataFormat.SPECTRUM
    )


def test_tango_catalog_connected_resolves_indexed_read_only_spectrum():
    attr_config = MockedAttributeInfoEx(
        name="position",
        writable=tango.AttrWriteType.READ,
        unit="mm",
        data_format=tango.AttrDataFormat.SPECTRUM,
    )
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/position", attr_config),
    ):
        device = resolver.resolve("domain/family/member/position@2")

    assert isinstance(device, AttributeReadOnly) and device._index is not None
    assert device.unit() == "mm"


def test_tango_catalog_connected_rejects_indexed_scalar_attribute():
    attr_config = MockedAttributeInfoEx(
        name="current",
        writable=tango.AttrWriteType.READ_WRITE,
        data_format=tango.AttrDataFormat.SCALAR,
    )
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/current", attr_config),
    ):
        with pytest.raises(pyaml.PyAMLException, match="not a SPECTRUM"):
            resolver.resolve("domain/family/member/current@0")


def test_tango_catalog_indexed_caches_resolved_devices():
    attr_config = MockedAttributeInfoEx(
        name="position",
        data_format=tango.AttrDataFormat.SPECTRUM,
    )
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy("domain/family/member/position", attr_config),
    ) as attr_proxy:
        first = resolver.resolve("domain/family/member/position@1")
        second = resolver.resolve("domain/family/member/position@1")

    attr_proxy.assert_called_once_with("domain/family/member/position")
    assert first is second


def test_tango_catalog_wraps_tango_errors():
    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with patch("tango.AttributeProxy", side_effect=tango.DevFailed()):
        with pytest.raises(
            pyaml.PyAMLException,
            match="Tango catalog 'tango-direct' cannot resolve 'domain/family/member/attribute'",
        ):
            resolver.resolve("domain/family/member/attribute")


def test_tango_catalog_rejects_incomplete_tango_config():
    class IncompleteAttributeConfig:
        unit = "A"
        min_value = "-1"
        max_value = "1"
        data_format = tango.AttrDataFormat.SCALAR

    catalog = TangoCatalog(ConfigModel(name="tango-direct"))
    resolver = build_resolver(catalog)

    with patch(
        "tango.AttributeProxy",
        return_value=MockedAttributeProxy(
            "domain/family/member/attribute", IncompleteAttributeConfig()
        ),
    ):
        with pytest.raises(
            pyaml.PyAMLException,
            match="incomplete Tango attribute config, missing 'writable'",
        ):
            resolver.resolve("domain/family/member/attribute")
