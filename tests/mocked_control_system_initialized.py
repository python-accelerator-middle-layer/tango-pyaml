from tango.pyaml.controlsystem import TangoControlSystem, ConfigModel


class MockedControlSystemInitialized(TangoControlSystem):

    @classmethod
    def is_initialized(cls):
        return True
