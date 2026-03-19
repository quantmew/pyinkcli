"""Tests for squashTextNodes parity behavior."""

from pyinkcli.dom import appendChildNode, createNode, createTextNode, squashTextNodes


def test_squashTextNodes_applies_child_transform_before_joining():
    root = createNode("ink-text")
    child = createNode("ink-virtual-text")
    child.internal_transform = lambda text, index: text.upper()
    appendChildNode(child, createTextNode("hello"))
    appendChildNode(root, child)

    assert squashTextNodes(root) == "HELLO"


def test_squashTextNodes_sanitizes_control_sequences():
    root = createNode("ink-text")
    appendChildNode(root, createTextNode("A\x1b[2JB"))

    assert squashTextNodes(root) == "AB"
