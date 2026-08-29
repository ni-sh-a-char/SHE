"""SHE interpreter: a tree-walking evaluator.

Design notes:
  * Control flow (`return`/`break`/`skip`) uses Python exceptions rather than a
    threaded result object. It is far less code and much harder to get wrong.
  * Every operation that can fail carries the AST node so errors point at source.
  * All side-effecting capability (files, net, processes) goes through the
    Sandbox, never directly.
"""

import concurrent.futures
import sys

from . import ast as A
from .errors import (
    AssertErr,
    ImportErr,
    IndexErr,
    KeyErr,
    MathErr,
    NameErr,
    SheError,
    Thrown,
    TypeErr,
    ValueErr,
    did_you_mean,
)
from .sandbox import Sandbox
from .values import (
    Builtin,
    Function,
    Future,
    Instance,
    Module,
    Range,
    Type,
    equal,
    iterate,
    matches_type,
    show,
    truthy,
    type_label,
    type_name,
)
from .values import SheError as ErrorValue

MAX_PY_RECURSION = 8000


# --- control-flow signals ---------------------------------------------------

class _Return(Exception):
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value


class _Break(Exception):
    pass


class _Skip(Exception):
    pass


# --- scopes -----------------------------------------------------------------

class Env:
    __slots__ = ("values", "consts", "parent", "name")

    def __init__(self, parent=None, name="<scope>"):
        self.values = {}
        self.consts = set()
        self.parent = parent
        self.name = name

    def declare(self, name, value, mutable=True):
        self.values[name] = value
        if mutable:
            self.consts.discard(name)
        else:
            self.consts.add(name)

    def get_quiet(self, name):
        env = self
        while env is not None:
            if name in env.values:
                return env.values[name]
            env = env.parent
        return None

    def has(self, name):
        env = self
        while env is not None:
            if name in env.values:
                return True
            env = env.parent
        return False

    def get(self, name, node=None):
        env = self
        while env is not None:
            if name in env.values:
                return env.values[name]
            env = env.parent
        raise NameErr(
            f"`{name}` has not been defined yet",
            node.pos if node else None, node.end if node else None,
            hint=did_you_mean(name, self.visible_names())
                 or f"declare it first: `let {name} = ...`",
        )

    def assign(self, name, value, node=None):
        env = self
        while env is not None:
            if name in env.values:
                if name in env.consts:
                    raise TypeErr(
                        f"`{name}` was declared with `let`, so it cannot be changed",
                        node.pos if node else None, node.end if node else None,
                        hint=f"use `var {name} = ...` if it needs to change.",
                    )
                env.values[name] = value
                return
            env = env.parent
        raise NameErr(
            f"`{name}` has not been defined yet",
            node.pos if node else None, node.end if node else None,
            hint=did_you_mean(name, self.visible_names())
                 or f"declare it first: `var {name} = ...`",
        )

    def visible_names(self):
        names = set()
        env = self
        while env is not None:
            names |= set(env.values)
            env = env.parent
        return names

    def child(self, name="<block>"):
        return Env(self, name)


# --- the interpreter --------------------------------------------------------

class Interpreter:
    def __init__(self, sandbox=None, out=None, err=None, ask=None, file="<input>"):
        self.sandbox = sandbox or Sandbox.locked()
        self.out = out if out is not None else sys.stdout
        self.err = err if err is not None else sys.stderr
        self.ask_fn = ask or (lambda prompt: input(prompt))
        self.file = file
        self.globals = Env(name="<global>")
        self.stack = []
        self.module_cache = {}
        self.tests = []
        self.pool = None
        self.search_paths = []
        from .stdlib import install_core
        install_core(self)

    # --- entry points ------------------------------------------------------
    def run(self, source, file=None, env=None):
        from .parser import parse
        tree = parse(source, file or self.file)
        return self.execute(tree, env)

    def execute(self, tree, env=None):
        env = env or self.globals
        result = None
        for stmt in tree.body:
            result = self.exec(stmt, env)
        return result

    def shutdown(self):
        if self.pool is not None:
            self.pool.shutdown(wait=True)
            self.pool = None

    # --- dispatch ----------------------------------------------------------
    def exec(self, node, env):
        self.sandbox.tick()
        method = self._STMT.get(type(node))
        if method is None:
            return self.eval(node, env)
        return method(self, node, env)

    def eval(self, node, env):
        self.sandbox.tick()
        method = self._EXPR.get(type(node))
        if method is None:
            raise TypeErr(f"I do not know how to evaluate {type(node).__name__}",
                          node.pos, node.end)
        return method(self, node, env)

    def write(self, text):
        self.out.write(text)

    # --- statements --------------------------------------------------------
    def s_program(self, node, env):
        return self.execute(node, env)

    def s_block(self, node, env):
        result = None
        for stmt in node.body:
            result = self.exec(stmt, env)
        return result

    def s_expr(self, node, env):
        return self.eval(node.value, env)

    def s_let(self, node, env):
        value = self.eval(node.value, env)
        if node.type_ is not None and not matches_type(value, node.type_, env):
            raise TypeErr(
                f"this should be a {type_label(node.type_)}, "
                f"but it is a {type_name(value)}",
                node.value.pos, node.value.end,
                hint=f"either change the value, or drop the `: {type_label(node.type_)}`.",
            )
        self.bind_pattern(node.target, value, env, mutable=node.mutable, declare=True)
        return None

    def s_assign(self, node, env):
        target = node.target
        value = self.eval(node.value, env)
        if node.op is not None:
            current = self.eval(target, env)
            value = self.binary_op(node.op, current, value, node)
        if isinstance(target, A.Name):
            env.assign(target.name, value, node)
        elif isinstance(target, A.Member):
            obj = self.eval(target.obj, env)
            self.set_member(obj, target.name, value, node)
        elif isinstance(target, A.Index):
            obj = self.eval(target.obj, env)
            key = self.eval(target.key, env)
            self.set_index(obj, key, value, node)
        else:
            raise TypeErr("this cannot be assigned to", target.pos, target.end,
                          hint="you can assign to a name, `thing.field`, or `thing[key]`.")
        return None

    def s_say(self, node, env):
        parts = [self.to_text(self.eval(v, env)) for v in node.values]
        self.write(" ".join(parts) + node.end)
        return None

    def s_if(self, node, env):
        if truthy(self.eval(node.cond, env)):
            return self.exec_block(node.then, env)
        if node.otherwise is not None:
            return self.exec_block(node.otherwise, env)
        return None

    def exec_block(self, block, env):
        scope = env.child()
        return self.s_block(block, scope)

    def s_while(self, node, env):
        while truthy(self.eval(node.cond, env)):
            try:
                self.exec_block(node.body, env)
            except _Break:
                break
            except _Skip:
                continue
        return None

    def s_repeat(self, node, env):
        while True:
            try:
                self.exec_block(node.body, env)
            except _Break:
                break
            except _Skip:
                pass
            if truthy(self.eval(node.cond, env)):
                break
        return None

    def s_foreach(self, node, env):
        source = self.eval(node.iterable, env)
        try:
            items = iterate(source)
        except SheError as exc:
            exc.pos = exc.pos or node.iterable.pos
            exc.end = exc.end or node.iterable.end
            raise
        targets = node.targets
        for index, item in enumerate(items):
            scope = env.child()
            if len(targets) == 1:
                self.bind_pattern(targets[0], item, scope, mutable=True, declare=True)
            elif isinstance(source, dict) and len(targets) == 2:
                self.bind_pattern(targets[0], item[0], scope, mutable=True, declare=True)
                self.bind_pattern(targets[1], item[1], scope, mutable=True, declare=True)
            elif len(targets) == 2:
                self.bind_pattern(targets[0], index, scope, mutable=True, declare=True)
                self.bind_pattern(targets[1], item, scope, mutable=True, declare=True)
            else:
                values = item if isinstance(item, (list, tuple)) else [item]
                if len(values) != len(targets):
                    raise ValueErr(
                        f"expected {len(targets)} values to unpack, got {len(values)}",
                        node.pos, node.end)
                for target, value in zip(targets, values):
                    self.bind_pattern(target, value, scope, mutable=True, declare=True)
            try:
                self.s_block(node.body, scope)
            except _Break:
                break
            except _Skip:
                continue
        return None

    def s_break(self, node, env):
        raise _Break()

    def s_skip(self, node, env):
        raise _Skip()

    def s_return(self, node, env):
        raise _Return(self.eval(node.value, env) if node.value is not None else None)

    def s_fundef(self, node, env):
        fn = Function(node.name, node.params, node.body, node.is_expr, env,
                      node.is_async, node.doc, node.returns)
        env.declare(node.name, fn, mutable=True)
        return None

    def s_typedef(self, node, env):
        parent = None
        if node.parent:
            parent = env.get(node.parent, node)
            if not isinstance(parent, Type):
                raise TypeErr(f"`{node.parent}` is not a type", node.pos, node.end)
        methods = {}
        type_env = env.child(node.name)
        obj = Type(node.name,
                   [(f.name, f.default, f.type_) for f in node.fields],
                   methods, parent, node.doc)
        type_env.declare(node.name, obj, mutable=False)
        for member in node.methods:
            if isinstance(member, A.FunDef):
                methods[member.name] = Function(member.name, member.params, member.body,
                                                member.is_expr, type_env, member.is_async,
                                                member.doc, member.returns)
            else:
                self.exec(member, type_env)
        env.declare(node.name, obj, mutable=False)
        return None

    def s_try(self, node, env):
        try:
            try:
                self.exec_block(node.body, env)
            except Thrown as thrown:
                if not self.handle_catch(node, env, thrown.value, thrown):
                    raise
            except (_Return, _Break, _Skip):
                raise
            except SheError as exc:
                value = ErrorValue(exc.kind, exc.message,
                                   {"hint": exc.hint} if exc.hint else {})
                if not self.handle_catch(node, env, value, exc):
                    raise
        finally:
            if node.finally_ is not None:
                self.exec_block(node.finally_, env)
        return None

    def handle_catch(self, node, env, value, original):
        kind = value.kind if isinstance(value, ErrorValue) else type_name(value)
        for catch in node.catches:
            if catch.kinds and kind not in catch.kinds:
                continue
            scope = env.child()
            if catch.name:
                scope.declare(catch.name, value, mutable=True)
            self.s_block(catch.body, scope)
            return True
        return False

    def s_throw(self, node, env):
        value = self.eval(node.value, env)
        if isinstance(value, str):
            value = ErrorValue("Error", value)
        message = value.message if isinstance(value, ErrorValue) else show(value)
        raise Thrown(value, message, node.pos, node.end, trace=list(self.stack))

    def s_import(self, node, env):
        from .stdlib import load_module
        module = load_module(self, node.module, node)
        if node.names:
            for name, alias in node.names:
                if name not in module.values:
                    raise ImportErr(
                        f"`{node.module}` has no `{name}`", node.pos, node.end,
                        hint=did_you_mean(name, module.values)
                             or f"`{node.module}` provides: "
                                f"{', '.join(sorted(module.values)[:8])}...",
                    )
                env.declare(alias or name, module.values[name], mutable=False)
        else:
            env.declare(node.alias or node.module.split(".")[0], module, mutable=False)
        return None

    def s_use(self, node, env):
        module = self.load_file_module(node.path, node)
        if node.names:
            for name, alias in node.names:
                if name not in module.values:
                    raise ImportErr(f"`{node.path}` does not define `{name}`",
                                    node.pos, node.end,
                                    hint=did_you_mean(name, module.values))
                env.declare(alias or name, module.values[name], mutable=False)
        else:
            import os
            default = os.path.splitext(os.path.basename(node.path))[0]
            env.declare(node.alias or default, module, mutable=False)
        return None

    def load_file_module(self, path, node):
        import os
        candidates = []
        base = os.path.dirname(os.path.abspath(self.file)) if self.file != "<input>" else os.getcwd()
        for root in [base] + self.search_paths:
            candidates.append(os.path.normpath(os.path.join(root, path)))
            if not path.endswith(".she"):
                candidates.append(os.path.normpath(os.path.join(root, path + ".she")))
        for candidate in candidates:
            if candidate in self.module_cache:
                return self.module_cache[candidate]
            if os.path.isfile(candidate):
                self.sandbox.check_path(candidate, "read")
                with open(candidate, encoding="utf-8") as handle:
                    source = handle.read()
                module_env = Env(self.globals, name=path)
                saved_file = self.file
                self.file = candidate
                try:
                    from .parser import parse
                    self.execute(parse(source, candidate), module_env)
                finally:
                    self.file = saved_file
                module = Module(os.path.basename(candidate), dict(module_env.values),
                                path=candidate)
                self.module_cache[candidate] = module
                return module
        raise ImportErr(f"I could not find `{path}`", node.pos, node.end,
                        hint="the path is relative to the file doing the importing.")

    def s_test(self, node, env):
        self.tests.append((node, env))
        return None

    def s_expect(self, node, env):
        value = self.eval(node.value, env)
        if node.op is None:
            ok = truthy(value)
            detail = f"expected something true, got {show(value, True)}"
        else:
            other = self.eval(node.other, env)
            ok = self.compare(node.op, value, other, node)
            detail = (f"expected {show(value, True)} "
                      f"{'to be' if node.op in ('is', '==') else node.op} "
                      f"{show(other, True)}")
        if not ok:
            message = self.to_text(self.eval(node.message, env)) if node.message else detail
            raise AssertErr(message, node.pos, node.end)
        return None

    # --- expressions -------------------------------------------------------
    def e_num(self, node, env):
        return node.value

    def e_bool(self, node, env):
        return node.value

    def e_nothing(self, node, env):
        return None

    def e_str(self, node, env):
        if len(node.parts) == 1 and isinstance(node.parts[0], str):
            return node.parts[0]
        out = []
        for part in node.parts:
            out.append(part if isinstance(part, str)
                       else self.to_text(self.eval(part, env)))
        return "".join(out)

    def e_name(self, node, env):
        return env.get(node.name, node)

    def e_list(self, node, env):
        out = []
        for item in node.items:
            if isinstance(item, A.Spread):
                out.extend(iterate(self.eval(item.value, env)))
            else:
                out.append(self.eval(item, env))
        return out

    def e_map(self, node, env):
        out = {}
        for pair in node.pairs:
            if isinstance(pair, A.Spread):
                other = self.eval(pair.value, env)
                if not isinstance(other, dict):
                    raise TypeErr(f"you can only spread a map into a map, "
                                  f"not a {type_name(other)}", pair.pos, pair.end)
                out.update(other)
                continue
            key = self.eval(pair[0], env)
            if isinstance(key, (list, dict)):
                raise TypeErr(f"a {type_name(key)} cannot be a map key",
                              pair[0].pos, pair[0].end,
                              hint="keys have to be text, numbers or booleans.")
            out[key] = self.eval(pair[1], env)
        return out

    def e_range(self, node, env):
        start = self.eval(node.start, env)
        stop = self.eval(node.stop, env)
        step = self.eval(node.step, env) if node.step is not None else 1
        for value, source in ((start, node.start), (stop, node.stop)):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeErr(f"a range needs numbers, got a {type_name(value)}",
                              source.pos, source.end, hint="write it like `1..10`.")
        if step == 0:
            raise ValueErr("a range step cannot be 0", node.pos, node.end,
                           hint="a step of 0 would loop forever.")
        return Range(start, stop, step, node.inclusive)

    def e_unary(self, node, env):
        value = self.eval(node.operand, env)
        if node.op == "not":
            return not truthy(value)
        if node.op == "-":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeErr(f"you cannot negate a {type_name(value)}",
                              node.pos, node.end)
            return -value
        return value

    def e_binary(self, node, env):
        left = self.eval(node.left, env)
        right = self.eval(node.right, env)
        return self.binary_op(node.op, left, right, node)

    def e_logical(self, node, env):
        left = self.eval(node.left, env)
        if node.op == "and":
            return self.eval(node.right, env) if truthy(left) else left
        return left if truthy(left) else self.eval(node.right, env)

    def e_coalesce(self, node, env):
        left = self.eval(node.left, env)
        return self.eval(node.right, env) if left is None else left

    def e_compare(self, node, env):
        return self.compare(node.op, self.eval(node.left, env),
                            self.eval(node.right, env), node)

    def e_ifexpr(self, node, env):
        return self.eval(node.then if truthy(self.eval(node.cond, env))
                         else node.otherwise, env)

    def e_lambda(self, node, env):
        return Function(None, node.params, node.body, node.is_expr, env, node.is_async)

    def e_pipe(self, node, env):
        """`x |> f(a)` calls `f(x, a)`. Left-to-right reading order."""
        value = self.eval(node.left, env)
        right = node.right
        if isinstance(right, A.Call):
            callee = self.eval(right.callee, env)
            args = [value] + self.eval_args(right.args, env)
            kwargs = {k: self.eval(v, env) for k, v in right.kwargs.items()}
            return self.call(callee, args, kwargs, node)
        callee = self.eval(right, env)
        return self.call(callee, [value], {}, node)

    def e_await(self, node, env):
        value = self.eval(node.value, env)
        return self.await_value(value, node)

    def await_value(self, value, node):
        if isinstance(value, Future):
            try:
                return value.result()
            except SheError:
                raise
            except Exception as exc:  # noqa: BLE001 - surface worker failures cleanly
                raise ValueErr(f"the task failed: {exc}", node.pos, node.end)
        if isinstance(value, list) and all(isinstance(v, Future) for v in value) and value:
            return [self.await_value(v, node) for v in value]
        return value

    def e_ask(self, node, env):
        prompt = self.to_text(self.eval(node.prompt, env)) if node.prompt else ""
        if prompt and not prompt.endswith((" ", "\n")):
            prompt += " "
        try:
            return self.ask_fn(prompt)
        except EOFError:
            return ""

    def e_member(self, node, env):
        obj = self.eval(node.obj, env)
        if obj is None and node.safe:
            return None
        return self.get_member(obj, node.name, node)

    def e_index(self, node, env):
        obj = self.eval(node.obj, env)
        key = self.eval(node.key, env)
        return self.get_index(obj, key, node)

    def e_slice(self, node, env):
        obj = self.eval(node.obj, env)
        start = self.eval(node.start, env) if node.start is not None else None
        stop = self.eval(node.stop, env) if node.stop is not None else None
        if not isinstance(obj, (list, str)):
            raise TypeErr(f"you cannot slice a {type_name(obj)}", node.pos, node.end,
                          hint="slicing works on lists and text.")
        for v in (start, stop):
            if v is not None and (isinstance(v, bool) or not isinstance(v, int)):
                raise TypeErr("slice positions have to be whole numbers",
                              node.pos, node.end)
        return obj[start:stop]

    def e_call(self, node, env):
        callee = self.eval(node.callee, env)
        args = self.eval_args(node.args, env)
        kwargs = {k: self.eval(v, env) for k, v in node.kwargs.items()}
        return self.call(callee, args, kwargs, node)

    def eval_args(self, arg_nodes, env):
        args = []
        for arg in arg_nodes:
            if isinstance(arg, A.Spread):
                args.extend(iterate(self.eval(arg.value, env)))
            else:
                args.append(self.eval(arg, env))
        return args

    def e_match(self, node, env):
        subject = self.eval(node.subject, env)
        for case in node.cases:
            scope = env.child()
            if not self.match_pattern(case.pattern, subject, scope):
                continue
            if case.guard is not None and not truthy(self.eval(case.guard, scope)):
                continue
            if case.is_expr:
                return self.eval(case.body, scope)
            return self.s_block(case.body, scope)
        raise ValueErr(
            f"nothing in this `match` handles {show(subject, True)}",
            node.pos, node.end,
            hint="add `case _ -> ...` to cover everything else.",
        )

    # --- pattern matching --------------------------------------------------
    def match_pattern(self, pattern, value, env):
        kind = type(pattern)
        if kind is A.PWild:
            return True
        if kind is A.PBind:
            env.declare(pattern.name, value, mutable=True)
            return True
        if kind is A.PLit:
            return equal(self.eval(pattern.value, env), value)
        if kind is A.POr:
            return any(self.match_pattern(option, value, env) for option in pattern.options)
        if kind is A.PRange:
            start = self.eval(pattern.start, env)
            stop = self.eval(pattern.stop, env)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False
            return start <= value <= stop if pattern.inclusive else start <= value < stop
        if kind is A.PList:
            if not isinstance(value, list):
                return False
            if pattern.rest is None:
                if len(value) != len(pattern.items):
                    return False
            elif len(value) < len(pattern.items):
                return False
            for sub, item in zip(pattern.items, value):
                if not self.match_pattern(sub, item, env):
                    return False
            if pattern.rest is not None:
                env.declare(pattern.rest, value[len(pattern.items):], mutable=True)
            return True
        if kind is A.PMap:
            if not isinstance(value, dict):
                return False
            for key, sub in pattern.pairs:
                if key not in value or not self.match_pattern(sub, value[key], env):
                    return False
            if pattern.rest is not None:
                used = {k for k, _ in pattern.pairs}
                env.declare(pattern.rest, {k: v for k, v in value.items() if k not in used},
                            mutable=True)
            return True
        if kind is A.PType:
            target = env.get_quiet(pattern.name)
            if isinstance(target, Type):
                if not isinstance(value, Instance) or not value.type.is_subtype_of(target):
                    return False
                fields = value.fields
            elif pattern.name in ("number", "text", "bool", "list", "map",
                                  "function", "nothing", "error", "range"):
                if not matches_type(value, pattern.name, env):
                    return False
                if pattern.args:
                    return len(pattern.args) == 1 and \
                        self.match_pattern(pattern.args[0], value, env)
                return True
            elif isinstance(value, ErrorValue) and value.kind == pattern.name:
                fields = {"kind": value.kind, "message": value.message, **value.data}
            else:
                return False
            if pattern.args is not None:
                order = [name for name, _, _ in (target.all_fields()
                                                 if isinstance(target, Type) else [])]
                if len(pattern.args) > len(order):
                    return False
                for sub, name in zip(pattern.args, order):
                    if not self.match_pattern(sub, fields.get(name), env):
                        return False
                return True
            for name, sub in (pattern.fields or []):
                if name not in fields or not self.match_pattern(sub, fields[name], env):
                    return False
            return True
        return False

    def bind_pattern(self, pattern, value, env, mutable=True, declare=True):
        """Used by `let`/`var` and loop targets. Raises if the shape does not fit."""
        if isinstance(pattern, A.PBind):
            if declare:
                env.declare(pattern.name, value, mutable)
            else:
                env.assign(pattern.name, value)
            return
        scratch = Env(env)
        if not self.match_pattern(pattern, value, scratch):
            raise ValueErr(
                f"{show(value, True)} does not fit this pattern",
                pattern.pos, pattern.end,
                hint="the shapes have to line up, e.g. `let [a, b] = [1, 2]`.",
            )
        for name, bound in scratch.values.items():
            if declare:
                env.declare(name, bound, mutable)
            else:
                env.assign(name, bound)

    # --- operators ---------------------------------------------------------
    def binary_op(self, op, left, right, node):
        pos, end = node.pos, node.end
        if op == "+":
            if isinstance(left, str) or isinstance(right, str):
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                raise TypeErr(
                    f"you cannot add a {type_name(left)} and a {type_name(right)}",
                    pos, end,
                    hint='to build text use interpolation: "total: {value}".')
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            if isinstance(left, dict) and isinstance(right, dict):
                return {**left, **right}
            return self.arith(op, left, right, node)
        if op in ("-", "*", "/", "//", "%", "^"):
            if op == "*" and isinstance(left, list) and isinstance(right, int) \
                    and not isinstance(right, bool):
                return left * max(0, right)
            if op == "*" and isinstance(left, str) and isinstance(right, int) \
                    and not isinstance(right, bool):
                return left * max(0, right)
            if op == "-" and isinstance(left, list) and isinstance(right, list):
                return [x for x in left if not any(equal(x, y) for y in right)]
            return self.arith(op, left, right, node)
        raise TypeErr(f"I do not know the operator `{op}`", pos, end)

    def arith(self, op, left, right, node):
        pos, end = node.pos, node.end
        for value in (left, right):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                hint = None
                if isinstance(value, str):
                    hint = ("text and numbers do not mix. "
                            "Convert first with `number(value)`.")
                raise TypeErr(
                    f"you cannot use `{op}` with a {type_name(left)} "
                    f"and a {type_name(right)}", pos, end, hint=hint)
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise MathErr("you cannot divide by zero", pos, end,
                              hint="check the divisor before dividing.")
            result = left / right
            return int(result) if isinstance(left, int) and isinstance(right, int) \
                and result.is_integer() else result
        if op == "//":
            if right == 0:
                raise MathErr("you cannot divide by zero", pos, end)
            return left // right
        if op == "%":
            if right == 0:
                raise MathErr("you cannot take the remainder of a division by zero", pos, end)
            return left % right
        if op == "^":
            try:
                result = left ** right
            except (OverflowError, ZeroDivisionError):
                raise MathErr("that power is too large to work out", pos, end)
            if isinstance(result, complex):
                raise MathErr("that power has no real answer", pos, end,
                              hint="a negative number to a fractional power is not a number.")
            return result
        raise TypeErr(f"I do not know the operator `{op}`", pos, end)

    def compare(self, op, left, right, node):
        if op in ("is", "=="):
            return equal(left, right)
        if op in ("is not", "!="):
            return not equal(left, right)
        if op == "in":
            return self.contains(right, left, node)
        if op == "not in":
            return not self.contains(right, left, node)
        both_numbers = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                           for v in (left, right))
        both_text = isinstance(left, str) and isinstance(right, str)
        if not (both_numbers or both_text):
            raise TypeErr(
                f"you cannot compare a {type_name(left)} with a {type_name(right)} "
                f"using `{op}`", node.pos, node.end,
                hint="`<` and `>` work on numbers, or on text alphabetically.")
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        return left >= right

    def contains(self, container, item, node):
        if isinstance(container, str):
            if not isinstance(item, str):
                raise TypeErr(f"`in` on text needs text, not a {type_name(item)}",
                              node.pos, node.end)
            return item in container
        if isinstance(container, dict):
            return item in container
        if isinstance(container, Range):
            return item in container
        if isinstance(container, (list, set, frozenset)):
            return any(equal(item, x) for x in container)
        raise TypeErr(f"`in` does not work on a {type_name(container)}",
                      node.pos, node.end,
                      hint="use it with a list, text, map or range.")

    # --- members and indexing ---------------------------------------------
    def get_member(self, obj, name, node):
        from .stdlib import member_of, module_for_method
        if isinstance(obj, Module):
            if name in obj.values:
                return obj.values[name]
            raise NameErr(f"`{obj.name}` has no `{name}`", node.pos, node.end,
                          hint=did_you_mean(name, obj.values))
        if isinstance(obj, Instance):
            if name in obj.fields:
                return obj.fields[name]
            method = obj.type.find_method(name)
            if method is not None:
                return method.bind(obj)
            raise NameErr(
                f"a {obj.type.name} has no `{name}`", node.pos, node.end,
                hint=did_you_mean(name, list(obj.fields) + list(obj.type.methods))
                     or f"a {obj.type.name} has: {', '.join(obj.fields) or 'no fields'}.")
        if isinstance(obj, Type):
            if name in obj.methods:
                return obj.methods[name]
            if name == "name":
                return obj.name
            if name == "fields":
                return [f[0] for f in obj.all_fields()]
        if isinstance(obj, ErrorValue):
            if name == "kind":
                return obj.kind
            if name == "message":
                return obj.message
            if name in obj.data:
                return obj.data[name]
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        builtin = member_of(obj, name)
        if builtin is not None:
            return builtin
        if obj is None:
            raise TypeErr(f"there is nothing here, so `.{name}` has no meaning",
                          node.pos, node.end,
                          hint="use `?.` to skip safely when a value might be nothing.")
        hint = did_you_mean(name, member_names(obj))
        if hint is None:
            module_name = module_for_method(name)
            if module_name is not None:
                value_type = "map" if module_name == "maps" else module_name
                hint = (f"`{name}` is a {value_type} function; "
                        f"use it on a {value_type} value.")
        raise NameErr(f"a {type_name(obj)} has no `{name}`", node.pos, node.end,
                      hint=hint)

    def set_member(self, obj, name, value, node):
        if isinstance(obj, Instance):
            obj.fields[name] = value
            return
        if isinstance(obj, dict):
            obj[name] = value
            return
        if isinstance(obj, Module):
            raise TypeErr(f"`{obj.name}` is a module and cannot be changed",
                          node.pos, node.end)
        raise TypeErr(f"you cannot set `{name}` on a {type_name(obj)}",
                      node.pos, node.end)

    def get_index(self, obj, key, node):
        if isinstance(obj, (list, str)):
            if isinstance(key, bool) or not isinstance(key, int):
                raise TypeErr(
                    f"a {type_name(obj)} is indexed by whole numbers, "
                    f"not a {type_name(key)}", node.pos, node.end,
                    hint="did you want a map instead? maps use `{key: value}`.")
            if not obj:
                raise IndexErr(f"this {type_name(obj)} is empty, so there is no position {key}",
                               node.pos, node.end)
            if key < -len(obj) or key >= len(obj):
                raise IndexErr(
                    f"position {key} is outside this {type_name(obj)} "
                    f"(it holds {len(obj)} item{'s' if len(obj) != 1 else ''})",
                    node.pos, node.end,
                    hint=f"valid positions are 0 to {len(obj) - 1}, "
                         f"or -1 to -{len(obj)} counting from the end.")
            return obj[key]
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            raise KeyErr(f"this map has no key {show(key, True)}", node.pos, node.end,
                         hint=did_you_mean(str(key), [str(k) for k in obj])
                              or "use `map.get(m, key, fallback)` when a key may be missing.")
        if isinstance(obj, Range):
            items = list(obj)
            if isinstance(key, int) and -len(items) <= key < len(items):
                return items[key]
            raise IndexErr(f"position {key} is outside this range", node.pos, node.end)
        if isinstance(obj, Instance):
            if isinstance(key, str) and key in obj.fields:
                return obj.fields[key]
            raise KeyErr(f"a {obj.type.name} has no `{show(key)}`", node.pos, node.end)
        if obj is None:
            raise TypeErr("there is nothing here to index into", node.pos, node.end)
        raise TypeErr(f"you cannot index into a {type_name(obj)}", node.pos, node.end)

    def set_index(self, obj, key, value, node):
        if isinstance(obj, list):
            if isinstance(key, bool) or not isinstance(key, int):
                raise TypeErr(f"a list is indexed by whole numbers, not a {type_name(key)}",
                              node.pos, node.end)
            if key < -len(obj) or key >= len(obj):
                raise IndexErr(
                    f"position {key} is outside this list (it holds {len(obj)} items)",
                    node.pos, node.end,
                    hint="use `list.push(items, value)` to add to the end.")
            obj[key] = value
            return
        if isinstance(obj, dict):
            obj[key] = value
            return
        if isinstance(obj, Instance):
            obj.fields[str(key)] = value
            return
        if isinstance(obj, str):
            raise TypeErr("text cannot be changed in place", node.pos, node.end,
                          hint="build a new piece of text instead.")
        raise TypeErr(f"you cannot assign into a {type_name(obj)}", node.pos, node.end)

    # --- calling -----------------------------------------------------------
    def call(self, callee, args, kwargs, node):
        if isinstance(callee, Builtin):
            return self.call_builtin(callee, args, kwargs, node)
        if isinstance(callee, Type):
            return self.construct(callee, args, kwargs, node)
        if isinstance(callee, Function):
            if callee.is_async:
                return self.spawn(callee, args, kwargs, node)
            return self.invoke(callee, args, kwargs, node)
        raise TypeErr(
            f"a {type_name(callee)} is not something you can call",
            node.pos, node.end,
            hint="only functions and types can be called with `()`.")

    def call_builtin(self, callee, args, kwargs, node):
        try:
            return callee.fn(self, args, kwargs, node)
        except SheError as exc:
            if exc.pos is None:
                exc.pos, exc.end = node.pos, node.end
            if not exc.trace:
                exc.trace = list(self.stack)
            raise
        except (_Return, _Break, _Skip):
            raise
        except RecursionError:
            raise
        except Exception as exc:  # noqa: BLE001 - never leak a Python traceback
            raise ValueErr(f"`{callee.name}` failed: {exc}", node.pos, node.end,
                           trace=list(self.stack))

    def invoke(self, fn, args, kwargs, node):
        scope = self.prepare_scope(fn, args, kwargs, node)
        if len(self.stack) >= self.sandbox.max_depth:
            raise ValueErr(
                f"`{fn.name}` called itself {len(self.stack)} times without stopping",
                node.pos, node.end,
                hint="a recursive function needs a case that returns without recursing.")
        self.stack.append(f"{fn.name} ({node.pos.file}:{node.pos.line + 1})"
                          if node.pos else fn.name)
        try:
            if fn.is_expr:
                result = self.eval(fn.body, scope)
            else:
                try:
                    self.s_block(fn.body, scope)
                    result = None
                except _Return as ret:
                    result = ret.value
        except RecursionError:
            raise ValueErr(f"`{fn.name}` recursed too deeply", node.pos, node.end,
                           hint="add a base case that stops the recursion.")
        except SheError as exc:
            if not exc.trace:
                exc.trace = list(self.stack)
            raise
        finally:
            self.stack.pop()
        if fn.returns is not None and not matches_type(result, fn.returns, scope):
            raise TypeErr(
                f"`{fn.name}` should return a {type_label(fn.returns)}, "
                f"but returned a {type_name(result)}", node.pos, node.end)
        return result

    def prepare_scope(self, fn, args, kwargs, node):
        scope = Env(fn.env, fn.name)
        params = fn.params
        if fn.bound_self is not None:
            scope.declare("self", fn.bound_self, mutable=True)
            params = [p for p in params if p.name != "self"] \
                if params and params[0].name == "self" else params
        kwargs = dict(kwargs)
        index = 0
        for param in params:
            if param.variadic:
                scope.declare(param.name, list(args[index:]), mutable=True)
                index = len(args)
                continue
            if index < len(args):
                value = args[index]
                index += 1
                if param.name in kwargs:
                    raise TypeErr(f"`{param.name}` was given twice", node.pos, node.end)
            elif param.name in kwargs:
                value = kwargs.pop(param.name)
            elif param.default is not None:
                value = self.eval(param.default, scope)
            else:
                raise TypeErr(
                    f"`{fn.name}` needs `{param.name}`, but it was not given",
                    node.pos, node.end,
                    hint=f"it is called like `{fn.signature()}`.")
            if param.type_ is not None and not matches_type(value, param.type_, scope):
                raise TypeErr(
                    f"`{fn.name}` expects `{param.name}` to be a "
                    f"{type_label(param.type_)}, but got a {type_name(value)}",
                    node.pos, node.end,
                    hint=f"it is called like `{fn.signature()}`.")
            scope.declare(param.name, value, mutable=True)
        if index < len(args) and not any(p.variadic for p in params):
            extra = len(args) - index
            raise TypeErr(
                f"`{fn.name}` was given {extra} more "
                f"{'values' if extra > 1 else 'value'} than it takes",
                node.pos, node.end, hint=f"it is called like `{fn.signature()}`.")
        if kwargs:
            unknown = ", ".join(sorted(kwargs))
            raise TypeErr(f"`{fn.name}` does not take `{unknown}`", node.pos, node.end,
                          hint=f"it is called like `{fn.signature()}`.")
        return scope

    def construct(self, type_obj, args, kwargs, node):
        fields = {}
        declared = type_obj.all_fields()
        kwargs = dict(kwargs)
        for index, (name, default, declared_type) in enumerate(declared):
            if index < len(args):
                value = args[index]
            elif name in kwargs:
                value = kwargs.pop(name)
            elif default is not None:
                value = self.eval(default, self.globals)
            else:
                raise TypeErr(
                    f"a {type_obj.name} needs `{name}`", node.pos, node.end,
                    hint=f"build it like "
                         f"`{type_obj.name}({', '.join(f[0] for f in declared)})`.")
            if declared_type is not None and not matches_type(value, declared_type, self.globals):
                raise TypeErr(
                    f"`{name}` on a {type_obj.name} should be a "
                    f"{type_label(declared_type)}, but got a {type_name(value)}",
                    node.pos, node.end)
            fields[name] = value
        if len(args) > len(declared):
            raise TypeErr(
                f"a {type_obj.name} takes {len(declared)} "
                f"value{'s' if len(declared) != 1 else ''}, got {len(args)}",
                node.pos, node.end)
        if kwargs:
            raise TypeErr(f"a {type_obj.name} has no field `{', '.join(sorted(kwargs))}`",
                          node.pos, node.end,
                          hint=did_you_mean(next(iter(kwargs)), [f[0] for f in declared]))
        instance = Instance(type_obj, fields)
        setup = type_obj.find_method("setup")
        if setup is not None:
            self.invoke(setup.bind(instance), [], {}, node)
        return instance

    def spawn(self, fn, args, kwargs, node):
        """Run an `async fun` on a worker thread and hand back a task."""
        if self.pool is None:
            self.pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=8, thread_name_prefix="she")
        sub = Interpreter.__new__(Interpreter)
        sub.__dict__ = dict(self.__dict__) if hasattr(self, "__dict__") else {}
        future = self.pool.submit(self._run_async, fn, args, kwargs, node)
        return Future(future, fn.name)

    def _run_async(self, fn, args, kwargs, node):
        plain = Function(fn.name, fn.params, fn.body, fn.is_expr, fn.env,
                         False, fn.doc, fn.returns, fn.bound_self)
        return self.invoke(plain, args, kwargs, node)

    # --- helpers used by the stdlib ---------------------------------------
    def to_text(self, value):
        if isinstance(value, Instance):
            method = value.type.find_method("to_text")
            if method is not None:
                return str(self.invoke(method.bind(value), [], {}, _SYNTHETIC))
        return show(value)

    def call_value(self, callee, args, node=None):
        return self.call(callee, list(args), {}, node or _SYNTHETIC)


class _Synthetic:
    pos = None
    end = None


_SYNTHETIC = _Synthetic()


def member_names(obj):
    from .stdlib import members_for
    return members_for(obj)


Interpreter._STMT = {
    A.Program: Interpreter.s_program,
    A.Block: Interpreter.s_block,
    A.ExprStmt: Interpreter.s_expr,
    A.Let: Interpreter.s_let,
    A.Assign: Interpreter.s_assign,
    A.Say: Interpreter.s_say,
    A.If: Interpreter.s_if,
    A.While: Interpreter.s_while,
    A.RepeatUntil: Interpreter.s_repeat,
    A.ForEach: Interpreter.s_foreach,
    A.Break: Interpreter.s_break,
    A.Skip: Interpreter.s_skip,
    A.Return: Interpreter.s_return,
    A.FunDef: Interpreter.s_fundef,
    A.TypeDef: Interpreter.s_typedef,
    A.Try: Interpreter.s_try,
    A.Throw: Interpreter.s_throw,
    A.Import: Interpreter.s_import,
    A.Use: Interpreter.s_use,
    A.TestDef: Interpreter.s_test,
    A.Expect: Interpreter.s_expect,
}

Interpreter._EXPR = {
    A.Num: Interpreter.e_num,
    A.Bool: Interpreter.e_bool,
    A.Nothing: Interpreter.e_nothing,
    A.Str: Interpreter.e_str,
    A.Name: Interpreter.e_name,
    A.ListLit: Interpreter.e_list,
    A.MapLit: Interpreter.e_map,
    A.Range: Interpreter.e_range,
    A.Unary: Interpreter.e_unary,
    A.Binary: Interpreter.e_binary,
    A.Logical: Interpreter.e_logical,
    A.Coalesce: Interpreter.e_coalesce,
    A.Compare: Interpreter.e_compare,
    A.IfExpr: Interpreter.e_ifexpr,
    A.Lambda: Interpreter.e_lambda,
    A.Pipe: Interpreter.e_pipe,
    A.Await: Interpreter.e_await,
    A.Ask: Interpreter.e_ask,
    A.Member: Interpreter.e_member,
    A.Index: Interpreter.e_index,
    A.Slice: Interpreter.e_slice,
    A.Call: Interpreter.e_call,
    A.MatchExpr: Interpreter.e_match,
}
