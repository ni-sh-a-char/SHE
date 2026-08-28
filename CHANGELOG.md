# Changelog

All notable changes to SHE. This project follows [semantic versioning](https://semver.org).

## [2.0.2] — 2026-08-28

### Fixed

- **`she: command not found` after a successful install.** pip puts `she.exe` in
  a per-user scripts folder that is not on `PATH` by default on Windows, nor
  after `pip install --user` on macOS and Linux. The install instructions in the
  README and on the website therefore failed on their very first command for a
  large share of users. Nothing was wrong with the install — `python -m she`
  worked throughout — it simply was not documented.
- The README, the docs site and its sidebar now cover the fallback and the
  `PATH` fix for both Windows and Unix, plus the virtual-environment approach
  that avoids the problem entirely.
- `she new` and the unknown-command error echo back whichever form was used to
  reach SHE, so a user who can only run `python -m she` is no longer told to run
  `she run main.she` next.

### Added

- Tests covering all three, including that `python -m she` remains a supported
  entry point now that the docs point people at it.

## [2.0.1] — 2026-08-27

A metadata fix. No change to the language, the standard library or the sandbox.

### Fixed

- The Buy Me a Coffee link used the wrong handle
  (`buymeacoffee.com/piyushmishra`, which returns 404). PyPI releases are
  immutable, so the README shown on the 2.0.0 project page could not be
  corrected in place — hence this release.
- Added `.github/FUNDING.yml`, which is what renders the Sponsor button on the
  repository and on every issue and pull request.

### Added

- Tests asserting the funding link is identical everywhere, and that the version
  agrees across `she/__init__.py`, `pyproject.toml`, `she.toml` and the VS Code
  extension — so neither can drift into a release again.

## [2.0.0] — 2026-08-27

A complete rewrite. SHE 2.0 does not run SHE 1.0 programs; the old interpreter is
archived on the `v1.0.0` branch, and [the docs](https://ni-sh-a-char.github.io/SHE/docs.html#migrating)
carry a line-by-line translation table.

### Why rewrite

SHE 1.0 was a BASIC-style tree-walking interpreter of about 2,200 lines. It could
not carry types, modules, exceptions or pattern matching without collapsing, and
its ALL-CAPS syntax (`VAR`, `THEN`, `END`) was the opposite of the goal. It also
shipped real defects — see *Fixed* below.

### Added

**The language**

- English-keyword syntax with `end`-terminated blocks. No braces, no significant
  whitespace.
- Real booleans (`true` / `false`) and a real `nothing`, distinct from `0`.
- Text interpolation `"hi {name}"`, triple-quoted blocks, raw strings `r"..."`.
  A `{` that does not hold a valid expression stays literal, so JSON and CSS
  need no escaping.
- `let` (immutable) and `var` (mutable). Reassigning a `let` is an error.
- Maps `{a: 1}`, ranges `1..10` and `1..<10`, slices `xs[1:3]`, negative indexing.
- `for each x in xs`, index-and-value loops, map iteration, `repeat`/`until`,
  `skip` and `break`.
- Functions with defaults, named arguments, rest parameters `...args`, spread,
  closures, lambdas and doc strings.
- `type X has a, b` with methods, inheritance via `from`, and the `setup` and
  `to_text` hooks.
- `match` with literal, range, or-pattern, guard, list, map and type patterns,
  plus destructuring in `let` and loop targets.
- `try` / `catch` / `finally`, `throw`, catching by error kind, `assert`.
- Gradual typing on variables, parameters and returns, including unions.
- `async fun` and `await`, including awaiting a list of tasks.
- Modules: `import`, `from ... import`, and `use "./file.she"`.
- `test "..." end` blocks with `expect`, run by `she test`.
- Pipelines `|>`, safe navigation `?.`, default `??`, and method syntax on every
  value (`"hi".upper()` and `text.upper("hi")` are the same call).

**Security**

- A capability sandbox. Programs start with no authority; `--allow-read`,
  `--allow-write`, `--allow-net`, `--allow-run`, `--allow-env` and `--allow-time`
  grant it, and can be narrowed to specific paths or hosts.
- Step, time and recursion budgets (`--max-steps`, `--timeout`, `--max-depth`).
- Permission errors name the exact flag that would have allowed the call.
- `tools/check_sandbox.py` asserts all of this in CI on every push.

**Standard library** — `text`, `list`, `maps`, `math`, `json`, `re`, `time`,
`random`, `csv`, `crypto`, `fs`, `http`, `os`, `web`. Around 300 functions, each
with a docstring that `she doc`, `help()` and editor hover all read.

**Integrations**

- `crypto` wraps [Kaalka](https://github.com/PIYUSH-MISHRA-00/Kaalka-Encryption-Algorithm),
  adding `seal`/`open` (base64-armoured, so ciphertext survives files and URLs)
  and `envelope`/`open_envelope` (addressed and HMAC-checksummed).
- `web` wraps [WebWeaveX](https://github.com/ni-sh-a-char/WebWeaveX) for
  deterministic extraction and graph queries.
- Both are optional extras; the modules fail with a clear install message rather
  than at import.

**Tooling**

- `she` REPL with `:help`, `:env`, `:type`, `:time`, `:load`, `:grant`, `:perms`.
- `she run`, `she test`, `she fmt`, `she check`, `she new`, `she doc`, `she lsp`.
- A formatter that works on tokens, so comments and blank lines survive.
- A language server (diagnostics, completion, hover, formatting) over stdio.
- A VS Code extension with highlighting, snippets and LSP support.
- A browser playground running the real interpreter through Pyodide.
- CI across Linux, macOS and Windows on Python 3.9–3.13.

### Fixed

Defects carried over from 1.0, each now covered by a test:

- **The interpreter crashed on import without `kaalka` installed.** `lexer.py`
  imported it at module scope and never used it. Kaalka is now an optional extra,
  loaded only when the `crypto` module is first used.
- **`skip_comment()` looped forever** on a file ending in a comment with no
  trailing newline.
- **Lists were silently shared.** `List.copy()` reused the same element list, so
  `let b = a + 4` mutated `a`. Lists are now copied properly.
- **`KAALKA_ENCRYPT(message)` always failed** even though the README documented
  the timestamp as optional — argument checking required exactly two. Optional
  arguments now work as documented.
- **Shared singletons were mutated.** `Number.null`, `Number.true` and
  `Number.false` were single objects whose position and context were overwritten
  on every use, corrupting error locations.
- **Strings could not be compared.** `"a" == "a"` raised "Illegal operation".
- **`CLEAR()` ran `cls` on every platform**, including where it does not exist.
- **The README documented `IS_STRING`; the interpreter registered `IS_STR`.**

### Removed

- The entire v1 syntax. See the [migration table](https://ni-sh-a-char.github.io/SHE/docs.html#migrating).
- `docs/README.md`, which described a statically typed compiled language with an
  ahead-of-time compiler, actors, an LSP and a Homebrew tap — none of which
  existed. It has been replaced with documentation of what SHE actually does.
- `github.sh` and `activity_log.md`, which were not part of the language.

### Changed

- Booleans are no longer `1` and `0`.
- `10 / 2` prints `5`, not `5.0`.
- Indexing is `xs[0]`, not `xs / 0`.
- The dictionary module is `maps`, not `map`, so it can never shadow the `map`
  function.
- Package name on PyPI is `she-lang`; the import name stays `she`.
- Licence file recognised as Apache-2.0 via PEP 639 metadata.

## [1.0.0] — archived

The original interpreter, kept on the `v1.0.0` branch for history. Unmaintained.

[2.0.2]: https://github.com/ni-sh-a-char/SHE/releases/tag/v2.0.2
[2.0.1]: https://github.com/ni-sh-a-char/SHE/releases/tag/v2.0.1
[2.0.0]: https://github.com/ni-sh-a-char/SHE/releases/tag/v2.0.0
