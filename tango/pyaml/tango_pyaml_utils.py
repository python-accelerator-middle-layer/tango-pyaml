import tango
import pyaml


def tango_to_PyAMLException(df: tango.DevFailed) -> pyaml.PyAMLException:
    if len(df.args)>0:
        err = df.args[0]
        message = f"{err.reason}: {err.desc} Origin: {err.origin} Severity: {err.severity.name}"
    else:
        message = "Unknown tango error!"
    return pyaml.PyAMLException(message)