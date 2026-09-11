"""Small helpers shared by the Tango pyAML classes."""

import pyaml
import tango


def to_float_or_none(s):
    """
    Convert a value to ``float``, returning ``None`` when impossible.

    Tango reports unset attribute limits as the string ``"Not specified"``;
    this helper maps such values to ``None``.

    Parameters
    ----------
    s : object
        Value to convert (typically a string or a number).

    Returns
    -------
    float or None
        The converted value, or ``None`` if ``s`` cannot be converted.
    """
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def tango_to_PyAMLException(df: tango.DevFailed) -> pyaml.PyAMLException:
    """
    Convert a Tango DevFailed exception to a PyAMLException.

    Parameters
    ----------
    df : tango.DevFailed
        The original Tango exception to convert.

    Returns
    -------
    pyaml.PyAMLException
        Converted exception including reason, description, origin and severity.
    """
    if len(df.args) > 0:
        err = df.args[0]
        message = f"{err.reason}: {err.desc} Origin: {err.origin} Severity: {err.severity.name}"
    else:
        message = "Unknown tango error!"
    return pyaml.PyAMLException(message)
