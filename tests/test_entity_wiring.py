"""
Tests that every entity method/state_key reference points to a real
method on SensoWashClient.

Uses AST + direct lib/ import to avoid needing homeassistant installed.
"""
import ast
import os
import re
import sys

LIB = os.path.join(os.path.dirname(__file__), "..", "custom_components", "sensowash", "lib")
sys.path.insert(0, os.path.abspath(LIB))

CC = os.path.join(os.path.dirname(__file__), "..", "custom_components", "sensowash")


def _client_method_names():
    """Parse client.py with AST and return all defined async/sync method names."""
    path = os.path.join(LIB, "client.py")
    tree = ast.parse(open(path).read())
    methods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SensoWashClient":
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.add(item.name)
    return methods


def _extract_string_values(path, attr):
    """Extract all string literal values for a given keyword attribute name from a Python file."""
    tree = ast.parse(open(path).read())
    values = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == attr:
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                values.append(node.value.value)
    return values


def test_button_methods_exist():
    methods = _client_method_names()
    refs = _extract_string_values(os.path.join(CC, "button.py"), "method")
    missing = [m for m in refs if m not in methods]
    assert not missing, f"Button methods not on SensoWashClient: {missing}"


def test_select_set_methods_exist():
    methods = _client_method_names()
    refs = _extract_string_values(os.path.join(CC, "select.py"), "set_method")
    missing = [m for m in refs if m not in methods]
    assert not missing, f"Select set_methods not on SensoWashClient: {missing}"


def test_switch_methods_exist():
    methods = _client_method_names()
    for attr in ("turn_on_method", "turn_off_method"):
        refs = _extract_string_values(os.path.join(CC, "switch.py"), attr)
        missing = [m for m in refs if m not in methods]
        assert not missing, f"Switch {attr} not on SensoWashClient: {missing}"


def test_no_duplicate_entity_keys():
    """Each platform must have unique keys."""
    for platform in ("button", "select", "switch", "sensor", "binary_sensor"):
        path = os.path.join(CC, f"{platform}.py")
        keys = _extract_string_values(path, "key")
        dupes = [k for k in keys if keys.count(k) > 1]
        assert not dupes, f"Duplicate keys in {platform}.py: {dupes}"


def test_lib_models_exports_all_used_names():
    """
    Every name imported from .lib.models across the integration
    must exist in lib/models.py.
    """
    import importlib
    models = importlib.import_module("models")
    exported = set(dir(models))

    for fname in os.listdir(CC):
        if not fname.endswith(".py"):
            continue
        src = open(os.path.join(CC, fname)).read()
        # Match: from .lib.models import (\n    X,\n    Y,\n) or single-line
        for match in re.findall(r"from \.lib\.models import \(([^)]+)\)", src, re.DOTALL):
            names = [n.strip().rstrip(",") for n in match.split("\n") if n.strip().rstrip(",")]
            missing = [n for n in names if n and not n.startswith("#") and n not in exported]
            assert not missing, f"{fname} imports {missing} from .lib.models but they don't exist"
        for match in re.findall(r"from \.lib\.models import ([^(\n][^\n]+)", src):
            names = [n.strip().rstrip(",") for n in match.split(",")]
            missing = [n for n in names if n and n not in exported]
            assert not missing, f"{fname} imports {missing} from .lib.models but they don't exist"
