"""SHE parser: tokens -> AST.

Recursive descent with a precedence-climbing expression parser. Blocks are
terminated by `end` (or by `else`/`case`/`catch`/`finally`, which close the
current block implicitly), so nothing depends on indentation.
"""

from . import ast as A
from .errors import SyntaxErr
from .lexer import tokenize

# Binary precedence, loosest first. Handled by climb().
PRECEDENCE = [
    ("??",),
    ("or",),
    ("and",),
    ("==", "!=", "is", "is not", "<", ">", "<=", ">=", "in", "not in"),
    ("..", "..<"),
    ("+", "-"),
    ("*", "/", "//", "%"),
    ("^",),
]
RIGHT_ASSOC = {"^"}

# Index of the comparison tier above, so `expect` can parse just below it.
COMPARE_LEVEL = 3

ASSIGN_OPS = {"+=": "+", "-=": "-", "*=": "*", "/=": "/", "//=": "//",
              "%=": "%", "^=": "^", "??=": "??"}

# Words that close a block without consuming `end`.
BLOCK_ENDERS = {"end", "else", "case", "catch", "finally", "until"}


class Parser:
    def __init__(self, tokens, file="<input>"):
        self.toks = tokens
        self.file = file
        self.i = 0

    # --- token plumbing ----------------------------------------------------
    @property
    def tok(self):
        return self.toks[self.i]

    def peek(self, n=1):
        return self.toks[min(self.i + n, len(self.toks) - 1)]

    def next(self):
        tok = self.toks[self.i]
        if self.i < len(self.toks) - 1:
            self.i += 1
        return tok

    def at(self, type_, value=None):
        return self.tok.is_(type_, value)

    def at_op(self, *ops):
        return self.tok.type == "OP" and self.tok.value in ops

    def at_kw(self, *words):
        return self.tok.type == "KEYWORD" and self.tok.value in words

    def accept(self, type_, value=None):
        if self.tok.is_(type_, value):
            return self.next()
        return None

    def expect(self, type_, value=None, what=None, hint=None):
        if self.tok.is_(type_, value):
            return self.next()
        want = what or (f"`{value}`" if value else type_.lower())
        raise self.error(f"expected {want}, but found {self.describe(self.tok)}", hint=hint)

    def describe(self, tok):
        if tok.type == "EOF":
            return "the end of the file"
        if tok.type == "NEWLINE":
            return "the end of the line"
        if tok.type == "STRING":
            return "some text"
        if tok.type == "NUMBER":
            return f"the number {tok.value}"
        return f"`{tok.value}`"

    def error(self, msg, tok=None, hint=None):
        tok = tok or self.tok
        return SyntaxErr(msg, tok.pos, tok.end, hint=hint)

    def skip_newlines(self):
        while self.tok.type == "NEWLINE":
            self.next()

    def end_of_statement(self, hint=None):
        if self.tok.type in ("NEWLINE", "EOF"):
            self.skip_newlines()
            return
        if self.at_kw(*BLOCK_ENDERS):
            return
        raise self.error(
            f"I did not expect {self.describe(self.tok)} here",
            hint=hint or "each statement goes on its own line (or separate them with `;`).",
        )

    # --- entry point -------------------------------------------------------
    def parse(self):
        body = self.statements(top_level=True)
        if self.tok.type != "EOF":
            if self.at_kw("end"):
                raise self.error("there is an extra `end` here",
                                 hint="remove it, or check that every `end` matches a block.")
            raise self.error(f"I did not expect {self.describe(self.tok)} here")
        pos = body[0].pos if body else self.tok.pos
        return A.Program(body, pos=pos, end=self.tok.end)

    def statements(self, top_level=False):
        body = []
        self.skip_newlines()
        while self.tok.type != "EOF" and not (not top_level and self.at_kw(*BLOCK_ENDERS)):
            body.append(self.statement())
            self.skip_newlines()
        return body

    def block(self, opener="block", allow_inline_then=False):
        """Parse statements until a block ender. Does not consume `end`."""
        if allow_inline_then and self.tok.type not in ("NEWLINE", "EOF"):
            stmt = self.statement()
            return A.Block([stmt], pos=stmt.pos, end=stmt.end)
        pos = self.tok.pos
        body = self.statements()
        if self.tok.type == "EOF":
            raise self.error(
                f"this {opener} is never closed",
                hint=f"add `end` to finish the {opener}.",
            )
        return A.Block(body, pos=pos, end=self.tok.end)

    def close_block(self, opener):
        if not self.accept("KEYWORD", "end"):
            raise self.error(f"expected `end` to close this {opener}, "
                             f"found {self.describe(self.tok)}",
                             hint=f"every `{opener}` needs a matching `end`.")

    # --- statements --------------------------------------------------------
    def statement(self):
        tok = self.tok
        if tok.type == "KEYWORD":
            handler = getattr(self, "stmt_" + tok.value, None)
            if handler is not None:
                return handler()
        return self.expression_statement()

    def stmt_let(self):
        return self.declaration(mutable=False)

    def stmt_var(self):
        return self.declaration(mutable=True)

    def declaration(self, mutable):
        start = self.next()
        target = self.binding_target()
        type_ = self.type_annotation()
        self.expect("OP", "=", what="`=`",
                    hint="declare with a value: `let name = \"World\"`.")
        value = self.expression()
        node = A.Let(target, value, mutable, type_, pos=start.pos, end=value.end)
        self.end_of_statement()
        return node

    def binding_target(self):
        """A name, or a destructuring pattern: `let [a, b] = xs`."""
        if self.at_op("["):
            return self.pattern()
        if self.at_op("{"):
            return self.pattern()
        tok = self.expect("NAME", what="a name",
                          hint="names start with a letter, like `total` or `user_name`.")
        return A.PBind(tok.value, pos=tok.pos, end=tok.end)

    def type_annotation(self):
        if not self.at_op(":"):
            return None
        self.next()
        return self.type_expr()

    def type_expr(self):
        parts = [self.type_atom()]
        while self.at_op("|"):
            self.next()
            parts.append(self.type_atom())
        return parts if len(parts) > 1 else parts[0]

    def type_atom(self):
        if self.at_kw("nothing"):
            self.next()
            return "nothing"
        tok = self.expect("NAME", what="a type name",
                          hint="built-in types are number, text, bool, list, map, function, any.")
        name = tok.value
        if self.at_op("["):  # list[number] — accepted, element type not enforced yet
            self.next()
            self.type_expr()
            self.expect("OP", "]", what="`]`")
        return name

    def stmt_say(self):
        start = self.next()
        values = []
        if self.tok.type not in ("NEWLINE", "EOF") and not self.at_kw(*BLOCK_ENDERS):
            values.append(self.expression())
            while self.accept("OP", ","):
                self.skip_newlines()
                values.append(self.expression())
        node = A.Say(values, "\n", pos=start.pos, end=self.tok.end)
        self.end_of_statement()
        return node

    def stmt_if(self):
        start = self.next()
        cond = self.expression()
        inline = bool(self.accept("KEYWORD", "then"))
        if inline and self.tok.type in ("NEWLINE", "EOF"):
            inline = False
        then = self.block("`if`", allow_inline_then=inline)
        if inline:
            return A.If(cond, then, None, pos=start.pos, end=then.end)

        otherwise = None
        if self.at_kw("else"):
            self.next()
            if self.at_kw("if"):
                nested = self.stmt_if_tail()
                otherwise = A.Block([nested], pos=nested.pos, end=nested.end)
                return A.If(cond, then, otherwise, pos=start.pos, end=nested.end)
            otherwise = self.block("`else`")
        self.close_block("if")
        node = A.If(cond, then, otherwise, pos=start.pos, end=self.toks[self.i - 1].end)
        self.end_of_statement()
        return node

    def stmt_if_tail(self):
        """`else if ...` — same as stmt_if but the caller already ate `else`."""
        start = self.next()
        cond = self.expression()
        inline = bool(self.accept("KEYWORD", "then"))
        if inline and self.tok.type in ("NEWLINE", "EOF"):
            inline = False
        then = self.block("`if`", allow_inline_then=inline)
        otherwise = None
        if not inline and self.at_kw("else"):
            self.next()
            if self.at_kw("if"):
                nested = self.stmt_if_tail()
                return A.If(cond, then, A.Block([nested], pos=nested.pos, end=nested.end),
                            pos=start.pos, end=nested.end)
            otherwise = self.block("`else`")
        if inline:
            return A.If(cond, then, None, pos=start.pos, end=then.end)
        self.close_block("if")
        return A.If(cond, then, otherwise, pos=start.pos, end=self.toks[self.i - 1].end)

    def stmt_while(self):
        start = self.next()
        cond = self.expression()
        inline = bool(self.accept("KEYWORD", "then")) and self.tok.type not in ("NEWLINE", "EOF")
        body = self.block("`while` loop", allow_inline_then=inline)
        if inline:
            return A.While(cond, body, pos=start.pos, end=body.end)
        self.close_block("while")
        node = A.While(cond, body, pos=start.pos, end=body.end)
        self.end_of_statement()
        return node

    def stmt_repeat(self):
        start = self.next()
        body = self.block("`repeat` loop")
        self.expect("KEYWORD", "until", what="`until`",
                    hint="a `repeat` block finishes with `until <condition>`.")
        cond = self.expression()
        node = A.RepeatUntil(body, cond, pos=start.pos, end=cond.end)
        self.end_of_statement()
        return node

    def stmt_for(self):
        start = self.next()
        self.accept("KEYWORD", "each")
        targets = [self.binding_target()]
        while self.accept("OP", ","):
            targets.append(self.binding_target())
        self.expect("KEYWORD", "in", what="`in`",
                    hint="loops read like English: `for each item in items`.")
        iterable = self.expression()
        if self.accept("KEYWORD", "by"):
            step = self.expression()
            if isinstance(iterable, A.Range):
                iterable.step = step
            else:
                raise self.error("`by` only makes sense with a range like `1..10`", hint=None)
        inline = bool(self.accept("KEYWORD", "then")) and self.tok.type not in ("NEWLINE", "EOF")
        body = self.block("`for` loop", allow_inline_then=inline)
        if inline:
            return A.ForEach(targets, iterable, body, pos=start.pos, end=body.end)
        self.close_block("for")
        node = A.ForEach(targets, iterable, body, pos=start.pos, end=body.end)
        self.end_of_statement()
        return node

    def stmt_break(self):
        tok = self.next()
        node = A.Break(pos=tok.pos, end=tok.end)
        self.end_of_statement()
        return node

    def stmt_skip(self):
        tok = self.next()
        node = A.Skip(pos=tok.pos, end=tok.end)
        self.end_of_statement()
        return node

    def stmt_return(self):
        tok = self.next()
        value = None
        if self.tok.type not in ("NEWLINE", "EOF") and not self.at_kw(*BLOCK_ENDERS):
            value = self.expression()
        node = A.Return(value, pos=tok.pos, end=(value.end if value else tok.end))
        self.end_of_statement()
        return node

    def stmt_async(self):
        start = self.next()
        if not self.at_kw("fun"):
            raise self.error("`async` has to be followed by `fun`",
                             hint="write `async fun name(...)`.")
        node = self.stmt_fun(is_async=True)
        node.pos = start.pos
        return node

    def stmt_fun(self, is_async=False):
        start = self.next()
        name_tok = self.expect("NAME", what="a function name",
                               hint="name it something you would say out loud: `fun greet(who)`.")
        params = self.params()
        returns = None
        if self.at_op("->") and self.peek().type == "NAME" and self.peek(2).type == "NEWLINE":
            pass  # `-> expr` shorthand where expr is a bare name; treat as body
        if self.at_op(":"):
            self.next()
            returns = self.type_expr()
        if self.at_op("->"):
            self.next()
            self.skip_newlines()
            body = self.expression()
            node = A.FunDef(name_tok.value, params, body, True, is_async, None, returns,
                            pos=start.pos, end=body.end)
            self.end_of_statement()
            return node
        body = self.block(f"function `{name_tok.value}`")
        self.close_block("fun")
        doc = self.extract_doc(body)
        node = A.FunDef(name_tok.value, params, body, False, is_async, doc, returns,
                        pos=start.pos, end=body.end)
        self.end_of_statement()
        return node

    @staticmethod
    def extract_doc(body):
        """A leading bare string in a body is its documentation."""
        if body.body and isinstance(body.body[0], A.ExprStmt):
            first = body.body[0].value
            if isinstance(first, A.Str) and all(isinstance(p, str) for p in first.parts):
                return "".join(first.parts).strip()
        return None

    def params(self):
        self.expect("OP", "(", what="`(`",
                    hint="even a function with no inputs needs `()`.")
        params = []
        self.skip_newlines()
        while not self.at_op(")"):
            variadic = False
            if self.at_op("..") and self.peek().is_("OP", "."):
                self.next()
                self.next()
                variadic = True
            name = self.expect("NAME", what="a parameter name")
            type_ = self.type_annotation()
            default = None
            if self.accept("OP", "="):
                default = self.expression()
            params.append(A.Param(name.value, default, type_, variadic,
                                  pos=name.pos, end=name.end))
            self.skip_newlines()
            if not self.accept("OP", ","):
                break
            self.skip_newlines()
        self.expect("OP", ")", what="`)`", hint="close the parameter list with `)`.")
        seen = set()
        for p in params:
            if p.name in seen:
                raise self.error(f"`{p.name}` is listed twice as a parameter", hint=None)
            seen.add(p.name)
        return params

    def stmt_type(self):
        start = self.next()
        name_tok = self.expect("NAME", what="a type name",
                               hint="type names are usually capitalised: `type Point has x, y`.")
        fields = []
        parent = None
        if self.accept("KEYWORD", "has"):
            while True:
                fname = self.expect("NAME", what="a field name")
                ftype = self.type_annotation()
                default = None
                if self.accept("OP", "="):
                    default = self.expression()
                fields.append(A.Field(fname.value, default, ftype, pos=fname.pos, end=fname.end))
                if not self.accept("OP", ","):
                    break
                self.skip_newlines()
        if self.accept("KEYWORD", "from"):
            parent = self.expect("NAME", what="the parent type name").value

        methods = []
        doc = None
        if self.tok.type == "NEWLINE" and self.opens_type_body():
            self.skip_newlines()
            while not self.at_kw("end") and self.tok.type != "EOF":
                if self.tok.type == "STRING" and doc is None and not methods:
                    doc_tok = self.next()
                    if all(isinstance(p, str) for p in doc_tok.value):
                        doc = "".join(doc_tok.value).strip()
                    self.skip_newlines()
                    continue
                if self.at_kw("fun", "async"):
                    methods.append(self.statement())
                else:
                    raise self.error(
                        f"a type body can only hold functions, found {self.describe(self.tok)}",
                        hint="define behaviour with `fun name(self, ...)`.")
                self.skip_newlines()
            self.close_block("type")
        node = A.TypeDef(name_tok.value, fields, methods, parent, doc,
                         pos=start.pos, end=self.toks[self.i - 1].end)
        self.end_of_statement()
        return node

    def opens_type_body(self):
        """True when the lines after a `type` header are its body.

        A body always begins with a doc string or with `fun`/`async`/`let`/`var`,
        so peeking one token past the newlines settles it without ambiguity."""
        index = self.i
        while index < len(self.toks) and self.toks[index].type == "NEWLINE":
            index += 1
        if index >= len(self.toks):
            return False
        tok = self.toks[index]
        if tok.type == "STRING":
            return True
        return tok.type == "KEYWORD" and tok.value in ("fun", "async")

    def stmt_try(self):
        start = self.next()
        body = self.block("`try`")
        catches = []
        finally_ = None
        while self.at_kw("catch"):
            self.next()
            kinds = []
            name = None
            if self.tok.type == "NAME":
                name = self.next().value
            if self.accept("OP", ":"):
                while True:
                    kinds.append(self.expect("NAME", what="an error kind").value)
                    if not self.accept("OP", "|"):
                        break
            cbody = self.block("`catch`")
            catches.append(A.Catch(name, kinds, cbody, pos=start.pos, end=cbody.end))
        if self.at_kw("finally"):
            self.next()
            finally_ = self.block("`finally`")
        if not catches and finally_ is None:
            raise self.error("a `try` needs a `catch` or a `finally`",
                             hint="write `catch e` to handle the problem.")
        self.close_block("try")
        node = A.Try(body, catches, finally_, pos=start.pos, end=self.toks[self.i - 1].end)
        self.end_of_statement()
        return node

    def stmt_throw(self):
        start = self.next()
        value = self.expression()
        node = A.Throw(value, pos=start.pos, end=value.end)
        self.end_of_statement()
        return node

    def stmt_import(self):
        start = self.next()
        parts = [self.expect("NAME", what="a module name").value]
        while self.at_op(".") and self.peek().type == "NAME":
            self.next()
            parts.append(self.next().value)
        module = ".".join(parts)
        alias = None
        if self.accept("KEYWORD", "as"):
            alias = self.expect("NAME", what="an alias").value
        node = A.Import(module, alias, None, pos=start.pos, end=self.toks[self.i - 1].end)
        self.end_of_statement()
        return node

    def stmt_from(self):
        start = self.next()
        if self.tok.type == "STRING":
            path_tok = self.next()
            path = "".join(p for p in path_tok.value if isinstance(p, str))
            self.expect("KEYWORD", "import", what="`import`")
            names = self.import_names()
            node = A.Use(path, None, names, pos=start.pos, end=self.toks[self.i - 1].end)
        else:
            parts = [self.expect("NAME", what="a module name").value]
            while self.at_op(".") and self.peek().type == "NAME":
                self.next()
                parts.append(self.next().value)
            self.expect("KEYWORD", "import", what="`import`",
                        hint="write `from math import sqrt`.")
            names = self.import_names()
            node = A.Import(".".join(parts), None, names,
                            pos=start.pos, end=self.toks[self.i - 1].end)
        self.end_of_statement()
        return node

    def import_names(self):
        names = []
        while True:
            name = self.expect("NAME", what="a name to import").value
            alias = None
            if self.accept("KEYWORD", "as"):
                alias = self.expect("NAME", what="an alias").value
            names.append((name, alias))
            if not self.accept("OP", ","):
                break
            self.skip_newlines()
        return names

    def stmt_use(self):
        start = self.next()
        tok = self.expect("STRING", what="a file path in quotes",
                          hint="write `use \"./helpers.she\" as helpers`.")
        path = "".join(p for p in tok.value if isinstance(p, str))
        alias = None
        if self.accept("KEYWORD", "as"):
            alias = self.expect("NAME", what="an alias").value
        node = A.Use(path, alias, None, pos=start.pos, end=self.toks[self.i - 1].end)
        self.end_of_statement()
        return node

    def stmt_test(self):
        start = self.next()
        tok = self.expect("STRING", what="a description in quotes",
                          hint="describe what you are checking: `test \"adds numbers\"`.")
        name = "".join(p for p in tok.value if isinstance(p, str))
        body = self.block("`test`")
        self.close_block("test")
        node = A.TestDef(name, body, pos=start.pos, end=body.end)
        self.end_of_statement()
        return node

    def stmt_expect(self):
        start = self.next()
        value = self.climb(COMPARE_LEVEL + 1)
        op, other = None, None
        if self.at_kw("is"):
            self.next()
            if self.at_kw("not"):
                self.next()
                op = "is not"
            else:
                op = "is"
            other = self.expression()
        elif self.at_op("==", "!=", "<", ">", "<=", ">="):
            op = self.next().value
            other = self.expression()
        elif self.at_kw("in"):
            self.next()
            op = "in"
            other = self.expression()
        message = None
        if self.accept("OP", ","):
            message = self.expression()
        node = A.Expect(value, op, other, message, pos=start.pos, end=self.toks[self.i - 1].end)
        self.end_of_statement()
        return node

    # `assert` and `expect` are the same check; `expect` reads better in a
    # test block and `assert` reads better as a guard in ordinary code.
    stmt_assert = stmt_expect

    def expression_statement(self):
        start = self.tok
        expr = self.expression()
        if self.at_op("="):
            self.next()
            value = self.expression()
            node = A.Assign(expr, value, None, pos=start.pos, end=value.end)
            self.end_of_statement()
            return node
        if self.tok.type == "OP" and self.tok.value in ASSIGN_OPS:
            op = ASSIGN_OPS[self.next().value]
            value = self.expression()
            node = A.Assign(expr, value, op, pos=start.pos, end=value.end)
            self.end_of_statement()
            return node
        node = A.ExprStmt(expr, pos=expr.pos, end=expr.end)
        self.end_of_statement(hint=self.statement_hint(start))
        return node

    def statement_hint(self, start):
        if start.type == "NAME" and self.at_op(":"):
            return "to declare a variable write `let name = value`."
        if self.tok.type == "NAME" and start.type == "NAME":
            return "did you mean to call it? `name(argument)`."
        return None

    # --- expressions -------------------------------------------------------
    def expression(self):
        return self.pipeline()

    def pipeline(self):
        left = self.climb(0)
        while self.at_op("|>") or self.continues_with("|>"):
            self.skip_newlines()
            self.next()
            self.skip_newlines()
            right = self.climb(0)
            left = A.Pipe(left, right, pos=left.pos, end=right.end)
        return left

    def continues_with(self, *ops):
        """True when the next line starts with one of these operators.

        Lets a long pipeline or method chain be written one step per line:

            numbers
              |> filter(even?)
              |> sum()
        """
        if self.tok.type != "NEWLINE":
            return False
        index = self.i
        while index < len(self.toks) and self.toks[index].type == "NEWLINE":
            index += 1
        tok = self.toks[index] if index < len(self.toks) else None
        return tok is not None and tok.type == "OP" and tok.value in ops

    def climb(self, level):
        if level >= len(PRECEDENCE):
            return self.unary()
        ops = PRECEDENCE[level]
        left = self.climb(level + 1)
        while True:
            op = self.current_binary_op(ops)
            if op is None:
                return left
            self.consume_binary_op(op)
            self.skip_newlines()
            if op in ("..", "..<"):
                right = self.climb(level + 1)
                left = A.Range(left, right, None, op == "..", pos=left.pos, end=right.end)
                continue
            nxt = level if op in RIGHT_ASSOC else level + 1
            right = self.climb(nxt)
            if op in ("and", "or"):
                left = A.Logical(op, left, right, pos=left.pos, end=right.end)
            elif op == "??":
                left = A.Coalesce(left, right, pos=left.pos, end=right.end)
            elif op in ("==", "!=", "is", "is not", "<", ">", "<=", ">=", "in", "not in"):
                left = A.Compare(op, left, right, pos=left.pos, end=right.end)
            else:
                left = A.Binary(op, left, right, pos=left.pos, end=right.end)

    def current_binary_op(self, ops):
        tok = self.tok
        if tok.type == "OP" and tok.value in ops:
            return tok.value
        if tok.type == "KEYWORD":
            if tok.value == "is" and "is" in ops:
                return "is not" if self.peek().is_("KEYWORD", "not") else "is"
            if tok.value == "in" and "in" in ops:
                return "in"
            if tok.value == "not" and self.peek().is_("KEYWORD", "in") and "not in" in ops:
                return "not in"
            if tok.value in ("and", "or") and tok.value in ops:
                return tok.value
        return None

    def consume_binary_op(self, op):
        self.next()
        if op in ("is not", "not in"):
            self.next()

    def unary(self):
        tok = self.tok
        if self.at_kw("not"):
            self.next()
            operand = self.unary()
            return A.Unary("not", operand, pos=tok.pos, end=operand.end)
        if self.at_op("-", "+"):
            self.next()
            operand = self.unary()
            return A.Unary(tok.value, operand, pos=tok.pos, end=operand.end)
        if self.at_kw("await"):
            self.next()
            operand = self.unary()
            return A.Await(operand, pos=tok.pos, end=operand.end)
        return self.postfix()

    def postfix(self):
        node = self.primary()
        while True:
            if self.continues_with(".", "?."):
                self.skip_newlines()
            if self.at_op("("):
                node = self.finish_call(node)
            elif self.at_op(".", "?."):
                safe = self.next().value == "?."
                name = self.tok
                if name.type not in ("NAME", "KEYWORD"):
                    raise self.error(f"expected a property name after `.`, "
                                     f"found {self.describe(name)}")
                self.next()
                node = A.Member(node, name.value, safe, pos=node.pos, end=name.end)
            elif self.at_op("["):
                self.next()
                self.skip_newlines()
                if self.at_op(":"):
                    self.next()
                    stop = None if self.at_op("]") else self.expression()
                    close = self.expect("OP", "]", what="`]`")
                    node = A.Slice(node, None, stop, pos=node.pos, end=close.end)
                    continue
                key = self.expression()
                if self.at_op(":"):
                    self.next()
                    stop = None if self.at_op("]") else self.expression()
                    close = self.expect("OP", "]", what="`]`")
                    node = A.Slice(node, key, stop, pos=node.pos, end=close.end)
                    continue
                self.skip_newlines()
                close = self.expect("OP", "]", what="`]`",
                                    hint="close the index with `]`.")
                node = A.Index(node, key, pos=node.pos, end=close.end)
            else:
                return node

    def finish_call(self, callee):
        self.expect("OP", "(")
        args, kwargs = [], {}
        self.skip_newlines()
        while not self.at_op(")"):
            if self.at_op("..") and self.peek().is_("OP", "."):
                start = self.next()
                self.next()
                value = self.expression()
                args.append(A.Spread(value, pos=start.pos, end=value.end))
            elif (self.tok.type in ("NAME", "KEYWORD")
                    and self.peek().is_("OP", ":")):
                # Keywords are allowed as argument labels: `sort(by: ...)`.
                name = self.next().value
                self.next()
                self.skip_newlines()
                kwargs[name] = self.expression()
            else:
                args.append(self.expression())
            self.skip_newlines()
            if not self.accept("OP", ","):
                break
            self.skip_newlines()
        close = self.expect("OP", ")", what="`)`",
                            hint="close the call with `)`.")
        return A.Call(callee, args, kwargs, pos=callee.pos, end=close.end)

    def primary(self):
        tok = self.tok
        if tok.type == "NUMBER":
            self.next()
            return A.Num(tok.value, pos=tok.pos, end=tok.end)
        if tok.type == "STRING":
            self.next()
            return self.string_node(tok)
        if tok.type == "NAME":
            self.next()
            return A.Name(tok.value, pos=tok.pos, end=tok.end)
        if tok.type == "KEYWORD":
            if tok.value == "true":
                self.next()
                return A.Bool(True, pos=tok.pos, end=tok.end)
            if tok.value == "false":
                self.next()
                return A.Bool(False, pos=tok.pos, end=tok.end)
            if tok.value == "nothing":
                self.next()
                return A.Nothing(pos=tok.pos, end=tok.end)
            if tok.value == "fun":
                return self.lambda_expr()
            if tok.value == "async" and self.peek().is_("KEYWORD", "fun"):
                self.next()
                node = self.lambda_expr()
                node.is_async = True
                node.pos = tok.pos
                return node
            if tok.value == "if":
                return self.if_expr()
            if tok.value == "match":
                return self.match_expr()
            if tok.value == "ask":
                self.next()
                prompt = None
                if self.tok.type in ("STRING", "NAME") or self.at_op("("):
                    prompt = self.unary()
                return A.Ask(prompt, pos=tok.pos, end=(prompt.end if prompt else tok.end))
        if self.at_op("("):
            self.next()
            self.skip_newlines()
            inner = self.expression()
            self.skip_newlines()
            self.expect("OP", ")", what="`)`", hint="close the group with `)`.")
            return inner
        if self.at_op("["):
            return self.list_literal()
        if self.at_op("{"):
            return self.map_literal()
        raise self.error(
            f"I expected a value here, but found {self.describe(tok)}",
            hint=self.value_hint(tok),
        )

    def value_hint(self, tok):
        if tok.type == "KEYWORD" and tok.value == "end":
            return "there may be an extra `end`, or a missing value before it."
        if tok.type == "NEWLINE":
            return "the line ends before the expression is finished."
        if tok.type == "KEYWORD":
            return f"`{tok.value}` is a keyword, so it cannot be used as a value."
        return None

    def string_node(self, tok):
        parts = []
        for part in tok.value:
            if isinstance(part, str):
                parts.append(part)
                continue
            _, tokens, raw = part
            try:
                sub = Parser(tokens, self.file)
                expr = sub.expression()
                if sub.tok.type not in ("EOF", "NEWLINE"):
                    raise sub.error("more than one expression")
            except SyntaxErr:
                parts.append(raw)   # not an expression, so it is literal text
                continue
            parts.append(expr)
        merged = []
        for part in parts:
            if isinstance(part, str) and merged and isinstance(merged[-1], str):
                merged[-1] += part
            else:
                merged.append(part)
        return A.Str(merged or [""], pos=tok.pos, end=tok.end)

    def list_literal(self):
        start = self.expect("OP", "[")
        items = []
        self.skip_newlines()
        while not self.at_op("]"):
            if self.at_op("..") and self.peek().is_("OP", "."):
                spread_start = self.next()
                self.next()
                value = self.expression()
                items.append(A.Spread(value, pos=spread_start.pos, end=value.end))
            else:
                items.append(self.expression())
            self.skip_newlines()
            if not self.accept("OP", ","):
                break
            self.skip_newlines()
        close = self.expect("OP", "]", what="`]`", hint="close the list with `]`.")
        return A.ListLit(items, pos=start.pos, end=close.end)

    def map_literal(self):
        start = self.expect("OP", "{")
        pairs = []
        self.skip_newlines()
        while not self.at_op("}"):
            if self.at_op("..") and self.peek().is_("OP", "."):
                spread_start = self.next()
                self.next()
                value = self.expression()
                pairs.append(A.Spread(value, pos=spread_start.pos, end=value.end))
                self.skip_newlines()
                if not self.accept("OP", ","):
                    break
                self.skip_newlines()
                continue
            if self.tok.type in ("NAME", "KEYWORD") and self.peek().is_("OP", ":"):
                key_tok = self.next()
                key = A.Str([key_tok.value], pos=key_tok.pos, end=key_tok.end)
            elif self.tok.type == "STRING" and self.peek().is_("OP", ":"):
                key = self.string_node(self.next())
            elif self.at_op("["):
                self.next()
                key = self.expression()
                self.expect("OP", "]", what="`]`")
            else:
                key = self.expression()
            self.expect("OP", ":", what="`:`",
                        hint="a map entry looks like `name: value`.")
            self.skip_newlines()
            value = self.expression()
            pairs.append((key, value))
            self.skip_newlines()
            if not self.accept("OP", ","):
                break
            self.skip_newlines()
        close = self.expect("OP", "}", what="`}`", hint="close the map with `}`.")
        return A.MapLit(pairs, pos=start.pos, end=close.end)

    def lambda_expr(self):
        start = self.expect("KEYWORD", "fun")
        params = self.params()
        if self.at_op("->"):
            self.next()
            self.skip_newlines()
            body = self.expression()
            return A.Lambda(params, body, True, False, pos=start.pos, end=body.end)
        body = self.block("function")
        self.close_block("fun")
        return A.Lambda(params, body, False, False, pos=start.pos, end=body.end)

    def if_expr(self):
        start = self.expect("KEYWORD", "if")
        cond = self.expression()
        self.expect("KEYWORD", "then", what="`then`",
                    hint="as a value, an `if` needs `then` and `else`: "
                         "`let x = if a then b else c`.")
        then = self.expression()
        self.expect("KEYWORD", "else", what="`else`",
                    hint="an `if` used as a value must always produce something.")
        otherwise = self.expression()
        return A.IfExpr(cond, then, otherwise, pos=start.pos, end=otherwise.end)

    def match_expr(self):
        start = self.expect("KEYWORD", "match")
        subject = self.expression()
        self.skip_newlines()
        cases = []
        while self.at_kw("case"):
            case_start = self.next()
            pattern = self.pattern()
            guard = None
            if self.at_kw("if"):
                self.next()
                guard = self.expression()
            if self.at_op("->"):
                self.next()
                self.skip_newlines()
                body = self.expression()
                cases.append(A.MatchCase(pattern, guard, body, True,
                                         pos=case_start.pos, end=body.end))
            else:
                self.skip_newlines()
                body = self.block("`case`")
                cases.append(A.MatchCase(pattern, guard, body, False,
                                         pos=case_start.pos, end=body.end))
            self.skip_newlines()
        if not cases:
            raise self.error("a `match` needs at least one `case`",
                             hint="write `case <pattern> -> <result>`.")
        self.close_block("match")
        return A.MatchExpr(subject, cases, pos=start.pos, end=self.toks[self.i - 1].end)

    # --- patterns ----------------------------------------------------------
    def pattern(self):
        first = self.pattern_atom()
        if not self.at_op("|"):
            return first
        options = [first]
        while self.accept("OP", "|"):
            options.append(self.pattern_atom())
        return A.POr(options, pos=first.pos, end=options[-1].end)

    def pattern_atom(self):
        tok = self.tok
        if tok.type == "NUMBER" or tok.type == "STRING":
            self.next()
            value = A.Num(tok.value, pos=tok.pos, end=tok.end) if tok.type == "NUMBER" \
                else self.string_node(tok)
            if self.at_op("..", "..<"):
                inclusive = self.next().value == ".."
                stop = self.primary()
                return A.PRange(value, stop, inclusive, pos=tok.pos, end=stop.end)
            return A.PLit(value, pos=tok.pos, end=tok.end)
        if self.at_op("-") and self.peek().type == "NUMBER":
            self.next()
            num = self.next()
            return A.PLit(A.Num(-num.value, pos=tok.pos, end=num.end), pos=tok.pos, end=num.end)
        if tok.type == "KEYWORD" and tok.value in ("true", "false", "nothing"):
            self.next()
            node = (A.Bool(tok.value == "true", pos=tok.pos, end=tok.end)
                    if tok.value != "nothing" else A.Nothing(pos=tok.pos, end=tok.end))
            return A.PLit(node, pos=tok.pos, end=tok.end)
        if tok.type == "NAME":
            self.next()
            if tok.value == "_":
                return A.PWild(pos=tok.pos, end=tok.end)
            if self.at_op("("):
                self.next()
                args = []
                self.skip_newlines()
                while not self.at_op(")"):
                    args.append(self.pattern())
                    self.skip_newlines()
                    if not self.accept("OP", ","):
                        break
                    self.skip_newlines()
                close = self.expect("OP", ")", what="`)`")
                return A.PType(tok.value, args, None, pos=tok.pos, end=close.end)
            if self.at_op("{"):
                fields, _rest = self.pattern_map_body()
                return A.PType(tok.value, None, fields, pos=tok.pos, end=self.toks[self.i - 1].end)
            return A.PBind(tok.value, pos=tok.pos, end=tok.end)
        if self.at_op("["):
            start = self.next()
            items, rest = [], None
            self.skip_newlines()
            while not self.at_op("]"):
                if self.at_op("..") and self.peek().is_("OP", "."):
                    self.next()
                    self.next()
                    rest = self.expect("NAME", what="a name for the rest").value
                else:
                    items.append(self.pattern())
                self.skip_newlines()
                if not self.accept("OP", ","):
                    break
                self.skip_newlines()
            close = self.expect("OP", "]", what="`]`")
            return A.PList(items, rest, pos=start.pos, end=close.end)
        if self.at_op("{"):
            start = self.tok
            fields, rest = self.pattern_map_body()
            return A.PMap(fields, rest, pos=start.pos, end=self.toks[self.i - 1].end)
        raise self.error(f"this is not something I can match on: {self.describe(tok)}",
                         hint="patterns can be values, names, `_`, `[a, b]`, `{k: v}`, "
                              "or `TypeName(a, b)`.")

    def pattern_map_body(self):
        self.expect("OP", "{")
        fields, rest = [], None
        self.skip_newlines()
        while not self.at_op("}"):
            if self.at_op("..") and self.peek().is_("OP", "."):
                self.next()
                self.next()
                rest = self.expect("NAME", what="a name for the rest").value
            else:
                key = self.expect("NAME", what="a field name").value
                if self.accept("OP", ":"):
                    fields.append((key, self.pattern()))
                else:
                    fields.append((key, A.PBind(key)))
            self.skip_newlines()
            if not self.accept("OP", ","):
                break
            self.skip_newlines()
        self.expect("OP", "}", what="`}`")
        return fields, rest


def parse(src, file="<input>"):
    return Parser(tokenize(src, file), file).parse()
