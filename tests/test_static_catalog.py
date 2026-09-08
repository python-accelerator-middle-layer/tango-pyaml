import pyaml
import pytest

from tango.pyaml.attribute import Attribute
from tango.pyaml.attribute_read_only import AttributeReadOnly
from tango.pyaml.controlsystem import TangoControlSystem
from tango.pyaml.static_catalog import StaticCatalog
from tango.pyaml.static_catalog_entry import StaticCatalogEntry


def make_attribute(
    path: str = "domain/family/member/attr", unit: str = "mm"
) -> Attribute:
    return Attribute(attribute=path, unit=unit)


def make_entry(key: str, device=None) -> StaticCatalogEntry:
    if device is None:
        device = make_attribute()
    return StaticCatalogEntry(key=key, device=device)


def make_catalog(name: str = "static", entries=None) -> StaticCatalog:
    if entries is None:
        entries = [make_entry("default/key")]
    return StaticCatalog(entries=entries)


# --- StaticCatalogEntry ---


def test_static_catalog_entry_returns_key():
    entry = make_entry("BPM/x")
    assert entry.get_key() == "BPM/x"


def test_static_catalog_entry_returns_device():
    device = make_attribute("sr/bpm/c01-01/x", unit="mm")
    entry = make_entry("BPM/x", device=device)
    assert entry.get_device() is device


# --- StaticCatalog construction ---


def test_static_catalog_rejects_empty_entries():
    with pytest.raises(pyaml.PyAMLException, match="must contain at least one entry"):
        StaticCatalog(entries=[])


def test_static_catalog_rejects_duplicate_keys():
    entries = [make_entry("BPM/x"), make_entry("BPM/x")]
    with pytest.raises(pyaml.PyAMLException, match="duplicate key 'BPM/x'"):
        StaticCatalog(entries=entries)


# --- StaticCatalog.resolve ---


def test_static_catalog_resolves_known_key():
    device = make_attribute("sr/bpm/c01-01/position")
    catalog = make_catalog(entries=[make_entry("BPM_C01-01/x", device=device)])

    resolved = catalog.resolve("BPM_C01-01/x")

    assert resolved is device


def test_static_catalog_resolves_multiple_entries():
    device_x = make_attribute("sr/bpm/c01-01/x")
    device_y = make_attribute("sr/bpm/c01-01/y")
    catalog = make_catalog(
        entries=[
            make_entry("BPM/x", device=device_x),
            make_entry("BPM/y", device=device_y),
        ]
    )

    assert catalog.resolve("BPM/x") is device_x
    assert catalog.resolve("BPM/y") is device_y


def test_static_catalog_raises_on_unknown_key():
    catalog = make_catalog(entries=[make_entry("BPM/x")])

    with pytest.raises(pyaml.PyAMLException, match="cannot resolve key 'BPM/y'"):
        catalog.resolve("BPM/y")


def test_static_catalog_is_shared_across_control_systems():
    device = make_attribute()
    catalog = make_catalog(entries=[make_entry("BPM/x", device=device)])
    live = TangoControlSystem(name="live", catalog=catalog)
    ops = TangoControlSystem(name="ops", catalog=catalog)

    assert live.get_catalog() is catalog
    assert ops.get_catalog() is catalog
    assert catalog.resolve("BPM/x") is device
    assert live.get_device_access("BPM/x") is not device
    assert ops.get_device_access("BPM/x") is not device
    assert live.get_device_access("BPM/x") is not ops.get_device_access("BPM/x")


# --- Integration with DeviceAccess types ---


def test_static_catalog_works_with_attribute_read_only():
    device = AttributeReadOnly(attribute="sr/bpm/c01-01/pos", unit="mm")
    catalog = make_catalog(entries=[make_entry("BPM/x", device=device)])

    resolved = catalog.resolve("BPM/x")

    assert isinstance(resolved, AttributeReadOnly)
    assert resolved.unit() == "mm"


def test_static_catalog_can_be_used_through_tango_control_system():
    device = make_attribute("sr/bpm/c01-01/x", unit="mm")
    catalog = make_catalog(entries=[make_entry("BPM/x", device=device)])
    control_system = TangoControlSystem(name="live", catalog=catalog)

    resolved = control_system.get_device_access("BPM/x")

    assert resolved is not device
    assert resolved.name() == "sr/bpm/c01-01/x"
