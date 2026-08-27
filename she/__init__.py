"""SHE — a programming language that reads like English.

    from she import run
    run('say "Hello, World!"')

Public surface:
    run(source, ...)      run a piece of SHE source, return (result, error)
    Interpreter           the evaluator, if you want to drive it yourself
    Sandbox / Grant       what a program is allowed to do
    parse(source)         source -> AST
    format_source(text)   canonical formatting
"""

__version__ = "2.0.1"
__all__ = [
    "__version__", "run", "run_file", "Interpreter", "Sandbox", "Grant",
    "parse", "format_source", "SheError",
]

from .errors import SheError
from .interp import Interpreter
from .parser import parse
from .sandbox import Grant, Sandbox


def run(source, file="<input>", sandbox=None, out=None, ask=None, interp=None):
    """Run SHE source. Returns (result, error) — error is None when it worked."""
    engine = interp or Interpreter(sandbox=sandbox, out=out, ask=ask, file=file)
    try:
        return engine.run(source, file), None
    except SheError as exc:
        return None, exc
    finally:
        if interp is None:
            engine.shutdown()


def run_file(path, sandbox=None, out=None, ask=None):
    """Run a .she file. Returns (result, error)."""
    with open(path, encoding="utf-8") as handle:
        return run(handle.read(), path, sandbox=sandbox, out=out, ask=ask)


def format_source(source, file="<input>"):
    from .formatter import format_source as _format
    return _format(source, file)
