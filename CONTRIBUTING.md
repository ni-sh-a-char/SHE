# Contributing to SHE

Thanks for being here. SHE is a young language and there is a lot of useful work
that does not require knowing anything about compilers.

## Getting set up

```sh
git clone https://github.com/ni-sh-a-char/SHE.git
cd SHE
pip install -e ".[dev,all]"

pytest                      # the Python test suite
she test examples           # SHE's own tests, written in SHE
python tools/check_sandbox.py   # proves the sandbox still holds
ruff check she tools        # lint
```

All four run in CI on every push, across Linux, macOS and Windows and Python 3.9
through 3.13. If they pass locally they will almost certainly pass there.

## Good first contributions

**Add a standard-library function.** This is about ten lines. Open the right file
in `she/stdlib/`, write a plain Python function with a one-line docstring, and add
it to the dict at the bottom of the module:

```python
def initials(s):
    """The first letter of each word, joined by dots."""
    return ".".join(w[0].upper() for w in _need_text(s, "initials").split() if w)
```

The docstring is not decoration — it is what `she doc text`, `help(text)` and the
editor hover all show. Write it for someone who has never programmed.

Then add a test in `tests/test_language.py` and you are done.

**Improve an error message.** If a message ever confused you, that is a bug worth
fixing. Every error takes a `hint=`, and the hint should say what to *do*, not
restate the problem. Compare:

```python
raise TypeErr("invalid operand type")                      # unhelpful
raise TypeErr(f"you cannot add a {type_name(a)} and a {type_name(b)}",
              hint='to build text use interpolation: "total: {value}".')
```

**Write an example.** `examples/` is documentation people actually read. A good
example does one thing, runs cleanly, and has a test at the bottom.

**Improve the docs or the site.** `site/` is plain HTML and CSS with no build step.
Open `site/index.html` in a browser and edit.

## Working on the language itself

The interpreter is about 5,000 lines and deliberately readable:

| File | What it does |
|---|---|
| `she/lexer.py` | Source text → tokens. Handles interpolation. |
| `she/parser.py` | Tokens → AST. Recursive descent, precedence climbing. |
| `she/ast.py` | The node types. Plain data. |
| `she/interp.py` | Walks the AST. Where evaluation happens. |
| `she/values.py` | The runtime value model. |
| `she/sandbox.py` | Capabilities and budgets. |
| `she/stdlib/` | The standard library. |
| `she/formatter.py` | `she fmt`. Works on tokens so comments survive. |
| `she/lsp.py` | The language server. |
| `she/cli.py` | The `she` command. |

**Adding syntax** usually touches four places: a keyword in `lexer.py`, a node in
`ast.py`, a `stmt_*` or expression rule in `parser.py`, and a visitor in
`interp.py` registered in the dispatch table at the bottom of the file.

## The rules we hold to

**1. Errors must be actionable.** Every error says what went wrong in plain words,
points at the source, and where possible suggests the fix. A message a beginner
cannot act on is a bug.

**2. The sandbox is not negotiable.** Any new function that touches the filesystem,
the network, the environment or another process *must* ask
`interp.sandbox.require(...)` before doing anything. `tools/check_sandbox.py` will
catch you if you forget, and you should add your case to it.

**3. Nothing is claimed that is not true.** If a feature has a limit, the docs say
so — see how `async` and Kaalka are described. Overselling is how projects lose
trust, and it is much harder to win back than to keep.

**4. New dependencies need a real argument.** SHE has zero required dependencies
and that is a feature. `kaalka` and `webweavex` are optional extras, and the
modules that use them fail with a clear install message rather than at import.

**5. Every change lands with a test.** `tests/test_language.py` is organised by
feature; put yours next to its neighbours.

## Style

- Python: `ruff check she tools` must pass. 100 columns.
- SHE: `she fmt` must leave your file unchanged.
- British or American spelling both fine — SHE aliases `capitalise`/`capitalize`
  and `centre`/`center` for the same reason.

## Pull requests

Small and focused beats large and sweeping. Say what problem you are solving and,
if it changes behaviour, show a before and after. If you are unsure whether an idea
fits, open an issue first — that is cheaper than writing code that gets turned down.

## Reporting bugs

Include the SHE version (`she --version`), the smallest program that shows the
problem, what you expected, and what happened. A three-line reproduction is worth
more than three paragraphs of description.

## Security

Do not open a public issue for a sandbox escape. See [SECURITY.md](SECURITY.md).

## Not writing code?

Reporting a confusing error message, or telling us which bit of syntax
made you stop and think, is a real contribution. So is
[buying a coffee](https://buymeacoffee.com/piyushmishra00) or starring the repo — both help more
than you would think.

## Code of conduct

By taking part you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
