import numpy as np
import pytest
import tango
from unittest.mock import patch

import pyaml

from tango.pyaml.attribute import Attribute, AttributeConfig
from tango.pyaml.attribute_read_only import AttributeReadOnly
from .mocked_device_proxy import (
    MockedAttributeInfoEx,
    MockedDeviceProxy,
    MockedDeviceAttribute,
)


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


# --- Attribute with index ---


def test_attribute_indexed_get_returns_w_value_at_index():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=1, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumDeviceProxy):
        attr = Attribute(**cfg.model_dump())
        assert attr.get() == SPECTRUM_ARRAY[1]


def test_attribute_indexed_readback_returns_value_at_index():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=0, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumDeviceProxy):
        attr = Attribute(**cfg.model_dump())
        rb = attr.readback()
        assert rb.value == SPECTRUM_ARRAY[0]


def test_attribute_indexed_set_raises():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=0)
    with patch("tango.DeviceProxy", new=MockedSpectrumDeviceProxy):
        attr = Attribute(**cfg.model_dump())
        with pytest.raises(
            pyaml.PyAMLException, match="does not support individual element writes"
        ):
            attr.set(99.0)


def test_attribute_indexed_set_and_wait_raises():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=0)
    with patch("tango.DeviceProxy", new=MockedSpectrumDeviceProxy):
        attr = Attribute(**cfg.model_dump())
        with pytest.raises(
            pyaml.PyAMLException, match="does not support individual element writes"
        ):
            attr.set_and_wait(99.0)


def test_attribute_indexed_name_includes_index():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=2)
    attr = Attribute(**cfg.model_dump())
    assert attr.name() == "domain/family/member/position[2]"


def test_attribute_indexed_measure_name_includes_index():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=2)
    attr = Attribute(**cfg.model_dump())
    assert attr.measure_name() == "position[2]"


def test_attribute_indexed_unit():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=0, unit="mm")
    attr = Attribute(**cfg.model_dump())
    assert attr.unit() == "mm"


def test_attribute_indexed_raises_when_not_spectrum():
    cfg = AttributeConfig(attribute="domain/family/member/current", index=0)
    with patch("tango.DeviceProxy", new=MockedScalarDeviceProxy):
        attr = Attribute(**cfg.model_dump())
        with pytest.raises(pyaml.PyAMLException, match="not a SPECTRUM"):
            attr.get()


def test_attribute_indexed_range_from_config():
    cfg = AttributeConfig(
        attribute="domain/family/member/position", index=0, unit="mm", range=(-5.0, 5.0)
    )
    attr = Attribute(**cfg.model_dump())
    assert attr.get_range() == [-5.0, 5.0]


# --- AttributeReadOnly with index ---


def test_attribute_indexed_read_only_get_returns_measured_value():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=2, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumRODeviceProxy):
        attr = AttributeReadOnly(**cfg.model_dump())
        assert attr.get() == SPECTRUM_ARRAY[2]


def test_attribute_indexed_read_only_readback_returns_value_at_index():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=1, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumRODeviceProxy):
        attr = AttributeReadOnly(**cfg.model_dump())
        assert attr.readback().value == SPECTRUM_ARRAY[1]


def test_attribute_indexed_read_only_set_raises():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=0)
    with patch("tango.DeviceProxy", new=MockedSpectrumRODeviceProxy):
        attr = AttributeReadOnly(**cfg.model_dump())
        with pytest.raises(pyaml.PyAMLException):
            attr.set(1.0)


def test_attribute_indexed_read_only_get_equals_readback():
    cfg = AttributeConfig(attribute="domain/family/member/position", index=0, unit="mm")
    with patch("tango.DeviceProxy", new=MockedSpectrumRODeviceProxy):
        attr = AttributeReadOnly(**cfg.model_dump())
        assert attr.get() == attr.readback().value
