"""`she fmt` — canonical formatting.

Works on the token stream rather than the AST so that comments and deliberate
blank lines survive. A formatter that silently eats your comments is worse than
no formatter at all.

Rules:
  * two spaces per block level
  * one space around binary operators, none inside brackets
  * one space after a comma, never before
  * at most one blank line in a row
  * trailing whitespace removed, file ends with exactly one newline
"""

from .lexer import tokenize

INDENT = "  "

# Words that open a block, and words that close or re-open one.
OPENERS = {"if", "for", "while", "fun", "type", "try", "match", "test", "repeat"}
CLOSERS = {"end", "until"}
MIDDLES = {"else", "case", "catch", "finally"}

NO_SPACE_BEFORE = {")", "]", "}", ",", ":", ".", "?.", "..", "..<"}
NO_SPACE_AFTER = {"(", "[", "{", ".", "?.", "..", "..<"}
UNARY_CONTEXT = {"(", "[", "{", ",", "=", "->", "=>", "|>", "+", "-", "*", "/",
                 "%", "^", "<", ">", "==", "!=", "<=", ">=", ":", "??"}
OPENERS_BRACKET = {"(": ")", "[": "]", "{": "}"}
CLOSERS_BRACKET = {")", "]", "}"}
# A line beginning with one of these continues the expression above it.
CONTINUATIONS = {"|>", ".", "?.", "??"}


def format_source(source, file="<input>"):
    """Return `source` formatted. Raises SyntaxErr if it does not parse."""
    tokenize(source, file)  # fail loudly rather than mangling broken code
    out = []
    depth = 0        # block depth, from `if` / `fun` / `end` and friends
    open_brackets = 0  # brackets left open by the lines above
    blank_run = 0

    for raw in source.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        code, comment = split_comment(raw)
        stripped = code.strip()

        if not stripped and not comment:
            blank_run += 1
            if blank_run <= 1 and out:
                out.append("")
            continue
        blank_run = 0

        if not stripped:
            out.append(INDENT * (depth + (1 if open_brackets else 0)) + comment.strip())
            continue

        tokens = safe_tokens(stripped, file)
        starts_continuation = bool(tokens) and tokens[0].type == "OP" \
            and tokens[0].value in CONTINUATIONS
        mid_expression = open_brackets > 0

        words = leading_words(stripped)
        if not mid_expression and words and (words[0] in CLOSERS or words[0] in MIDDLES):
            depth = max(0, depth - 1)

        indent = depth
        if mid_expression or starts_continuation:
            # A closing bracket lines up with the line that opened it.
            closes_first = bool(tokens) and tokens[0].type == "OP" \
                and tokens[0].value in CLOSERS_BRACKET
            indent += 0 if (closes_first and open_brackets == 1) else 1

        line = INDENT * indent + respace(stripped, file)
        if comment:
            line += "  " + comment.strip()
        out.append(line.rstrip())

        if not mid_expression and not starts_continuation:
            depth = max(0, depth + delta(stripped, words, file))
        open_brackets = max(0, open_brackets + net_brackets(tokens))

    while out and not out[-1]:
        out.pop()
    return "\n".join(out) + "\n"


def safe_tokens(code, file):
    try:
        return [t for t in tokenize(code, file) if t.type not in ("EOF", "NEWLINE")]
    except Exception:  # noqa: BLE001 - formatting must never crash on odd input
        return []


def net_brackets(tokens):
    """How many brackets this line leaves open."""
    depth = 0
    for token in tokens:
        if token.type != "OP":
            continue
        if token.value in OPENERS_BRACKET:
            depth += 1
        elif token.value in CLOSERS_BRACKET:
            depth -= 1
    return depth


def split_comment(line):
    """Split a line into (code, comment), respecting text and block comments."""
    in_text = None
    i = 0
    while i < len(line):
        ch = line[i]
        if in_text:
            if ch == "\\":
                i += 2
                continue
            if ch == in_text:
                in_text = None
        elif ch in "\"'":
            in_text = ch
        elif ch == "#":
            return line[:i], line[i:]
        i += 1
    return line, ""


def leading_words(code):
    out = []
    for token in code.replace("(", " ").replace(")", " ").split():
        out.append(token)
        if len(out) >= 3:
            break
    return out


def delta(code, words, file):
    """How much this line changes the block depth."""
    if not words:
        return 0
    first = words[0]
    change = 0
    if first in MIDDLES:
        return 1
    if first in CLOSERS:
        return 0
    if first in OPENERS or (first == "async" and len(words) > 1 and words[1] == "fun"):
        # `if x then y`, `fun f() -> expr` and `type P has x, y` stay on one line.
        if first == "type" and " has " in f" {code} " and not code.rstrip().endswith("has"):
            return 0
        if inline_block(code, file):
            return 0
        change = 1
    return change


def inline_block(code, file):
    """True when the line opens and finishes a block on the same line."""
    try:
        tokens = tokenize(code, file)
    except Exception:  # noqa: BLE001 - formatting must never crash on odd input
        return False
    values = [t.value for t in tokens]
    if "->" in values:
        return True
    if "then" in values:
        index = values.index("then")
        rest = [v for v in values[index + 1:] if v not in (None, "\n")]
        return bool(rest)
    return False


def respace(code, file):
    """Re-emit one line of code with canonical spacing."""
    try:
        tokens = [t for t in tokenize(code, file) if t.type not in ("EOF", "NEWLINE")]
    except Exception:  # noqa: BLE001
        return code
    out = []
    previous = None
    before_previous = None
    previous_unary = False
    brackets = []          # which bracket we are inside, innermost last
    for index, token in enumerate(tokens):
        text = render(token, code)
        unary = (token.type == "OP" and token.value in ("-", "+")
                 and starts_a_value(previous))
        # `...rest` lexes as `..` then `.`; it is a spread, not a range, and
        # wants an ordinary space in front of it.
        spread = (token.type == "OP" and token.value == ".."
                  and index + 1 < len(tokens) and tokens[index + 1].is_("OP", "."))
        if out and needs_space(previous, token, previous_unary, brackets,
                                 before_previous, spread):
            out.append(" " + text)
        else:
            out.append(text)
        if token.type == "OP":
            if token.value in OPENERS_BRACKET:
                brackets.append(token.value)
            elif token.value in CLOSERS_BRACKET and brackets:
                brackets.pop()
        before_previous, previous, previous_unary = previous, token, unary
    return "".join(out)


def is_member(before_previous):
    return (before_previous is not None and before_previous.type == "OP"
            and before_previous.value in (".", "?."))


def starts_a_value(previous):
    """True when a `-` here negates rather than subtracts."""
    if previous is None:
        return True
    if previous.type == "OP":
        return previous.value in UNARY_CONTEXT
    if previous.type == "KEYWORD":
        return previous.value not in ("true", "false", "nothing", "end")
    return False


def render(token, source):
    if token.type == "STRING":
        return source[token.pos.idx:token.end.idx] or rebuild_string(token)
    if token.type == "NUMBER":
        return source[token.pos.idx:token.end.idx]
    return str(token.value)


def rebuild_string(token):
    parts = []
    for part in token.value:
        parts.append(part if isinstance(part, str) else "{...}")
    return '"' + "".join(parts) + '"'


def needs_space(previous, token, previous_unary, brackets,
                before_previous=None, spread=False):
    if previous_unary:
        return False
    if previous.type == "OP" and previous.value in NO_SPACE_AFTER:
        return False
    if token.type == "OP" and token.value in NO_SPACE_BEFORE and not spread:
        return False
    if previous.type == "OP" and previous.value == ":" and brackets[-1:] == ["["]:
        return False        # a slice is `xs[1:3]`, a map entry is `{a: 1}`
    if token.type == "OP" and token.value == "(":
        # `f(x)` and `"hi".repeat(3)` hug; `if (x)` does not.
        if previous.type in ("NAME", "STRING") or (previous.type == "OP"
                                                   and previous.value in ")]"):
            return False
        if previous.type == "KEYWORD" and previous.value in ("fun", "ask"):
            return False
        if previous.type == "KEYWORD" and is_member(before_previous):
            return False        # `.repeat(3)` — a keyword used as a method name
    if token.type == "OP" and token.value == "[":
        if previous.type in ("NAME", "STRING") or (previous.type == "OP"
                                                   and previous.value in ")]"):
            return False
    return True


def format_file(path, write=False):
    """Format one file. Returns True when the file changed."""
    with open(path, encoding="utf-8") as handle:
        original = handle.read()
    formatted = format_source(original, path)
    if formatted == original:
        return False
    if write:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(formatted)
    return True
