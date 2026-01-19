from tango.pyaml.controlsystem import TangoControlSystem


class MockedControlSystemInitialized(TangoControlSystem):
    @classmethod
    def is_initialized(cls):
        return True
