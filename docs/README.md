# SHE documentation

The full reference lives at **[she-lang.dev/docs](https://she-lang.dev/docs)** —
searchable, with runnable examples and a browser playground.

This folder holds the parts that are easier to read next to the source.

| | |
|---|---|
| [language.md](language.md) | The complete language reference, in one file |
| [../examples/](../examples/) | Ten programs, each one runnable and tested |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | How the interpreter is laid out and how to change it |
| [../SECURITY.md](../SECURITY.md) | What the sandbox promises, and what it does not |
| [../CHANGELOG.md](../CHANGELOG.md) | What changed in 2.0 and why |

## The fastest way in

```sh
pip install she-lang
she                      # try things at the prompt
she doc                  # every module
she doc math             # one module in full
```

From inside a program, `help(math)` prints the same thing, and `help(value)`
describes any value along with what you can do with it.
