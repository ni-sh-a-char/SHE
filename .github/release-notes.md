## SHE 2.0.3

Adds a warning when `--allow-run` is granted without naming a program.

Prompted by a question on Reddit: does a child `she` process stay capped by its
parent's grants? It does not — it parses its own flags and gets whatever it asks
for. But `she` is incidental, since `os.run("python", ["-c", ...])` reaches just as
far, so capping children would be theatre. Unscoped `--allow-run` is equivalent to
`--allow-all`, and now says so.

SECURITY.md and the permissions docs cover the property and point at scoping as the
mitigation. `tools/check_sandbox.py` pins both halves in CI.

---

## SHE 2.0.2

Fixes the first command in the install instructions failing on Windows.

pip installs `she.exe` into a per-user scripts folder that is not on `PATH` by default,
so `pip install she-lang` followed by `she run hello.she` — exactly what the README and
website said to do — failed for a lot of people. Nothing was wrong with the install;
`python -m she` worked all along and was simply undocumented.

The docs now cover the fallback and the `PATH` fix, and `she new` echoes back whichever
form you used to reach SHE rather than assuming `she` is on your path.

---

## SHE 2.0.1

A metadata fix on top of 2.0.0. The language, standard library and sandbox are unchanged.

The Buy Me a Coffee link used the wrong handle, which returned 404. PyPI releases are
immutable, so the README on the 2.0.0 project page could not be corrected in place —
this release exists to fix it. Tests now assert the funding link and the version agree
everywhere, so neither can drift into a release again.

Everything below describes SHE 2.0.

---

## SHE 2.0

A programming language that reads like English — and can't touch your machine unless you say so.

**[Try it in your browser](https://ni-sh-a-char.github.io/SHE/playground.html)** · **[Docs](https://ni-sh-a-char.github.io/SHE/docs.html)** · **[Examples](https://github.com/ni-sh-a-char/SHE/tree/main/examples)**

```sh
pip install she-lang
```

```she
let name = ask "What is your name?"
say "Hello, {name}!"

say [4, 8, 15, 16, 23, 42]
  |> filter(fun(n) -> n % 2 is 0)
  |> map(fun(n) -> n / 2)
  |> sum()
```

### What this release is

A complete rewrite. SHE 1.0 was a BASIC-style interpreter of about 2,200 lines that
could not carry types, modules, exceptions or pattern matching without collapsing.
The old interpreter is archived on the [`v1.0.0`](https://github.com/ni-sh-a-char/SHE/tree/v1.0.0)
branch, and the docs carry a [line-by-line migration table](https://ni-sh-a-char.github.io/SHE/docs.html#migrating).

### The language

English-keyword syntax with `end`-terminated blocks — no braces, no significant
whitespace. Real booleans and a real `nothing`. Text interpolation where a `{` that
holds no valid expression stays literal, so JSON and CSS need no escaping. `let`
immutable by default. Lists, maps, ranges, slices, destructuring and spread.
Functions with defaults, named arguments, rest parameters and closures. Types with
methods, inheritance and `setup`/`to_text` hooks. Pattern matching over literals,
ranges, guards, lists, maps and types. `try`/`catch`/`finally` with catch-by-kind.
Gradual typing. `async`/`await`. Modules and file imports. `test`/`expect` blocks.
Pipelines, safe navigation, and methods on every value.

### Permissions, which is the point

A program starts with no authority at all — no files, no network, no processes, no
environment:

```sh
she run report.she                       # arithmetic only
she run report.she --allow-read=./data   # now it can read that one folder
```

Anything ungranted fails with a message naming the exact flag that would allow it.
`tools/check_sandbox.py` asserts 11 refusals and 7 allowances on every push.

### Included

`crypto` wraps [Kaalka](https://github.com/PIYUSH-MISHRA-00/Kaalka-Encryption-Algorithm)
with base64-armoured `seal`/`open` and checksummed `envelope`/`open_envelope`, alongside
vetted `hash`, `hmac`, `password_hash` and `token`. `web` wraps
[WebWeaveX](https://github.com/ni-sh-a-char/WebWeaveX) for deterministic extraction and
graph queries. Both optional; both fail with a clear install message.

> Kaalka is a novel construction that has not been through public cryptanalysis. SHE
> ships it for time-keyed handoff, puzzles and teaching, and says so in the module,
> the docs and [SECURITY.md](https://github.com/ni-sh-a-char/SHE/blob/main/SECURITY.md).
> For secrets that matter, use the vetted primitives in the same module.

### Tooling

REPL, `run`, `test`, `fmt`, `check`, `new`, `doc`, `lsp`. A formatter that works on
tokens so comments survive. A language server. A VS Code extension. A browser
playground running the real interpreter via Pyodide.

### Verified

145 Python tests and 8 SHE tests across Linux, macOS and Windows on Python 3.9, 3.11
and 3.13, plus lint, sandbox and packaging jobs. Ten runnable examples.

The full [changelog](https://github.com/ni-sh-a-char/SHE/blob/main/CHANGELOG.md) lists
the eight defects carried over from 1.0 that this release fixes, each now covered by a test.

---

SHE is free and Apache 2.0. If it saved you time, [a coffee](https://buymeacoffee.com/piyushmishra00) keeps it moving — and a star helps others find it.
