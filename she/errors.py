"""Errors that read like a helpful colleague, not a stack dump."""


class Pos:
    __slots__ = ("idx", "line", "col", "file", "src")

    def __init__(self, idx, line, col, file, src):
        self.idx, self.line, self.col, self.file, self.src = idx, line, col, file, src

    def copy(self):
        return Pos(self.idx, self.line, self.col, self.file, self.src)

    def advance(self, ch=None):
        self.idx += 1
        self.col += 1
        if ch == "\n":
            self.line += 1
            self.col = 0
        return self


class SheError(Exception):
    """Base for everything the user can see. `kind` is what SHE code catches."""

    kind = "Error"

    def __init__(self, message, pos=None, end=None, hint=None, trace=None):
        super().__init__(message)
        self.message = message
        self.pos = pos
        self.end = end
        self.hint = hint
        self.trace = trace or []

    def render(self, color=True):
        def paint(s, c):
            return f"\033[{c}m{s}\033[0m" if color else s

        out = [paint(f"{self.kind}: {self.message}", "1;31")]
        if self.pos is not None:
            out.append(paint(f"  --> {self.pos.file}:{self.pos.line + 1}:{self.pos.col + 1}", "2;37"))
            out.append(self._snippet(color))
        for frame in reversed(self.trace):
            out.append(paint(f"  in {frame}", "2;37"))
        if self.hint:
            out.append(paint(f"  help: {self.hint}", "1;36"))
        return "\n".join(out)

    def _snippet(self, color=True):
        src = self.pos.src or ""
        lines = src.split("\n")
        if self.pos.line >= len(lines):
            return ""
        line = lines[self.pos.line].replace("\t", "    ")
        num = str(self.pos.line + 1)
        gutter = " " * len(num)
        start = self.pos.col
        width = 1
        if self.end is not None and self.end.line == self.pos.line:
            width = max(1, self.end.col - start)
        caret = " " * start + "^" * width
        if color:
            caret = f"\033[1;31m{caret}\033[0m"
        return f"  {gutter} |\n  {num} | {line}\n  {gutter} | {caret}"

    def __str__(self):
        return self.render(color=False)


class SyntaxErr(SheError):
    kind = "SyntaxError"


class NameErr(SheError):
    kind = "NameError"


class TypeErr(SheError):
    kind = "TypeError"


class ValueErr(SheError):
    kind = "ValueError"


class IndexErr(SheError):
    kind = "IndexError"


class KeyErr(SheError):
    kind = "KeyError"


class MathErr(SheError):
    kind = "MathError"


class ImportErr(SheError):
    kind = "ImportError"


class PermissionErr(SheError):
    """Raised when a program touches a capability it was not granted."""

    kind = "PermissionError"


class LimitErr(SheError):
    """Step / recursion / time budget exhausted."""

    kind = "LimitError"


class AssertErr(SheError):
    kind = "AssertionError"


class Thrown(SheError):
    """`throw x` from SHE code. Carries the raw value."""

    kind = "Thrown"

    def __init__(self, value, message=None, pos=None, end=None, trace=None):
        super().__init__(message if message is not None else str(value), pos, end, trace=trace)
        self.value = value


def did_you_mean(name, candidates, limit=3):
    """Cheap edit-distance suggestion. Beginners live or die by this."""
    import difflib

    hits = difflib.get_close_matches(name, list(candidates), n=limit, cutoff=0.6)
    if not hits:
        return None
    if len(hits) == 1:
        return f"did you mean `{hits[0]}`?"
    return "did you mean " + " or ".join(f"`{h}`" for h in hits) + "?"
