import tango
import pyaml


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
    if len(df.args)>0:
        err = df.args[0]
        message = f"{err.reason}: {err.desc} Origin: {err.origin} Severity: {err.severity.name}"
    else:
        message = "Unknown tango error!"
    return pyaml.PyAMLException(message)