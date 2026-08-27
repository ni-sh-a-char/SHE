"""SHE runtime values.

SHE values are plain Python values wherever possible:

    number   -> int | float          text  -> str
    bool     -> bool                 list  -> list
    nothing  -> None                 map   -> dict

Only things Python has no good match for get a class: functions, types,
instances, ranges and futures. Keeping the common cases native makes the
standard library nearly free to write and keeps the interpreter fast.
"""

import math

from .errors import TypeErr


class Nothing:
    """Marker only used for `type_name`; the runtime value of `nothing` is None."""


class Range:
    __slots__ = ("start", "stop", "step", "inclusive")

    def __init__(self, start, stop, step=1, inclusive=True):
        self.start, self.stop, self.inclusive = start, stop, inclusive
        self.step = 1 if step in (None, 0) else step

    def __iter__(self):
        cur, step = self.start, self.step
        if step > 0:
            while (cur <= self.stop) if self.inclusive else (cur < self.stop):
                yield cur
                cur += step
        else:
            while (cur >= self.stop) if self.inclusive else (cur > self.stop):
                yield cur
                cur += step

    def __len__(self):
        span = self.stop - self.start
        if (span > 0) != (self.step > 0) and span != 0:
            return 0
        n = int(span / self.step) + (1 if self.inclusive else 0)
        if not self.inclusive and span % self.step == 0:
            n = int(span / self.step)
        return max(0, n)

    def __contains__(self, item):
        if not isinstance(item, (int, float)) or isinstance(item, bool):
            return False
        lo, hi = (self.start, self.stop) if self.step > 0 else (self.stop, self.start)
        if not (lo <= item <= hi if self.inclusive else lo <= item < hi):
            return False
        return (item - self.start) % self.step == 0

    def __eq__(self, other):
        return (isinstance(other, Range) and self.start == other.start
                and self.stop == other.stop and self.step == other.step
                and self.inclusive == other.inclusive)

    def __hash__(self):
        return hash((self.start, self.stop, self.step, self.inclusive))

    def __repr__(self):
        dots = ".." if self.inclusive else "..<"
        tail = f" by {self.step}" if self.step != 1 else ""
        return f"{show(self.start)}{dots}{show(self.stop)}{tail}"


class Function:
    """A user-defined function or method. Closes over `env`."""

    __slots__ = ("name", "params", "body", "is_expr", "is_async", "env",
                 "doc", "returns", "bound_self")

    def __init__(self, name, params, body, is_expr, env, is_async=False,
                 doc=None, returns=None, bound_self=None):
        self.name = name or "<anonymous>"
        self.params = params
        self.body = body
        self.is_expr = is_expr
        self.is_async = is_async
        self.env = env
        self.doc = doc
        self.returns = returns
        self.bound_self = bound_self

    def bind(self, instance):
        return Function(self.name, self.params, self.body, self.is_expr, self.env,
                        self.is_async, self.doc, self.returns, instance)

    @property
    def arity(self):
        required = sum(1 for p in self.params if p.default is None and not p.variadic)
        return required

    def signature(self):
        parts = []
        for p in self.params:
            text = ("..." if p.variadic else "") + p.name
            if p.type_:
                text += ": " + type_label(p.type_)
            if p.default is not None:
                text += " = ..."
            parts.append(text)
        return f"{self.name}({', '.join(parts)})"

    def __repr__(self):
        return f"<function {self.name}>"


class Builtin:
    """A standard-library function implemented in Python.

    `fn` receives (interp, args, kwargs, node). Simple builtins are wrapped by
    `she.stdlib.wrap` so they can just be ordinary Python callables.
    """

    __slots__ = ("name", "fn", "doc", "arity", "module")

    def __init__(self, name, fn, doc=None, arity=None, module=None):
        self.name = name
        self.fn = fn
        self.doc = doc
        self.arity = arity
        self.module = module

    def signature(self):
        return f"{self.name}(...)"

    def __repr__(self):
        return f"<builtin {self.name}>"


class Module:
    """A namespace: a stdlib module or another .she file loaded with `use`."""

    __slots__ = ("name", "values", "doc", "path")

    def __init__(self, name, values=None, doc=None, path=None):
        self.name = name
        self.values = values if values is not None else {}
        self.doc = doc
        self.path = path

    def __repr__(self):
        return f"<module {self.name}>"


class Type:
    """A user-defined type declared with `type Name has ...`."""

    __slots__ = ("name", "fields", "methods", "parent", "doc")

    def __init__(self, name, fields, methods, parent=None, doc=None):
        self.name = name
        self.fields = fields            # list[(name, default_node, type_)]
        self.methods = methods          # dict[str, Function]
        self.parent = parent
        self.doc = doc

    def all_fields(self):
        """Inherited fields first, then new ones. Re-declaring a parent field
        replaces it in place rather than adding a second one of the same name."""
        out = list(self.parent.all_fields()) if self.parent else []
        positions = {name: i for i, (name, _, _) in enumerate(out)}
        for field in self.fields:
            if field[0] in positions:
                out[positions[field[0]]] = field
            else:
                positions[field[0]] = len(out)
                out.append(field)
        return out

    def find_method(self, name):
        if name in self.methods:
            return self.methods[name]
        return self.parent.find_method(name) if self.parent else None

    def is_subtype_of(self, other):
        node = self
        while node is not None:
            if node is other:
                return True
            node = node.parent
        return False

    def __repr__(self):
        return f"<type {self.name}>"


class Instance:
    __slots__ = ("type", "fields")

    def __init__(self, type_, fields):
        self.type = type_
        self.fields = fields

    def __eq__(self, other):
        return (isinstance(other, Instance) and other.type is self.type
                and other.fields == self.fields)

    def __hash__(self):
        return hash((id(self.type), tuple(sorted(self.fields.items(), key=lambda kv: kv[0]))))

    def __repr__(self):
        return show(self, quote=True)


class Future:
    """Result of calling an `async fun`. Backed by a thread pool."""

    __slots__ = ("_future", "label")

    def __init__(self, future, label="task"):
        self._future = future
        self.label = label

    def done(self):
        return self._future.done()

    def result(self, timeout=None):
        return self._future.result(timeout)

    def __repr__(self):
        state = "done" if self.done() else "running"
        return f"<task {self.label} ({state})>"


class SheError:
    """A catchable error value inside SHE. `throw` and `catch` speak this."""

    __slots__ = ("kind", "message", "data")

    def __init__(self, kind, message, data=None):
        self.kind = kind
        self.message = message
        self.data = data if data is not None else {}

    def __repr__(self):
        return f"<{self.kind}: {self.message}>"


# --- type names -------------------------------------------------------------

BUILTIN_TYPE_NAMES = {
    "number", "text", "bool", "list", "map", "function", "range",
    "nothing", "any", "type", "module", "error", "task",
}


def type_name(value):
    if value is None:
        return "nothing"
    if value is True or value is False:
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "map"
    if isinstance(value, Range):
        return "range"
    if isinstance(value, (Function, Builtin)):
        return "function"
    if isinstance(value, Type):
        return "type"
    if isinstance(value, Instance):
        return value.type.name
    if isinstance(value, Module):
        return "module"
    if isinstance(value, SheError):
        return "error"
    if isinstance(value, Future):
        return "task"
    if isinstance(value, (set, frozenset)):
        return "set"
    if isinstance(value, bytes):
        return "bytes"
    return type(value).__name__


def type_label(t):
    if isinstance(t, list):
        return " or ".join(type_label(x) for x in t)
    return str(t)


def matches_type(value, declared, env=None):
    """Runtime check for a gradual type annotation. `declared` is str or list."""
    if declared is None or declared == "any":
        return True
    if isinstance(declared, list):
        return any(matches_type(value, d, env) for d in declared)
    if declared == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared == "bool":
        return isinstance(value, bool)
    if declared == "text":
        return isinstance(value, str)
    if declared == "list":
        return isinstance(value, list)
    if declared == "map":
        return isinstance(value, dict)
    if declared == "function":
        return isinstance(value, (Function, Builtin))
    if declared == "range":
        return isinstance(value, Range)
    if declared == "nothing":
        return value is None
    if declared == "error":
        return isinstance(value, SheError)
    if declared == "task":
        return isinstance(value, Future)
    if declared == "type":
        return isinstance(value, Type)
    # A user type name.
    if env is not None:
        target = env.get_quiet(declared)
        if isinstance(target, Type):
            return isinstance(value, Instance) and value.type.is_subtype_of(target)
    return type_name(value) == declared


# --- truth, equality, display -----------------------------------------------

def truthy(value):
    """SHE truthiness: nothing/false/0/""/[]/{} are false. Everything else is true."""
    if value is None or value is False:
        return False
    if value is True:
        return True
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (str, list, dict, set, bytes)):
        return len(value) > 0
    if isinstance(value, Range):
        return len(value) > 0
    return True


def equal(a, b):
    """Structural equality. `1 == 1.0` is true; `1 == true` is not."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if type_name(a) != type_name(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, Instance):
        return a.type is b.type and all(equal(a.fields.get(k), b.fields.get(k))
                                        for k in set(a.fields) | set(b.fields))
    return a == b


def number_text(value):
    """Print 5.0 as 5 — beginners should never see a stray `.0`."""
    if isinstance(value, float):
        if value != value:
            return "nan"
        if value == math.inf:
            return "infinity"
        if value == -math.inf:
            return "-infinity"
        if value.is_integer() and abs(value) < 1e16:
            return str(int(value))
        return repr(value)
    return str(value)


def show(value, quote=False, seen=None):
    """Human-readable text for a value. `quote` adds quotes around text."""
    seen = seen if seen is not None else set()
    if value is None:
        return "nothing"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return number_text(value)
    if isinstance(value, str):
        if not quote:
            return value
        body = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{body}"'
    if id(value) in seen:
        return "..."
    if isinstance(value, (list, dict, Instance, set)):
        seen = seen | {id(value)}
    if isinstance(value, list):
        return "[" + ", ".join(show(v, True, seen) for v in value) + "]"
    if isinstance(value, (set, frozenset)):
        if not value:
            return "set()"
        return "{" + ", ".join(sorted(show(v, True, seen) for v in value)) + "}"
    if isinstance(value, dict):
        if not value:
            return "{}"
        inner = ", ".join(f"{show(k, True, seen)}: {show(v, True, seen)}"
                          for k, v in value.items())
        return "{" + inner + "}"
    if isinstance(value, Range):
        return repr(value)
    if isinstance(value, Instance):
        inner = ", ".join(f"{k}: {show(v, True, seen)}" for k, v in value.fields.items())
        return f"{value.type.name}({inner})"
    if isinstance(value, SheError):
        return f"{value.kind}: {value.message}"
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    return repr(value)


def to_number(value, what="value"):
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                raise TypeErr(f"`{value}` is not a number",
                              hint="numbers look like 42 or 3.14.")
    raise TypeErr(f"a {type_name(value)} is not a number", hint=None)


def iterate(value):
    """Everything SHE can loop over."""
    if isinstance(value, dict):
        return list(value.items())
    if isinstance(value, (list, str, set, frozenset, bytes)):
        return list(value)
    if isinstance(value, Range):
        return list(value)
    if isinstance(value, Instance):
        return list(value.fields.items())
    raise TypeErr(f"a {type_name(value)} is not something you can loop over",
                  hint="you can loop over a list, text, map, or range like `1..10`.")
