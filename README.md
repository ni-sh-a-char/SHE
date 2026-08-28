<div align="center">

<img src="site/assets/logo.svg" width="112" height="112" alt="SHE logo">

# SHE

**A programming language that reads like English — and can't touch your machine unless you say so.**

[![CI](https://github.com/ni-sh-a-char/SHE/actions/workflows/ci.yml/badge.svg)](https://github.com/ni-sh-a-char/SHE/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/she-lang?color=7C3AED&label=pypi)](https://pypi.org/project/she-lang/)
[![Python](https://img.shields.io/badge/python-3.9%2B-4F46E5)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-06B6D4)](LICENCE)
[![Try it](https://img.shields.io/badge/try%20it-in%20your%20browser-7C3AED)](https://ni-sh-a-char.github.io/SHE/playground.html)

[**Try it now**](https://ni-sh-a-char.github.io/SHE/playground.html) · [**Docs**](https://ni-sh-a-char.github.io/SHE/docs.html) · [**Examples**](examples/) · [**Discussions**](https://github.com/ni-sh-a-char/SHE/discussions)

</div>

---

```she
let name = ask "What is your name?"
say "Hello, {name}!"

let numbers = [4, 8, 15, 16, 23, 42]

say numbers
  |> filter(fun(n) -> n % 2 is 0)
  |> map(fun(n) -> n / 2)
  |> sum()
```

That is the whole language: say what you mean, in the order you'd say it out loud.

---

## Why another language?

Most languages ask you to choose. Readable **or** capable. Friendly **or** safe. A toy you outgrow in a week, or a professional tool with a month-long ramp.

SHE refuses the trade.

### 1. It reads like a sentence

No braces. No semicolons. No significant whitespace to get wrong. Blocks end with `end`, comparisons use `is`, and loops say `for each item in items`. A person who has never programmed can read a SHE file and mostly follow it.

```she
type Account has owner: text, balance: number = 0
  fun deposit(self, amount)
    if amount <= 0 then throw "a deposit has to be positive"
    self.balance += amount
    return self.balance
  end
end

let account = Account("Ada")
say account.deposit(50)
```

But it is not verbose. There is no `public static void`, no ceremony, no boilerplate file you must write before the first line that does something.

### 2. It has no power until you grant it

**This is the part that matters.** A SHE program starts with *nothing*: it cannot read a file, open a socket, start a process, or read an environment variable.

```sh
she run report.she                       # arithmetic only — nothing else is possible
she run report.she --allow-read=./data   # now it can read that one folder
she run report.she --allow-net=api.stripe.com
```

Try to do something ungranted and SHE tells you exactly which flag would allow it:

```
PermissionError: report.she tried to read files from disk (~/.ssh/id_rsa),
                 but was not given permission
  --> report.she:14:12
     |
  14 |   let key = fs.read("~/.ssh/id_rsa")
     |             ^^^^^^^
  help: run it with `--allow-read=~/.ssh/id_rsa` to permit this,
        or `--allow-all` while you are developing.
```

You can hand someone a SHE script and know from the command line alone what it is able to touch. That is a property no mainstream scripting language gives you.

### 3. The errors teach instead of scold

Every error points at the source, says what went wrong in plain words, and suggests the fix.

```
NameError: `totl` has not been defined yet
  --> budget.she:7:5
     |
   7 | say totl
     |     ^^^^
  help: did you mean `total`?
```

```
TypeError: `x` was declared with `let`, so it cannot be changed
  --> counter.she:3:1
     |
   3 | x = 2
     | ^
  help: use `var x = ...` if it needs to change.
```

---

## Install

```sh
pip install she-lang
```

Then:

```sh
she                          # interactive prompt
she run hello.she            # run a program
she new my-project           # scaffold a project
she test                     # run tests
she fmt                      # format code
```

Nothing to compile, no toolchain to install. If you have Python 3.9+, you have SHE.

> **`she: command not found`?**
> `python -m she` does the same thing and always works — `python -m she run hello.she`.
>
> This happens when pip installs into a per-user folder that isn't on your `PATH`.
> It is common on Windows and on macOS/Linux with `pip install --user`. To fix it
> properly, add the folder pip named in its install warning to your `PATH`:
>
> ```powershell
> # Windows PowerShell, then open a new terminal
> $s = python -c "import sysconfig; print(sysconfig.get_path('scripts','nt_user'))"
> [Environment]::SetEnvironmentVariable("PATH", "$([Environment]::GetEnvironmentVariable('PATH','User'));$s", "User")
> ```
>
> ```sh
> # macOS / Linux, then reopen your shell
> echo 'export PATH="$PATH:'"$(python3 -m site --user-base)"'/bin"' >> ~/.zshrc
> ```
>
> A virtual environment sidesteps it entirely, and is the better habit anyway:
> `python -m venv .venv` then `.venv\Scripts\activate` (Windows) or
> `source .venv/bin/activate`.

**Optional extras** — SHE works fully without these:

```sh
pip install "she-lang[all]"   # adds the crypto and web modules
```

`crypto` works on any supported Python. `web` wraps WebWeaveX, which needs
Python 3.10 or newer — on 3.9 it is skipped and the module tells you so.

---

## A tour in sixty seconds

<table>
<tr><td width="50%" valign="top">

**Values and text**

```she
let pi = 3.14159        # cannot change
var count = 0           # can change
count += 1

say "pi is about {pi}"
say "a {{literal}} brace"
```

**Deciding**

```she
if age >= 18
  say "you can vote"
else if age >= 16
  say "nearly there"
else
  say "not yet"
end

let price = if member then 20 else 40
```

**Repeating**

```she
for each item in shopping
  say item
end

for each n in 1..10 by 2
  say n
end

repeat
  tries += 1
until tries >= 3
```

</td><td width="50%" valign="top">

**Functions**

```she
fun greet(who = "world") -> "Hello, {who}!"

fun total(...numbers) -> sum(numbers)

let double = fun(n) -> n * 2

say rectangle(width: 4, height: 3)
```

**Matching**

```she
match value
  case 0 -> "nothing"
  case 1 | 2 | 3 -> "a few"
  case n if n < 0 -> "below zero"
  case [first, ...rest] -> "a list"
  case {name: n} -> "called {n}"
  case Point(x, y) -> "at {x},{y}"
  case _ -> "something else"
end
```

**When things go wrong**

```she
try
  risky()
catch e: MathError
  say "maths problem: {e.message}"
catch e
  say "something else: {e.kind}"
finally
  say "cleaned up"
end
```

</td></tr>
</table>

---

## Everything it has

| | |
|---|---|
| **Values** | numbers, text, booleans, `nothing`, lists, maps, ranges, functions, your own types |
| **Text** | interpolation `"hi {name}"`, triple-quoted blocks, raw `r"..."`, full text library |
| **Control flow** | `if`/`else if`/`else`, `while`, `repeat until`, `for each`, `break`, `skip`, `match` |
| **Functions** | defaults, named arguments, rest `...args`, spread, closures, lambdas, recursion |
| **Types** | `type X has a, b`, methods, inheritance, `setup` and `to_text` hooks |
| **Pattern matching** | literals, ranges, or-patterns, guards, list and map destructuring, type patterns |
| **Errors** | `try`/`catch`/`finally`, `throw`, catch by kind, `assert` |
| **Gradual typing** | `let n: number`, `fun f(a: text): number`, unions — checked at runtime, never required |
| **Concurrency** | `async fun`, `await`, `await` a whole list of tasks |
| **Modules** | `import math`, `from math import sqrt`, `use "./helpers.she" as helpers` |
| **Modern sugar** | pipelines `\|>`, safe navigation `?.`, defaults `??`, method syntax on every value |
| **Testing** | `test "name" ... end` blocks with `expect`, run by `she test` |
| **Security** | capability sandbox, step and time budgets, vetted crypto primitives |
| **Tooling** | REPL, formatter, test runner, project scaffolder, doc browser, language server |

Full reference: **[ni-sh-a-char.github.io/SHE/docs.html](https://ni-sh-a-char.github.io/SHE/docs.html)**

---

## Batteries included

```she
import math      # sqrt, round, clamp, prime?, mean, median, stdev, trigonometry
import json      # parse, stringify, pretty
import re        # matches?, find_all, replace, split
import time      # now, today, format, parse, sleep
import random    # whole, choice, shuffle, dice, uuid
import csv       # parse, stringify
import crypto    # hash, hmac, password_hash, token, Kaalka encryption
import fs        # read, write, list, walk           [needs --allow-read/write]
import http      # get, post, json, download          [needs --allow-net]
import os        # env, run, platform                 [needs --allow-env/run]
import web       # extract, crawl, fingerprint        [needs --allow-net]
```

`text`, `list`, `math`, `json`, `re`, `time` and `random` are always available — no import needed. Everything that can touch the outside world must be imported *and* granted.

---

## Two libraries, built in

SHE ships first-class bindings for two projects, exposed as ordinary modules.

### `crypto` — [Kaalka](https://github.com/PIYUSH-MISHRA-00/Kaalka-Encryption-Algorithm)

Encryption whose key is a moment in time.

```she
import crypto

let sealed = crypto.seal("meet at the bridge", "14:35:22")
say crypto.open(sealed, "14:35:22")

# Envelopes add sender, recipient and a checksum
let packet = crypto.envelope("the eagle has landed", "ada", "bob")
say crypto.open_envelope(packet, "bob")
```

`seal` / `open` armour Kaalka's output as base64 so ciphertext survives a file, a URL or a JSON field — raw Kaalka output does not.

> **Said plainly:** Kaalka is a novel construction that has not been through public cryptanalysis. SHE ships it for time-keyed handoff, puzzles and teaching. For secrets that matter, the same module gives you `crypto.hash`, `crypto.hmac`, `crypto.password_hash` and `crypto.token`, which wrap vetted primitives. A language should be honest about which is which.

### `web` — [WebWeaveX](https://github.com/ni-sh-a-char/WebWeaveX)

Turn a live app, a repository or a document into a deterministic graph.

```she
import web

let graph = web.extract("https://example.com", "web")
say "{web.nodes(graph).length} nodes, {web.edges(graph).length} edges"

# The same input always produces the same identity
say web.fingerprint(graph)
```

---

## Editor support

The VS Code extension in [`editors/vscode`](editors/vscode) gives syntax highlighting, snippets, and live diagnostics via SHE's built-in language server.

```sh
cd editors/vscode && npm install && npm run package
code --install-extension she-lang-2.0.3.vsix
```

Any editor that speaks LSP can use `she lsp` directly.

---

## Who it is for

**Never programmed before?** Start with [`examples/01-hello.she`](examples/01-hello.she). The errors are written for you, and nothing you run can damage anything.

**A student?** Every feature you will be taught — recursion, closures, pattern matching, types, concurrency — is here, without a build system in the way.

**A developer?** Pipelines, destructuring, gradual types, a real test runner, a formatter and an LSP. `pip install`, and the whole toolchain is there.

**Security work?** Capability sandboxing, step and time budgets for running untrusted code, hashing, HMAC, password storage and token generation in the box.

**A team?** Scripts whose reach is declared on the command line and enforced by the runtime. Code review of a SHE script means reading one line of flags.

---

## Contributing

Contributions are genuinely welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

```sh
git clone https://github.com/ni-sh-a-char/SHE.git
cd SHE
pip install -e ".[dev]"
pytest              # the Python test suite
she test examples   # SHE's own tests
```

Good first issues are labelled [`good first issue`](https://github.com/ni-sh-a-char/SHE/labels/good%20first%20issue). Adding a standard-library function is about ten lines and a docstring.

---

## Support the project

SHE is free, Apache-2.0, and built in the open. If it saved you time, taught you something, or you just want to see it keep going:

<a href="https://buymeacoffee.com/piyushmishra00">
  <img src="https://img.shields.io/badge/Buy%20me%20a%20coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black" alt="Buy me a coffee">
</a>

Starring the repo helps more people find it, and costs nothing. ⭐

---

## Versions

| Version | What it is |
|---|---|
| **2.0** (`main`) | The language documented here — rewritten from scratch |
| **1.0** (`v1.0.0` branch) | The original BASIC-style interpreter, kept for history |

SHE 2.0 is not compatible with 1.0. The [changelog](CHANGELOG.md) explains why, and what changed.

---

## Licence

Apache 2.0 — see [LICENCE](LICENCE). Use it for anything, including commercially.

<div align="center">
<br>
<sub>Built by <a href="https://github.com/PIYUSH-MISHRA-00">Piyush Mishra</a> · <a href="https://ni-sh-a-char.github.io/SHE/">ni-sh-a-char.github.io/SHE</a></sub>
</div>
