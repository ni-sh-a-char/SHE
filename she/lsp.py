"""A small Language Server for SHE.

Speaks LSP over stdin/stdout using nothing but the standard library. Supports:
  * diagnostics as you type (the same errors the CLI gives, hint included)
  * completion for keywords, builtins, stdlib modules and their members
  * hover documentation
  * document formatting

Start it with `she lsp`. The VS Code extension in editors/vscode wires it up.
"""

import json
import re
import sys

from . import __version__
from .errors import SheError
from .lexer import KEYWORDS

_MEMBER = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z0-9_?]*)$")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_?]*$")

KEYWORD_DOCS = {
    "let": "Name a value that will not change.",
    "var": "Name a value that can change later.",
    "fun": "Define a function.",
    "say": "Print values on one line.",
    "ask": "Read a line of input.",
    "if": "Do something only when a condition holds.",
    "else": "What to do otherwise.",
    "for": "Repeat over every item: `for each item in items`.",
    "while": "Repeat while a condition holds.",
    "repeat": "Repeat until a condition holds. Always runs at least once.",
    "match": "Choose a branch by the shape of a value.",
    "type": "Define a type: `type Point has x, y`.",
    "try": "Run code that might fail.",
    "catch": "Handle a failure.",
    "throw": "Raise a failure.",
    "test": "Define a test block, run by `she test`.",
    "expect": "Assert inside a test.",
    "import": "Bring in a module.",
    "use": "Bring in another .she file.",
    "async": "Run a function on its own thread; call `await` for the result.",
    "await": "Wait for a task to finish.",
    "end": "Close the current block.",
}


def serve(stdin=None, stdout=None):
    """Run the server until the client closes the connection."""
    stdin = stdin or sys.stdin.buffer
    stdout = stdout or sys.stdout.buffer
    documents = {}
    while True:
        message = read_message(stdin)
        if message is None:
            return 0
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        if method == "initialize":
            send(stdout, request_id, {
                "capabilities": {
                    "textDocumentSync": 1,
                    "completionProvider": {"triggerCharacters": ["."]},
                    "hoverProvider": True,
                    "documentFormattingProvider": True,
                },
                "serverInfo": {"name": "she-lsp", "version": __version__},
            })
        elif method == "initialized":
            continue
        elif method == "shutdown":
            send(stdout, request_id, None)
        elif method == "exit":
            return 0
        elif method in ("textDocument/didOpen", "textDocument/didChange",
                        "textDocument/didSave"):
            document = params.get("textDocument", {})
            uri = document.get("uri", "")
            if method == "textDocument/didOpen":
                text = document.get("text", "")
            else:
                changes = params.get("contentChanges") or [{}]
                text = changes[-1].get("text", documents.get(uri, ""))
            documents[uri] = text
            notify(stdout, "textDocument/publishDiagnostics",
                   {"uri": uri, "diagnostics": diagnose(text, uri)})
        elif method == "textDocument/didClose":
            documents.pop(params.get("textDocument", {}).get("uri", ""), None)
        elif method == "textDocument/completion":
            uri = params.get("textDocument", {}).get("uri", "")
            send(stdout, request_id,
                 complete(documents.get(uri, ""), params.get("position", {})))
        elif method == "textDocument/hover":
            uri = params.get("textDocument", {}).get("uri", "")
            send(stdout, request_id,
                 hover(documents.get(uri, ""), params.get("position", {})))
        elif method == "textDocument/formatting":
            uri = params.get("textDocument", {}).get("uri", "")
            send(stdout, request_id, format_document(documents.get(uri, ""), uri))
        elif request_id is not None:
            send(stdout, request_id, None)


# --- transport --------------------------------------------------------------

def read_message(stream):
    length = 0
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.decode("utf-8", "replace").strip()
        if not line:
            break
        if line.lower().startswith("content-length:"):
            try:
                length = int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    if length <= 0:
        return {}
    body = stream.read(length)
    try:
        return json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def write(stream, payload):
    body = json.dumps(payload).encode("utf-8")
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    stream.write(body)
    stream.flush()


def send(stream, request_id, result):
    if request_id is None:
        return
    write(stream, {"jsonrpc": "2.0", "id": request_id, "result": result})


def notify(stream, method, params):
    write(stream, {"jsonrpc": "2.0", "method": method, "params": params})


# --- features ---------------------------------------------------------------

def diagnose(text, uri):
    from .parser import parse
    try:
        parse(text, uri)
        return []
    except SheError as error:
        line = error.pos.line if error.pos else 0
        start = error.pos.col if error.pos else 0
        end = error.end.col if error.end and error.end.line == line else start + 1
        message = error.message
        if error.hint:
            message += f"\n\nhelp: {error.hint}"
        return [{
            "range": {"start": {"line": line, "character": max(0, start)},
                      "end": {"line": line, "character": max(start + 1, end)}},
            "severity": 1,
            "source": "she",
            "message": message,
        }]
    except Exception:  # noqa: BLE001 - the editor must never see a crash
        return []


def line_prefix(text, position):
    lines = text.split("\n")
    row = position.get("line", 0)
    if row >= len(lines):
        return ""
    return lines[row][:position.get("character", 0)]


def complete(text, position):
    prefix = line_prefix(text, position)
    member = _MEMBER.search(prefix)
    items = []
    if member:
        owner = member.group(1)
        for name, doc in members_of(owner):
            items.append({"label": name, "kind": 2, "detail": f"{owner}.{name}",
                          "documentation": doc})
        if items:
            return {"isIncomplete": False, "items": items}
    for word in sorted(KEYWORDS):
        items.append({"label": word, "kind": 14,
                      "documentation": KEYWORD_DOCS.get(word, "")})
    for name, doc in global_names():
        items.append({"label": name, "kind": 3, "documentation": doc})
    return {"isIncomplete": False, "items": items}


def hover(text, position):
    lines = text.split("\n")
    row = position.get("line", 0)
    column = position.get("character", 0)
    line = lines[row] if row < len(lines) else ""
    start = column
    while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
        start -= 1
    stop = column
    while stop < len(line) and (line[stop].isalnum() or line[stop] in "_?"):
        stop += 1
    word = line[start:stop]
    if not word:
        return None
    if word in KEYWORD_DOCS:
        return {"contents": {"kind": "markdown",
                             "value": f"**{word}** — {KEYWORD_DOCS[word]}"}}
    owner_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\.$", line[:start])
    if owner_match:
        for name, doc in members_of(owner_match.group(1)):
            if name == word:
                return {"contents": {"kind": "markdown",
                                     "value": f"`{owner_match.group(1)}.{name}`\n\n{doc}"}}
    for name, doc in global_names():
        if name == word:
            return {"contents": {"kind": "markdown", "value": f"`{name}`\n\n{doc}"}}
    return None


def format_document(text, uri):
    from .formatter import format_source
    try:
        formatted = format_source(text, uri)
    except SheError:
        return None
    lines = text.split("\n")
    return [{
        "range": {"start": {"line": 0, "character": 0},
                  "end": {"line": len(lines), "character": 0}},
        "newText": formatted,
    }]


_CACHE = {}


def _interpreter():
    if "interp" not in _CACHE:
        from .interp import Interpreter
        from .sandbox import Sandbox
        _CACHE["interp"] = Interpreter(sandbox=Sandbox.locked())
    return _CACHE["interp"]


def global_names():
    interp = _interpreter()
    out = []
    for name, value in sorted(interp.globals.values.items()):
        out.append((name, (getattr(value, "doc", "") or "").split("\n")[0]))
    from .stdlib import DOCS, module_names
    for name in module_names():
        out.append((name, DOCS.get(name, "")))
    return out


def members_of(owner):
    from .stdlib import REGISTRY, load_module
    _interpreter()      # importing the stdlib is what fills REGISTRY
    if owner not in REGISTRY:
        return []
    key = f"members:{owner}"
    if key not in _CACHE:
        try:
            module = load_module(_interpreter(), owner)
        except SheError:
            return []
        _CACHE[key] = [(name, (getattr(value, "doc", "") or "").split("\n")[0])
                       for name, value in sorted(module.values.items())]
    return _CACHE[key]


if __name__ == "__main__":
    sys.exit(serve())
