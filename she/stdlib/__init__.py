"""The SHE standard library.

A module is just a dict of Python callables. `wrap` turns a plain function into
something SHE can call; if a function's first parameter is named `interp` it is
handed the interpreter (needed for callbacks and for capability checks).

Modules are built lazily, so a program that never touches `http` never imports
urllib, and one that never touches `crypto` never imports kaalka.
"""

import inspect

from ..errors import ImportErr, TypeErr, ValueErr, did_you_mean
from ..values import (
    Builtin,
    Function,
    Instance,
    Module,
    Range,
    Type,
    iterate,
    show,
    to_number,
    truthy,
    type_name,
)
from ..values import SheError as ErrorValue

# name -> callable returning {export name: python callable}
REGISTRY = {}
DOCS = {}
_CACHE = {}


def register(name, doc=""):
    def decorate(builder):
        REGISTRY[name] = builder
        DOCS[name] = doc
        return builder
    return decorate


def wrap(fn, name=None, module=None):
    """Adapt a plain Python function into a SHE Builtin."""
    if isinstance(fn, Builtin):
        return fn
    name = name or getattr(fn, "she_name", None) or fn.__name__.rstrip("_")
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        params = []
    wants_interp = bool(params) and params[0].name == "interp"
    positional = list(params[1 if wants_interp else 0:])
    required = sum(1 for p in positional
                   if p.default is inspect.Parameter.empty
                   and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD))
    takes_varargs = any(p.kind is p.VAR_POSITIONAL for p in positional)
    maximum = None if takes_varargs else len(positional)
    labels = [p.name for p in positional]

    def call(interp, args, kwargs, node):
        total = len(args) + len(kwargs)
        if total < required or (maximum is not None and len(args) > maximum):
            shape = ", ".join(
                label if i < required else label + " = ..."
                for i, label in enumerate(labels))
            raise TypeErr(
                f"`{name}` takes {describe_arity(required, maximum)}, but got {total}",
                node.pos, node.end, hint=f"it is called like `{name}({shape})`.")
        try:
            if wants_interp:
                return fn(interp, *args, **kwargs)
            return fn(*args, **kwargs)
        except TypeError as exc:
            if "positional argument" in str(exc) or "keyword argument" in str(exc):
                raise TypeErr(f"`{name}` was called the wrong way: {exc}",
                              node.pos, node.end)
            raise

    return Builtin(name, call, doc=(fn.__doc__ or "").strip(),
                   arity=required, module=module)


def describe_arity(required, maximum):
    if maximum is None:
        return f"at least {required} value{'s' if required != 1 else ''}"
    if required == maximum:
        return f"{required} value{'s' if required != 1 else ''}"
    return f"between {required} and {maximum} values"


def build(name, exports, doc=""):
    return Module(name, {k: wrap(v, k, name) for k, v in exports.items()}, doc=doc)


def load_module(interp, name, node=None):
    """Resolve `import <name>`. Caches per process."""
    if name in _CACHE:
        return _CACHE[name]
    if name not in REGISTRY:
        raise ImportErr(
            f"there is no module called `{name}`",
            node.pos if node else None, node.end if node else None,
            hint=did_you_mean(name, REGISTRY)
                 or "built-in modules: " + ", ".join(sorted(REGISTRY)) + ".")
    module = build(name, REGISTRY[name](), DOCS.get(name, ""))
    _CACHE[name] = module
    return module


def module_names():
    return sorted(REGISTRY)


# --- method-call syntax on plain values -------------------------------------
# `"hi".upper()` and `text.upper("hi")` are the same call. The table is built
# from the stdlib modules themselves so the two spellings can never drift.

_METHOD_TABLES = None
_TABLE_SOURCES = {
    "text": str,
    "list": list,
    "maps": dict,
}
PROPERTIES = {"length", "count", "size"}


def method_tables():
    global _METHOD_TABLES
    if _METHOD_TABLES is None:
        _METHOD_TABLES = {}
        for module_name, py_type in _TABLE_SOURCES.items():
            exports = REGISTRY[module_name]()
            _METHOD_TABLES[py_type] = {k: wrap(v, k, module_name)
                                       for k, v in exports.items()}
    return _METHOD_TABLES


def member_of(obj, name):
    """Look up `obj.name`. Returns a bound Builtin, a property value, or None."""
    if name in PROPERTIES:
        if isinstance(obj, (str, list, dict, set, frozenset, bytes)):
            return len(obj)
        if isinstance(obj, Range):
            return len(obj)
    if isinstance(obj, (Function, Builtin)):
        if name == "name":
            return obj.name
        if name == "doc":
            return obj.doc or ""
    if isinstance(obj, Range):
        if name in ("start", "stop", "step"):
            return getattr(obj, name)
        if name == "to_list":
            return bind(wrap(lambda r: list(r), "to_list", "range"), obj)
    table = method_tables().get(type(obj))
    if table is None and isinstance(obj, bool):
        table = None
    if table is None:
        return None
    fn = table.get(name)
    if fn is None:
        return None
    return bind(fn, obj)


def bind(builtin, receiver):
    """Turn `text.upper(s)` into `s.upper()`."""
    def call(interp, args, kwargs, node):
        return builtin.fn(interp, [receiver] + list(args), kwargs, node)
    return Builtin(builtin.name, call, builtin.doc, builtin.arity, builtin.module)


def members_for(obj):
    table = method_tables().get(type(obj))
    names = set(PROPERTIES) if isinstance(obj, (str, list, dict)) else set()
    if table:
        names |= set(table)
    return names


# --- core: available without importing anything -----------------------------

# Modules you can use without importing. They are pure computation, so having
# them always present costs nothing. Anything that can touch the outside world
# (fs, http, os, crypto, web) must be imported on purpose.
ALWAYS_AVAILABLE = ("text", "list", "math", "json", "re", "time", "random")


def install_core(interp):
    from . import basics, compute, data, security, system  # noqa: F401  (registers modules)

    env = interp.globals
    for name, fn in core_exports().items():
        env.declare(name, wrap(fn, name, "core"), mutable=False)
    env.declare("infinity", float("inf"), mutable=False)
    env.declare("nan", float("nan"), mutable=False)
    for name in ALWAYS_AVAILABLE:
        env.declare(name, load_module(interp, name), mutable=False)


def core_exports():
    return {
        "print": _print,
        "show": _show,
        "to_text": _text,
        "to_number": _number,
        "to_bool": _boolean,
        "to_whole": _whole,
        "to_list": _list_of,
        "to_map": _map_of,
        "number": _number,
        "boolean": _boolean,
        "whole": _whole,
        "len": _len,
        "length": _len,
        "type_of": type_name,
        "range": _range,
        "keys": _keys,
        "values": _values,
        "items": _items,
        "min": _min,
        "max": _max,
        "sum": _sum,
        "abs": _abs,
        "round": _round,
        "sorted": _sorted,
        "reversed": _reversed,
        "enumerate": _enumerate,
        "zip": _zip,
        "map": _map,
        "filter": _filter,
        "reduce": _reduce,
        "each": _each,
        "any": _any,
        "all": _all,
        "count": _count,
        "first": _first,
        "last": _last,
        "contains": _contains,
        "empty?": _empty,
        "input": _input,
        "error": _error,
        "help": _help,
        "modules": _modules,
        "exit": _exit,
    }


# --- implementations --------------------------------------------------------

def _print(interp, *values):
    """Write values on one line, separated by spaces."""
    interp.write(" ".join(interp.to_text(v) for v in values) + "\n")


def _show(interp, value):
    """Text for a value, with quotes around text so it is unambiguous."""
    return show(value, quote=True)


def _text(interp, value):
    """Convert anything to text."""
    return interp.to_text(value)


def _number(value):
    """Convert text or a boolean to a number."""
    return to_number(value)


def _boolean(value):
    """Convert anything to true/false using SHE truthiness."""
    return truthy(value)


def _whole(value):
    """Round toward zero and return a whole number."""
    return int(to_number(value))


def _len(value):
    """How many items are in a list, map, text or range."""
    if isinstance(value, (str, list, dict, set, frozenset, bytes)):
        return len(value)
    if isinstance(value, Range):
        return len(value)
    if isinstance(value, Instance):
        return len(value.fields)
    raise TypeErr(f"a {type_name(value)} has no length",
                  hint="length works on text, lists, maps and ranges.")


def _range(start, stop=None, step=1):
    """`range(5)` is 0 up to 4. `range(1, 10)` is 1 up to 9."""
    if stop is None:
        start, stop = 0, start
    return Range(start, stop, step, inclusive=False)


def _list_of(value):
    """Turn anything iterable into a list."""
    return iterate(value)


def _map_of(pairs):
    """Build a map from a list of [key, value] pairs."""
    out = {}
    for pair in iterate(pairs):
        items = list(pair) if isinstance(pair, (list, tuple)) else None
        if not items or len(items) != 2:
            raise ValueErr("map_of needs a list of [key, value] pairs")
        out[items[0]] = items[1]
    return out


def _keys(value):
    """The keys of a map, or the field names of a value."""
    if isinstance(value, dict):
        return list(value.keys())
    if isinstance(value, Instance):
        return list(value.fields.keys())
    raise TypeErr(f"a {type_name(value)} has no keys")


def _values(value):
    """The values of a map, or the field values of a value."""
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, Instance):
        return list(value.fields.values())
    raise TypeErr(f"a {type_name(value)} has no values")


def _items(value):
    """A map as a list of [key, value] pairs."""
    if isinstance(value, dict):
        return [[k, v] for k, v in value.items()]
    if isinstance(value, Instance):
        return [[k, v] for k, v in value.fields.items()]
    raise TypeErr(f"a {type_name(value)} has no items")


def _sequence(value, what):
    try:
        return iterate(value)
    except TypeErr:
        raise TypeErr(f"`{what}` needs a list, text, map or range, "
                      f"not a {type_name(value)}")


def _numeric(items, what):
    for item in items:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise TypeErr(f"`{what}` works on numbers, but found a {type_name(item)}")
    return items


def _min(interp, value, *rest):
    """Smallest value in a list, or of the values given."""
    items = list(value) + list(rest) if rest else _sequence(value, "min")
    if not items:
        raise ValueErr("`min` needs at least one value")
    if all(isinstance(i, str) for i in items):
        return min(items)
    return min(_numeric(items, "min"))


def _max(interp, value, *rest):
    """Largest value in a list, or of the values given."""
    items = list(value) + list(rest) if rest else _sequence(value, "max")
    if not items:
        raise ValueErr("`max` needs at least one value")
    if all(isinstance(i, str) for i in items):
        return max(items)
    return max(_numeric(items, "max"))


def _sum(value, start=0):
    """Add up every number in a list or range."""
    return sum(_numeric(_sequence(value, "sum"), "sum"), start)


def _abs(value):
    """Distance from zero."""
    return abs(to_number(value))


def _round(value, places=0):
    """Round to the given number of decimal places."""
    result = round(to_number(value), int(places))
    return int(result) if places == 0 else result


def _sorted(interp, value, by=None, descending=False):
    """Sorted copy. Pass `by` to sort on a computed value."""
    items = _sequence(value, "sorted")
    if by is not None:
        return sorted(items, key=lambda item: interp.call_value(by, [item]),
                      reverse=truthy(descending))
    if all(isinstance(i, str) for i in items):
        return sorted(items, reverse=truthy(descending))
    return sorted(_numeric(items, "sorted"), reverse=truthy(descending))


def _reversed(value):
    """Reversed copy of a list or text."""
    if isinstance(value, str):
        return value[::-1]
    return list(reversed(_sequence(value, "reversed")))


def _enumerate(value, start=0):
    """Pairs of [position, item]."""
    return [[i + int(start), v] for i, v in enumerate(_sequence(value, "enumerate"))]


def _zip(*sequences):
    """Line up several lists into a list of groups."""
    lists = [_sequence(s, "zip") for s in sequences]
    return [list(group) for group in zip(*lists)]


def _map(interp, value, fn):
    """Apply a function to every item."""
    return [interp.call_value(fn, [item]) for item in _sequence(value, "map")]


def _filter(interp, value, fn):
    """Keep only the items the function says true for."""
    return [item for item in _sequence(value, "filter")
            if truthy(interp.call_value(fn, [item]))]


def _reduce(interp, value, fn, start=None):
    """Fold a list down to a single value."""
    items = _sequence(value, "reduce")
    if start is None:
        if not items:
            raise ValueErr("`reduce` on an empty list needs a starting value")
        total, items = items[0], items[1:]
    else:
        total = start
    for item in items:
        total = interp.call_value(fn, [total, item])
    return total


def _each(interp, value, fn):
    """Run a function for every item, keeping nothing."""
    for item in _sequence(value, "each"):
        interp.call_value(fn, [item])
    return None


def _any(interp, value, fn=None):
    """True if any item is true (or passes the function)."""
    items = _sequence(value, "any")
    if fn is None:
        return any(truthy(i) for i in items)
    return any(truthy(interp.call_value(fn, [i])) for i in items)


def _all(interp, value, fn=None):
    """True if every item is true (or passes the function)."""
    items = _sequence(value, "all")
    if fn is None:
        return all(truthy(i) for i in items)
    return all(truthy(interp.call_value(fn, [i])) for i in items)


def _count(interp, value, fn=None):
    """How many items match, or how many there are."""
    items = _sequence(value, "count")
    if fn is None:
        return len(items)
    if isinstance(fn, (Function, Builtin)):
        return sum(1 for i in items if truthy(interp.call_value(fn, [i])))
    from ..values import equal
    return sum(1 for i in items if equal(i, fn))


def _first(value, fallback=None):
    """The first item, or a fallback when empty."""
    items = _sequence(value, "first")
    return items[0] if items else fallback


def _last(value, fallback=None):
    """The last item, or a fallback when empty."""
    items = _sequence(value, "last")
    return items[-1] if items else fallback


def _contains(interp, container, item):
    """True if the container holds the item."""
    from ..values import equal
    if isinstance(container, str):
        return str(item) in container
    if isinstance(container, dict):
        return item in container
    return any(equal(item, x) for x in _sequence(container, "contains"))


def _empty(value):
    """True when there is nothing in it."""
    return not truthy(value) if not isinstance(value, (int, float)) else False


def _input(interp, prompt=""):
    """Read a line of text from whoever is running the program."""
    text = interp.to_text(prompt)
    if text and not text.endswith((" ", "\n")):
        text += " "
    try:
        return interp.ask_fn(text)
    except EOFError:
        return ""


def _assert(interp, condition, message="the check failed"):
    """Stop the program unless the condition holds."""
    if not truthy(condition):
        from ..errors import AssertErr
        raise AssertErr(interp.to_text(message))
    return None


def _error(kind, message=None, data=None):
    """Build an error value you can `throw`."""
    if message is None:
        kind, message = "Error", kind
    return ErrorValue(str(kind), str(message), data if isinstance(data, dict) else {})


def _help(interp, thing=None):
    """Describe a value, function, module or type."""
    if thing is None:
        interp.write("SHE — modules: " + ", ".join(module_names()) + "\n")
        interp.write("Try help(math), or read the docs at https://ni-sh-a-char.github.io/SHE/\n")
        return None
    if isinstance(thing, Module):
        interp.write(f"module {thing.name}\n")
        if thing.doc:
            interp.write(f"  {thing.doc}\n")
        for key in sorted(thing.values):
            value = thing.values[key]
            doc = (getattr(value, "doc", "") or "").split("\n")[0]
            interp.write(f"  {key:<18} {doc}\n")
        return None
    if isinstance(thing, Type):
        fields = ", ".join(f[0] for f in thing.all_fields())
        interp.write(f"type {thing.name} has {fields}\n")
        if thing.doc:
            interp.write(f"  {thing.doc}\n")
        for _, method in sorted(thing.methods.items()):
            interp.write(f"  {method.signature()}\n")
        return None
    if isinstance(thing, (Function, Builtin)):
        interp.write(thing.signature() + "\n")
        if getattr(thing, "doc", None):
            interp.write("  " + thing.doc.replace("\n", "\n  ") + "\n")
        return None
    interp.write(f"{type_name(thing)}: {show(thing, quote=True)}\n")
    names = sorted(members_for(thing))
    if names:
        interp.write("  you can use: " + ", ".join(names) + "\n")
    return None


def _modules():
    """Every module you can import."""
    return module_names()


def _exit(code=0):
    """Stop the program."""
    raise SystemExit(int(code))
