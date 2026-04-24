import numpy as np
import pytest
import tango
from unittest.mock import patch

import pyaml

from tango.pyaml.attribute_indexed import AttributeIndexed, ConfigModel
from tango.pyaml.attribute_indexed_read_only import AttributeIndexedReadOnly
from .mocked_device_proxy import MockedAttributeInfoEx, MockedDeviceProxy, MockedDeviceAttribute


SPECTRUM_ARRAY = np.array([10.0, 20.0, 30.0])


class MockedSpectrumDeviceProxy(MockedDeviceProxy):
    """DeviceProxy that returns a SPECTRUM (READ_WRITE) attribute."""

    def attribute_query(self, name):
        return MockedAttributeInfoEx(
            name,
            writable=tango.AttrWriteType.READ_WRITE,
            data_format=tango.AttrDataFormat.SPECTRUM,
            unit="mm",
        )

    def read_attribute(self, name):
        return MockedDeviceAttribute(name, SPECTRUM_ARRAY)


class MockedSpectrumRODeviceProxy(MockedDeviceProxy):
    """DeviceProxy that returns a SPECTRUM (READ) attribute."""

    def attribute_query(self, name):
        return MockedAttributeInfoEx(
            name,
            writable=tango.AttrWriteType.READ,
            data_format=tango.AttrDataFormat.SPECTRUM,
            unit="mm",
        )

    def read_attribute(self, name):
        return MockedDeviceAttribute(name, SPECTRUM_ARRAY)


class MockedScalarDeviceProxy(MockedDeviceProxy):
    """DeviceProxy that returns a SCALAR attribute."""

    def attribute_query(self, name):
        return MockedAttributeInfoEx(
            name,
            data_format=tango.AttrDataFormat.SCALAR,
        )


# --- AttributeIndexed ---


def test_attribute_indexed_get_returns_w_value_at_index():
    cfg = ConfigModel(attribute="domain/family/member/position", index=1, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumDeviceProxy):
        attr = AttributeIndexed(cfg)
        assert attr.get() == SPECTRUM_ARRAY[1]


def test_attribute_indexed_readback_returns_value_at_index():
    cfg = ConfigModel(attribute="domain/family/member/position", index=0, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumDeviceProxy):
        attr = AttributeIndexed(cfg)
        rb = attr.readback()
        assert rb.value == SPECTRUM_ARRAY[0]


def test_attribute_indexed_set_raises():
    cfg = ConfigModel(attribute="domain/family/member/position", index=0)
    with patch("tango.DeviceProxy", new=MockedSpectrumDeviceProxy):
        attr = AttributeIndexed(cfg)
        with pytest.raises(pyaml.PyAMLException, match="does not support individual element writes"):
            attr.set(99.0)


def test_attribute_indexed_set_and_wait_raises():
    cfg = ConfigModel(attribute="domain/family/member/position", index=0)
    with patch("tango.DeviceProxy", new=MockedSpectrumDeviceProxy):
        attr = AttributeIndexed(cfg)
        with pytest.raises(pyaml.PyAMLException, match="does not support individual element writes"):
            attr.set_and_wait(99.0)


def test_attribute_indexed_name_includes_index():
    cfg = ConfigModel(attribute="domain/family/member/position", index=2)
    attr = AttributeIndexed(cfg)
    assert attr.name() == "domain/family/member/position[2]"


def test_attribute_indexed_measure_name_includes_index():
    cfg = ConfigModel(attribute="domain/family/member/position", index=2)
    attr = AttributeIndexed(cfg)
    assert attr.measure_name() == "position[2]"


def test_attribute_indexed_unit():
    cfg = ConfigModel(attribute="domain/family/member/position", index=0, unit="mm")
    attr = AttributeIndexed(cfg)
    assert attr.unit() == "mm"


def test_attribute_indexed_raises_when_not_spectrum():
    cfg = ConfigModel(attribute="domain/family/member/current", index=0)
    with patch("tango.DeviceProxy", new=MockedScalarDeviceProxy):
        attr = AttributeIndexed(cfg)
        with pytest.raises(pyaml.PyAMLException, match="not a SPECTRUM"):
            attr.get()


def test_attribute_indexed_range_from_config():
    cfg = ConfigModel(
        attribute="domain/family/member/position", index=0, unit="mm", range=(-5.0, 5.0)
    )
    attr = AttributeIndexed(cfg)
    assert attr.get_range() == [-5.0, 5.0]


# --- AttributeIndexedReadOnly ---


def test_attribute_indexed_read_only_get_returns_measured_value():
    cfg = ConfigModel(attribute="domain/family/member/position", index=2, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumRODeviceProxy):
        attr = AttributeIndexedReadOnly(cfg)
        assert attr.get() == SPECTRUM_ARRAY[2]


def test_attribute_indexed_read_only_readback_returns_value_at_index():
    cfg = ConfigModel(attribute="domain/family/member/position", index=1, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumRODeviceProxy):
        attr = AttributeIndexedReadOnly(cfg)
        assert attr.readback().value == SPECTRUM_ARRAY[1]


def test_attribute_indexed_read_only_set_raises():
    cfg = ConfigModel(attribute="domain/family/member/position", index=0)
    with patch("tango.DeviceProxy", new=MockedSpectrumRODeviceProxy):
        attr = AttributeIndexedReadOnly(cfg)
        with pytest.raises(pyaml.PyAMLException):
            attr.set(1.0)


def test_attribute_indexed_read_only_get_equals_readback():
    cfg = ConfigModel(attribute="domain/family/member/position", index=0, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumRODeviceProxy):
        attr = AttributeIndexedReadOnly(cfg)
        assert attr.get() == attr.readback().value
