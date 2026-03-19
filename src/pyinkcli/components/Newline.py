from pyinkcli._component_runtime import createElement


def Newline():
    return createElement("ink-text", "\n")


__all__ = ["Newline"]
