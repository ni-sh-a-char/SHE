"""SHE AST nodes.

Deliberately dumb data holders. Every node carries `pos`/`end` so runtime errors
can point at the exact source that caused them.
"""


class Node:
    __slots__ = ("pos", "end")

    def __init__(self, pos=None, end=None):
        self.pos = pos
        self.end = end


def _node(name, *fields):
    """Make a Node subclass with the given slots. Keeps this file readable."""
    slots = tuple(fields)

    def __init__(self, *args, pos=None, end=None):
        Node.__init__(self, pos, end)
        for field, value in zip(slots, args):
            setattr(self, field, value)

    def __repr__(self):
        inner = ", ".join(f"{f}={getattr(self, f, None)!r}" for f in slots)
        return f"{name}({inner})"

    return type(name, (Node,), {"__slots__": slots, "__init__": __init__,
                                "__repr__": __repr__, "_fields": slots})


# --- literals & names -------------------------------------------------------
Num = _node("Num", "value")
Str = _node("Str", "parts")            # parts: list[str | Node]
Bool = _node("Bool", "value")
Nothing = _node("Nothing")
ListLit = _node("ListLit", "items")     # items: list[Node | Spread]
MapLit = _node("MapLit", "pairs")       # pairs: list[(Node key, Node value) | Spread]
Spread = _node("Spread", "value")       # ...xs inside a list/map/call
Name = _node("Name", "name")
Range = _node("Range", "start", "stop", "step", "inclusive")

# --- expressions ------------------------------------------------------------
Unary = _node("Unary", "op", "operand")
Binary = _node("Binary", "op", "left", "right")
Logical = _node("Logical", "op", "left", "right")   # and / or, short-circuit
Compare = _node("Compare", "op", "left", "right")
Call = _node("Call", "callee", "args", "kwargs")
Member = _node("Member", "obj", "name", "safe")     # safe=True for `?.`
Index = _node("Index", "obj", "key")
Slice = _node("Slice", "obj", "start", "stop")
Lambda = _node("Lambda", "params", "body", "is_expr", "is_async")
Pipe = _node("Pipe", "left", "right")
Coalesce = _node("Coalesce", "left", "right")       # ??
IfExpr = _node("IfExpr", "cond", "then", "otherwise")
Await = _node("Await", "value")
Ask = _node("Ask", "prompt")
MatchExpr = _node("MatchExpr", "subject", "cases")  # cases: list[MatchCase]
MatchCase = _node("MatchCase", "pattern", "guard", "body", "is_expr")

# --- patterns (match / destructuring) --------------------------------------
PWild = _node("PWild")                              # _
PBind = _node("PBind", "name")                      # n
PLit = _node("PLit", "value")                       # 1, "x", true
PList = _node("PList", "items", "rest")             # [a, b, ...rest]
PMap = _node("PMap", "pairs", "rest")               # {name: n, ...rest}
PType = _node("PType", "name", "args", "fields")    # Point(x, y) / Point{x: a}
POr = _node("POr", "options")                       # 1 | 2 | 3
PRange = _node("PRange", "start", "stop", "inclusive")

# --- statements -------------------------------------------------------------
Program = _node("Program", "body")
Block = _node("Block", "body")
Let = _node("Let", "target", "value", "mutable", "type_")
Assign = _node("Assign", "target", "value", "op")   # op: None | "+" | "-" | ...
ExprStmt = _node("ExprStmt", "value")
Say = _node("Say", "values", "end")
If = _node("If", "cond", "then", "otherwise")
While = _node("While", "cond", "body")
RepeatUntil = _node("RepeatUntil", "body", "cond")
ForEach = _node("ForEach", "targets", "iterable", "body")
ForRange = _node("ForRange", "name", "range", "body")
Break = _node("Break")
Skip = _node("Skip")
Return = _node("Return", "value")
FunDef = _node("FunDef", "name", "params", "body", "is_expr", "is_async", "doc", "returns")
Param = _node("Param", "name", "default", "type_", "variadic")
TypeDef = _node("TypeDef", "name", "fields", "methods", "parent", "doc")
Field = _node("Field", "name", "default", "type_")
Try = _node("Try", "body", "catches", "finally_")
Catch = _node("Catch", "name", "kinds", "body")
Throw = _node("Throw", "value")
Import = _node("Import", "module", "alias", "names")   # names: list[(name, alias)]
Use = _node("Use", "path", "alias", "names")           # `use "./x.she" as x`
TestDef = _node("TestDef", "name", "body")
Expect = _node("Expect", "value", "op", "other", "message")
