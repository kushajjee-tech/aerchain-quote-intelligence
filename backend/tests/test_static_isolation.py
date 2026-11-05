"""M0: static isolation rules (architecture §5.1 control 2).

- No file I/O in app code outside `app/storage` (builtin open, pathlib, os/shutil file ops,
  workbook/csv loaders given a path).
- No references to ground-truth material in app code.
"""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
IO_ALLOWED = {APP / "storage" / "__init__.py", APP / "config.py"}
EVAL_NAME_ALLOWED = {APP / "config.py"}
FORBIDDEN_LITERALS = ("answer_key", "truth", "aerchain-eval", "EVAL_ROOT", "eval_tests")
FORBIDDEN_MODULES = {"pathlib", "shutil", "glob"}
FORBIDDEN_OS_ATTRS = {"open", "remove", "unlink", "listdir", "walk", "scandir", "rename", "makedirs"}
PATH_LOADERS = {"load_workbook", "read_csv", "read_excel", "Document"}


def _py_files():
    return sorted(p for p in APP.rglob("*.py") if "__pycache__" not in p.parts)


def test_no_file_io_outside_storage():
    violations = []
    for f in _py_files():
        if f in IO_ALLOWED:
            continue
        tree = ast.parse(f.read_text(), filename=str(f))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in FORBIDDEN_MODULES:
                        violations.append(f"{f.name}:{node.lineno} import {a.name}")
            elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in FORBIDDEN_MODULES:
                violations.append(f"{f.name}:{node.lineno} from {node.module}")
            elif isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id == "open":
                    violations.append(f"{f.name}:{node.lineno} open()")
                if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id == "os" \
                        and fn.attr in FORBIDDEN_OS_ATTRS:
                    violations.append(f"{f.name}:{node.lineno} os.{fn.attr}")
                name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
                if name in PATH_LOADERS and node.args:
                    first = node.args[0]
                    ok = isinstance(first, ast.Call) and getattr(first.func, "attr", getattr(first.func, "id", "")) == "BytesIO"
                    if not ok:
                        violations.append(f"{f.name}:{node.lineno} {name}() must read from BytesIO via storage")
    assert not violations, "file I/O outside storage:\n" + "\n".join(violations)


def test_no_ground_truth_references():
    violations = []
    for f in _py_files():
        text = f.read_text()
        for lit in FORBIDDEN_LITERALS:
            if lit in text and not (f in EVAL_NAME_ALLOWED and lit in ("EVAL_ROOT", "aerchain-eval")):
                violations.append(f"{f.relative_to(APP)} mentions '{lit}'")
    assert not violations, "\n".join(violations)
