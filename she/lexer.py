"""SHE lexer. Turns source text into tokens.

String interpolation is handled here: "hi {name}" becomes a STRING token whose
value is a list of literal / expression parts, so the parser never re-scans text.
"""

from .errors import Pos, SyntaxErr

KEYWORDS = {
    "and", "as", "async", "await", "break", "by", "case", "catch", "do", "each",
    "else", "end", "false", "finally", "for", "from", "fun", "has", "if",
    "import", "in", "is", "let", "match", "not", "nothing", "or", "repeat",
    "return", "say", "skip", "test", "then", "throw", "true", "try", "type",
    "until", "use", "var", "while", "ask", "expect", "assert",
}

# Longest first so `..<` beats `..` beats `.`
OPERATORS = [
    "..<", "//=", "??=", "?.", "|>", "??", "->", "=>", "..",
    "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "%=", "^=", "//",
    "+", "-", "*", "/", "%", "^", "<", ">", "=", "(", ")", "[", "]",
    "{", "}", ",", ".", ":", "|",
]


class Tok:
    __slots__ = ("type", "value", "pos", "end")

    def __init__(self, type_, value, pos, end):
        self.type, self.value, self.pos, self.end = type_, value, pos, end

    def is_(self, type_, value=None):
        return self.type == type_ and (value is None or self.value == value)

    def __repr__(self):
        return f"{self.type}({self.value!r})"


class Lexer:
    def __init__(self, src, file="<input>"):
        self.src = src
        self.file = file
        self.pos = Pos(-1, 0, -1, file, src)
        self.ch = None
        self.advance()

    def advance(self, n=1):
        for _ in range(n):
            self.pos.advance(self.ch)
            self.ch = self.src[self.pos.idx] if self.pos.idx < len(self.src) else None

    def peek(self, offset=1):
        i = self.pos.idx + offset
        return self.src[i] if 0 <= i < len(self.src) else None

    def at(self, s):
        return self.src.startswith(s, self.pos.idx)

    def error(self, msg, pos=None, hint=None):
        p = pos or self.pos.copy()
        return SyntaxErr(msg, p, p.copy().advance(), hint=hint)

    def tokens(self):
        out = []
        while self.ch is not None:
            if self.ch in " \t\r":
                self.advance()
            elif self.at("#-"):
                self.block_comment()
            elif self.ch == "#":
                while self.ch is not None and self.ch != "\n":
                    self.advance()
            elif self.ch == "\\" and self.peek() == "\n":
                self.advance(2)  # explicit line continuation
            elif self.ch in "\n;":
                start = self.pos.copy()
                self.advance()
                if out and out[-1].type != "NEWLINE":
                    out.append(Tok("NEWLINE", "\n", start, self.pos.copy()))
            elif self.ch.isdigit() or (self.ch == "." and (self.peek() or "").isdigit()):
                out.append(self.number())
            elif self.ch.isalpha() or self.ch == "_":
                tok = self.word()
                if tok.type == "NAME" and tok.value == "r" and self.ch in "\"'":
                    out.append(self.string(raw=True))
                else:
                    out.append(tok)
            elif self.ch in "\"'":
                out.append(self.string())
            else:
                op = next((o for o in OPERATORS if self.at(o)), None)
                if op is None:
                    raise self.error(
                        "I do not understand the character `" + self.ch + "`",
                        hint="SHE uses `is` or `==` to compare, and `#` to start a comment.",
                    )
                start = self.pos.copy()
                self.advance(len(op))
                out.append(Tok("OP", op, start, self.pos.copy()))
        out.append(Tok("EOF", None, self.pos.copy(), self.pos.copy()))
        return out

    def block_comment(self):
        start = self.pos.copy()
        self.advance(2)
        depth = 1
        while self.ch is not None and depth:
            if self.at("#-"):
                depth += 1
                self.advance(2)
            elif self.at("-#"):
                depth -= 1
                self.advance(2)
            else:
                self.advance()
        if depth:
            raise self.error("this block comment is never closed", start,
                             hint="close it with `-#`.")

    def number(self):
        start = self.pos.copy()
        if self.ch == "0" and (self.peek() or "").lower() in ("x", "b", "o"):
            base = {"x": 16, "b": 2, "o": 8}[self.peek().lower()]
            self.advance(2)
            digits = ""
            while self.ch is not None and (self.ch.isalnum() or self.ch == "_"):
                digits += self.ch
                self.advance()
            try:
                return Tok("NUMBER", int(digits.replace("_", ""), base), start, self.pos.copy())
            except ValueError:
                raise self.error(f"`{digits}` is not a valid base-{base} number", start)

        text = ""
        dots = 0
        while self.ch is not None and (self.ch.isdigit() or self.ch == "_" or self.ch == "."):
            if self.ch == ".":
                if self.peek() == "." or dots:  # `1..10` is a range, not a decimal point
                    break
                dots = 1
            text += self.ch
            self.advance()
        nxt = self.peek() or ""
        if self.ch in ("e", "E") and (nxt.isdigit() or (nxt in "+-" and (self.peek(2) or "").isdigit())):
            text += self.ch
            self.advance()
            if self.ch in "+-":
                text += self.ch
                self.advance()
            while self.ch is not None and self.ch.isdigit():
                text += self.ch
                self.advance()
            dots = 1
        text = text.replace("_", "")
        value = float(text) if dots else int(text)
        return Tok("NUMBER", value, start, self.pos.copy())

    def word(self):
        start = self.pos.copy()
        text = ""
        while self.ch is not None and (self.ch.isalnum() or self.ch == "_"):
            text += self.ch
            self.advance()
        # Predicate names read like English: empty?, valid?, prime?
        if self.ch == "?" and text and text not in KEYWORDS and self.peek() != ".":
            text += "?"
            self.advance()
        kind = "KEYWORD" if text in KEYWORDS else "NAME"
        return Tok(kind, text, start, self.pos.copy())

    ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\",
               "\"": "\"", "'": "'", "{": "{", "}": "}", "e": "\033"}

    def string(self, raw=False):
        """Returns a STRING token whose value is a list of str | ("expr", tokens)."""
        start = self.pos.copy()
        quote = self.ch
        triple = self.at(quote * 3)
        self.advance(3 if triple else 1)

        parts = []
        buf = ""
        while True:
            if self.ch is None:
                raise self.error("this text is never closed", start,
                                 hint="add a closing " + quote + " at the end.")
            if triple and self.at(quote * 3):
                self.advance(3)
                break
            if not triple and self.ch == quote:
                self.advance()
                break
            if not triple and self.ch == "\n":
                raise self.error("text cannot span lines", start,
                                 hint="use \\n inside the text, or triple quotes for a block.")
            if self.ch == "\\" and not raw:
                self.advance()
                if self.ch is None:
                    continue
                buf += self.ESCAPES.get(self.ch, "\\" + self.ch)
                self.advance()
                continue
            if self.ch == "}" and not raw and self.peek() == "}":
                buf += "}"          # }} is a literal closing brace
                self.advance(2)
                continue
            if self.ch == "{" and not raw:
                if self.peek() == "{":  # {{ is a literal brace
                    buf += "{"
                    self.advance(2)
                    continue
                found = self.interpolation(quote, triple)
                if found is None:
                    # No closing brace before the text ends, so this `{` is
                    # just a brace — JSON, CSS and `{2,3}` in patterns all
                    # sit inside ordinary text without escaping.
                    buf += "{"
                    self.advance()
                    continue
                if buf:
                    parts.append(buf)
                    buf = ""
                parts.append(("expr",) + found)
                continue
            buf += self.ch
            self.advance()

        if buf or not parts:
            parts.append(buf)
        return Tok("STRING", parts, start, self.pos.copy())

    def interpolation(self, quote="\"", triple=False):
        """Scan a balanced {...} and lex its contents as a sub-expression.

        Returns None (having consumed nothing) when there is no closing brace
        before the text ends, so the caller can treat the `{` as literal."""
        open_pos = self.pos.copy()   # the position of the `{` itself
        self.advance()
        depth = 1
        inner_start = self.pos.idx
        while self.ch is not None:
            if self.ch in "\"'":
                # A nested string inside the braces: `"{join(names, ", ")}"`.
                q = self.ch
                self.advance()
                while self.ch is not None and self.ch != q:
                    if self.ch == "\\":
                        self.advance()
                    self.advance()
            elif self.ch == "\n" and not triple:
                break
            elif self.ch == "{":
                depth += 1
            elif self.ch == "}":
                depth -= 1
                if depth == 0:
                    break
            self.advance()
        if self.ch != "}" or depth != 0:
            self.pos = open_pos.copy()       # rewind to the `{`, consume nothing
            self.ch = self.src[self.pos.idx]
            return None
        inner = self.src[inner_start:self.pos.idx]
        self.advance()
        toks = Lexer(inner, self.file).tokens()
        if len(toks) <= 1:
            raise self.error("there is nothing inside these braces", open_pos,
                             hint="put an expression in, like {name}.")
        for t in toks:  # re-anchor onto the real file so errors point at the right spot
            t.pos.line = t.end.line = open_pos.line
            t.pos.col += open_pos.col + 1
            t.end.col += open_pos.col + 1
            t.pos.src = t.end.src = self.src
            t.pos.file = t.end.file = self.file
        return toks, "{" + inner + "}"


def tokenize(src, file="<input>"):
    return Lexer(src, file).tokens()
