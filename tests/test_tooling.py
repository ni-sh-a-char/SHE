"""The formatter, the CLI and the language server.

The formatter especially: one that mangles code is worse than none at all, so
every rule it applies is pinned here.
"""

import io
import json
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from she.errors import SheError  # noqa: E402
from she.formatter import format_source  # noqa: E402


def fmt(source):
    return format_source(source, "<test>")


# --- formatting -------------------------------------------------------------

def test_normalises_spacing():
    assert fmt("let  x=1+2\n") == "let x = 1 + 2\n"


def test_hugs_brackets_and_commas():
    assert fmt("f( a ,b )\n") == "f(a, b)\n"
    assert fmt("let xs=[ 1,2 , 3 ]\n") == "let xs = [1, 2, 3]\n"


def test_keeps_comments():
    assert fmt("let x = 1   # why\n") == "let x = 1  # why\n"


def test_does_not_touch_text():
    assert fmt('say "  keep   these   spaces  "\n') == 'say "  keep   these   spaces  "\n'


def test_hash_inside_text_is_not_a_comment():
    assert fmt('say "a # not a comment"\n') == 'say "a # not a comment"\n'


def test_indents_blocks():
    source = "if x\nsay 1\nelse\nsay 2\nend\n"
    assert fmt(source) == "if x\n  say 1\nelse\n  say 2\nend\n"


def test_leaves_one_liners_alone():
    assert fmt("if x then say 1\n") == "if x then say 1\n"
    assert fmt("fun f(a) -> a + 1\n") == "fun f(a) -> a + 1\n"


def test_type_header_is_not_a_block():
    source = "type Point has x, y\nlet p = Point(1, 2)\n"
    assert fmt(source) == source


def test_negative_numbers_keep_their_sign():
    assert fmt("let xs = [1, -2, 3]\n") == "let xs = [1, -2, 3]\n"
    assert fmt("let n = 3 - 2\n") == "let n = 3 - 2\n"


def test_ranges_hug():
    """`1..5`, not `1 ..5`."""
    assert fmt("for each n in 1..5\nsay n\nend\n") == "for each n in 1..5\n  say n\nend\n"
    assert fmt("let r = 0..<10\n") == "let r = 0..<10\n"


def test_spread_keeps_its_space():
    """`...` is a spread, not a range, even though it starts with two dots."""
    assert fmt("let ys = [a, ...rest]\n") == "let ys = [a, ...rest]\n"
    assert fmt("fun total(...numbers) -> sum(numbers)\n") \
        == "fun total(...numbers) -> sum(numbers)\n"


def test_slice_colon_hugs_but_map_colon_does_not():
    assert fmt("say xs[1:3]\n") == "say xs[1:3]\n"
    assert fmt("let m = {a:1}\n") == "let m = {a: 1}\n"


def test_method_call_on_a_literal_hugs():
    assert fmt('say "hi".repeat(3)\n') == 'say "hi".repeat(3)\n'


def test_indents_multi_line_pipelines():
    source = "say numbers\n|> filter(f)\n|> sum()\n"
    assert fmt(source) == "say numbers\n  |> filter(f)\n  |> sum()\n"


def test_indents_multi_line_literals():
    source = 'let m = {\nname: "Ada",\nborn: 1815,\n}\n'
    assert fmt(source) == 'let m = {\n  name: "Ada",\n  born: 1815,\n}\n'


def test_multi_line_literal_inside_a_block():
    source = "fun f()\nlet m = {\na: 1,\n}\nend\n"
    assert fmt(source) == "fun f()\n  let m = {\n    a: 1,\n  }\nend\n"


def test_collapses_runs_of_blank_lines():
    assert fmt("let a = 1\n\n\n\nlet b = 2\n") == "let a = 1\n\nlet b = 2\n"


def test_is_idempotent():
    source = """
# a program using most of the syntax
type Point has x, y
  fun length(self) -> math.sqrt(self.x ^ 2 + self.y ^ 2)
end

fun classify(n)
  if n < 0 then return "negative"
  return match n
    case 0 -> "zero"
    case 1..9 -> "small"
    case _ -> "large"
  end
end

let numbers = [1, -2, 3]
say numbers
  |> filter(fun(n) -> n > 0)
  |> sum()

let m = {
  a: 1,
  b: [1, 2, 3],
}
say m.a, numbers[0:2], Point(3, 4).length()
"""
    once = fmt(source)
    assert fmt(once) == once, "formatting twice should change nothing the second time"


def test_formatted_code_still_parses():
    from she.parser import parse
    source = "if x\nsay [1,-2]\nend\nfor each n in 1..3\nsay n\nend\n"
    parse(fmt(source), "<test>")


def test_refuses_to_format_broken_code():
    with pytest.raises(SheError):
        fmt('say "never closed\n')


def test_every_example_is_already_formatted():
    """CI enforces this, so a drifting example fails here first."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    examples = os.path.join(root, "examples")
    unformatted = []
    for name in sorted(os.listdir(examples)):
        if not name.endswith(".she"):
            continue
        path = os.path.join(examples, name)
        with open(path, encoding="utf-8") as handle:
            original = handle.read()
        if format_source(original, path) != original:
            unformatted.append(name)
    assert not unformatted, f"run `she fmt examples`: {unformatted}"


# --- the command line -------------------------------------------------------

def run_cli(*args, **kwargs):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return subprocess.run([sys.executable, "-m", "she", *args],
                          capture_output=True, text=True, cwd=root, timeout=90, **kwargs)


def test_cli_reports_its_version():
    done = run_cli("--version")
    assert done.returncode == 0
    assert "SHE" in done.stdout


def test_cli_runs_a_file(tmp_path):
    script = tmp_path / "hello.she"
    script.write_text('say "from the cli"\n', encoding="utf-8")
    done = run_cli("run", str(script))
    assert done.returncode == 0, done.stderr
    assert "from the cli" in done.stdout


def test_cli_refuses_without_permission(tmp_path):
    script = tmp_path / "peek.she"
    script.write_text('import fs\nsay fs.read("anything.txt")\n', encoding="utf-8")
    done = run_cli("run", str(script))
    assert done.returncode == 1
    assert "PermissionError" in done.stderr
    assert "--allow-read" in done.stderr


def test_cli_allows_with_permission(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello from a file", encoding="utf-8")
    script = tmp_path / "peek.she"
    script.write_text(f'import fs\nsay fs.read({str(target)!r})\n', encoding="utf-8")
    done = run_cli("run", str(script), f"--allow-read={tmp_path}")
    assert done.returncode == 0, done.stderr
    assert "hello from a file" in done.stdout


def test_cli_reports_a_syntax_error_with_position(tmp_path):
    script = tmp_path / "broken.she"
    script.write_text("let x = \n", encoding="utf-8")
    done = run_cli("run", str(script))
    assert done.returncode == 1
    assert "SyntaxError" in done.stderr


def test_cli_new_scaffolds_a_project(tmp_path):
    done = run_cli("new", str(tmp_path / "demo"))
    assert done.returncode == 0, done.stderr
    for name in ("main.she", "she.toml", "README.md"):
        assert (tmp_path / "demo" / name).is_file()
    ran = run_cli("run", str(tmp_path / "demo" / "main.she"))
    assert ran.returncode == 0, ran.stderr
    assert "Hello" in ran.stdout


def test_cli_runs_the_scaffolded_test(tmp_path):
    run_cli("new", str(tmp_path / "demo"))
    done = run_cli("test", str(tmp_path / "demo"))
    assert done.returncode == 0, done.stderr
    assert "1 passed" in done.stdout


def test_cli_doc_lists_modules():
    done = run_cli("doc")
    assert done.returncode == 0
    for module in ("math", "crypto", "fs", "web"):
        assert module in done.stdout


def test_cli_check_accepts_the_examples():
    done = run_cli("check", "examples")
    assert done.returncode == 0, done.stderr


def test_cli_rejects_an_unknown_permission(tmp_path):
    script = tmp_path / "x.she"
    script.write_text("say 1\n", encoding="utf-8")
    done = run_cli("run", str(script), "--allow-everything")
    assert done.returncode == 2
    assert "unknown permission" in done.stderr


# --- the language server ----------------------------------------------------

def lsp_exchange(messages):
    """Speak LSP to `she lsp` over stdin/stdout and collect the replies."""
    body = b""
    for message in messages:
        payload = json.dumps(message).encode()
        body += f"Content-Length: {len(payload)}\r\n\r\n".encode() + payload
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    done = subprocess.run([sys.executable, "-m", "she", "lsp"], input=body,
                          capture_output=True, cwd=root, timeout=90)
    out = done.stdout.decode("utf-8", "replace")
    return [json.loads(chunk.split("\r\n\r\n", 1)[1])
            for chunk in ("\x00" + out).split("Content-Length: ")[1:]
            if "\r\n\r\n" in chunk]


def test_lsp_initialises_and_reports_a_syntax_error():
    replies = lsp_exchange([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": "file:///a.she", "languageId": "she",
                             "version": 1, "text": "let x = \n"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
        {"jsonrpc": "2.0", "method": "exit"},
    ])
    initialise = next(r for r in replies if r.get("id") == 1)
    assert initialise["result"]["capabilities"]["hoverProvider"] is True

    published = next(r for r in replies
                     if r.get("method") == "textDocument/publishDiagnostics")
    diagnostics = published["params"]["diagnostics"]
    assert len(diagnostics) == 1
    assert diagnostics[0]["severity"] == 1
    assert "range" in diagnostics[0]


def test_lsp_says_nothing_about_valid_code():
    replies = lsp_exchange([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": "file:///b.she", "languageId": "she",
                             "version": 1, "text": 'say "fine"\n'}}},
        {"jsonrpc": "2.0", "method": "exit"},
    ])
    published = next(r for r in replies
                     if r.get("method") == "textDocument/publishDiagnostics")
    assert published["params"]["diagnostics"] == []


def test_lsp_completes_module_members():
    replies = lsp_exchange([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": "file:///c.she", "languageId": "she",
                             "version": 1, "text": "say math."}}},
        {"jsonrpc": "2.0", "id": 2, "method": "textDocument/completion", "params": {
            "textDocument": {"uri": "file:///c.she"},
            "position": {"line": 0, "character": 9}}},
        {"jsonrpc": "2.0", "method": "exit"},
    ])
    completion = next(r for r in replies if r.get("id") == 2)
    labels = [item["label"] for item in completion["result"]["items"]]
    assert "sqrt" in labels
    assert "median" in labels


# --- packaging metadata -----------------------------------------------------

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNDING = "https://buymeacoffee.com/piyushmishra00"


def read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_the_funding_link_is_the_same_everywhere():
    """A wrong handle shipped to PyPI once, where releases are immutable and the
    only fix is a new version. Every copy of the link is checked here now."""
    wrong = []
    for name in ("README.md", "pyproject.toml", "CONTRIBUTING.md",
                 "docs/README.md", ".github/FUNDING.yml", ".github/release-notes.md",
                 "site/index.html", "site/docs.html", "site/playground.html"):
        text = read(*name.split("/"))
        for found in re.findall(r"https://buymeacoffee\.com/[A-Za-z0-9_-]+", text):
            if found != FUNDING:
                wrong.append(f"{name}: {found}")
    assert not wrong, "these point at the wrong Buy Me a Coffee handle: " + "; ".join(wrong)


def test_the_readme_pypi_will_show_has_a_working_funding_link():
    """pyproject points long_description at README.md, so this is the text that
    ends up on the PyPI project page."""
    readme = read("README.md")
    assert FUNDING in readme
    assert 'readme = "README.md"' in read("pyproject.toml")


def test_the_version_is_the_same_everywhere():
    import she
    version = she.__version__
    assert f'version = "{version}"' in read("pyproject.toml")
    assert f'version = "{version}"' in read("she.toml")
    assert f'"version": "{version}"' in read("editors", "vscode", "package.json")
