"""The `she` command.

    she                      start the interactive prompt
    she run app.she          run a program (no permissions unless granted)
    she app.she              same thing, shorter
    she test                 run every `test "..."` block it can find
    she fmt [path]           format files
    she check app.she        parse and report problems without running
    she new my-project       scaffold a project
    she doc [module]         show what a module provides
    she lsp                  language server, for editors
"""

import os
import sys

from . import __version__
from .errors import SheError
from .interp import Interpreter
from .sandbox import Sandbox, grants_from_args

BANNER = f"""\033[95m
   ____  _   _  _____
  / ___|| | | || ____|   SHE {__version__}
  \\___ \\| |_| ||  _|     a language that reads like English
   ___) |  _  || |___
  |____/|_| |_||_____|   type :help for help, :quit to leave
\033[0m"""

HELP = """\033[1mUsage\033[0m
  she                        interactive prompt
  she <file.she>             run a program
  she run <file.she>         the same, explicitly
  she test [path]            run tests
  she fmt [path]             format code (--check to only report)
  she check <file.she>       look for problems without running
  she new <name>             start a new project
  she doc [module]           what a module provides
  she lsp                    language server for editors

\033[1mPermissions\033[0m  (a program gets none unless you say so)
  --allow-read[=path]        read files
  --allow-write[=path]       write files
  --allow-net[=host]         reach the network
  --allow-run[=program]      start other programs
  --allow-env[=name]         read environment variables
  --allow-time               sleep
  --allow-all, -A            all of the above

\033[1mLimits\033[0m
  --max-steps N              stop after N steps (default: no limit)
  --timeout N                stop after N seconds
  --max-depth N              how deep calls may nest (default 200)

\033[1mMore\033[0m
  --version, -v              print the version
  --help, -h                 this message
  docs: https://ni-sh-a-char.github.io/SHE/
"""

REPL_HELP = """\033[1mAt the prompt\033[0m
  :help            this message
  :quit  :q        leave
  :clear           clear the screen
  :env             what is defined right now
  :grant read      turn on a permission for this session
  :perms           what this session may do
  :load file.she   run a file into this session
  :time expr       run something and report how long it took
  :type expr       what kind of value something is
  Values print themselves, so just typing `1 + 1` shows 2.
"""

EXAMPLE = '''# {name} — made with SHE
# Run it with:  she run main.she

fun greet(who = "world") -> "Hello, {{who}}!"

say greet()
say greet("{name}")

let numbers = [1, 2, 3, 4, 5]
say "the even ones add up to {{numbers |> filter(fun(n) -> n % 2 is 0) |> sum()}}"

test "greeting says hello"
  expect greet("SHE") is "Hello, SHE!"
end
'''

MANIFEST = '''# {name}
name = "{name}"
version = "0.1.0"
entry = "main.she"

# Permissions this project needs. `she run` reads these.
permissions = []
'''

README_TEMPLATE = """# {name}

Built with [SHE](https://ni-sh-a-char.github.io/SHE/).

## Run it

```sh
she run main.she
```

## Test it

```sh
she test
```
"""


def use_utf8():
    """Windows consoles still default to a legacy code page, which turns
    perfectly ordinary text into mojibake. Ask for UTF-8 and move on."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv=None):
    use_utf8()
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return repl()

    first = argv[0]
    if first in ("--version", "-v", "version"):
        print(f"SHE {__version__}")
        return 0
    if first in ("--help", "-h", "help"):
        print(HELP)
        return 0

    commands = {"run": cmd_run, "test": cmd_test, "fmt": cmd_fmt,
                "format": cmd_fmt, "check": cmd_check, "new": cmd_new,
                "doc": cmd_doc, "docs": cmd_doc, "repl": lambda a: repl(),
                "lsp": cmd_lsp}
    if first in commands:
        return commands[first](argv[1:])
    if first.endswith(".she") or os.path.isfile(first):
        return cmd_run(argv)
    print(f"she: `{first}` is not a command and not a .she file", file=sys.stderr)
    print("try `she --help`", file=sys.stderr)
    return 2


def split_flags(args):
    """Separate --flags from everything else."""
    flags = [a for a in args if a.startswith("-")]
    rest = [a for a in args if not a.startswith("-")]
    return flags, rest


def build_sandbox(flags, name="this program"):
    try:
        grants = grants_from_args([f for f in flags
                                   if f.startswith("--allow") or f == "-A"])
    except ValueError as exc:
        print(f"she: {exc}", file=sys.stderr)
        raise SystemExit(2)
    limits = {}
    for flag in flags:
        for key, field in (("--max-steps", "max_steps"), ("--timeout", "timeout"),
                           ("--max-depth", "max_depth")):
            if flag.startswith(key + "="):
                try:
                    value = float(flag.split("=", 1)[1])
                except ValueError:
                    print(f"she: `{flag}` needs a number", file=sys.stderr)
                    raise SystemExit(2)
                limits[field] = value if field == "timeout" else int(value)
    return Sandbox(grants, name=name, **limits)


def report(error, colour=None):
    colour = sys.stderr.isatty() if colour is None else colour
    print(error.render(color=colour), file=sys.stderr)


def cmd_run(args):
    flags, rest = split_flags(args)
    if not rest:
        print("she: which file should I run?", file=sys.stderr)
        print("try `she run main.she`", file=sys.stderr)
        return 2
    path, script_args = rest[0], rest[1:]
    if not os.path.isfile(path) and os.path.isfile(path + ".she"):
        path += ".she"
    if not os.path.isfile(path):
        print(f"she: I cannot find `{path}`", file=sys.stderr)
        return 1
    try:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
    except OSError as exc:
        print(f"she: I could not read `{path}`: {exc}", file=sys.stderr)
        return 1

    sandbox = build_sandbox(flags, name=os.path.basename(path))
    interp = Interpreter(sandbox=sandbox, file=path)
    interp.script_args = script_args
    try:
        interp.run(source, path)
        return 0
    except SheError as error:
        report(error)
        return 1
    except SystemExit as exit_:
        return int(exit_.code or 0)
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
        return 130
    except RecursionError:
        print("she: the program nested too deeply and was stopped", file=sys.stderr)
        return 1
    finally:
        interp.shutdown()


def cmd_check(args):
    flags, rest = split_flags(args)
    targets = collect_files(rest or ["."])
    if not targets:
        print("she: nothing to check", file=sys.stderr)
        return 1
    from .parser import parse
    problems = 0
    for path in targets:
        try:
            with open(path, encoding="utf-8") as handle:
                parse(handle.read(), path)
        except SheError as error:
            report(error)
            problems += 1
        except OSError as exc:
            print(f"she: {path}: {exc}", file=sys.stderr)
            problems += 1
    if problems:
        print(f"\n{problems} file{'s' if problems != 1 else ''} with problems",
              file=sys.stderr)
        return 1
    print(f"checked {len(targets)} file{'s' if len(targets) != 1 else ''}, all good")
    return 0


def cmd_fmt(args):
    flags, rest = split_flags(args)
    check_only = "--check" in flags
    targets = collect_files(rest or ["."])
    if not targets:
        print("she: nothing to format", file=sys.stderr)
        return 1
    from .formatter import format_file
    changed = []
    for path in targets:
        try:
            if format_file(path, write=not check_only):
                changed.append(path)
        except SheError as error:
            report(error)
            return 1
        except OSError as exc:
            print(f"she: {path}: {exc}", file=sys.stderr)
            return 1
    if check_only:
        for path in changed:
            print(f"needs formatting: {path}")
        if changed:
            print(f"\n{len(changed)} file{'s' if len(changed) != 1 else ''} "
                  f"would change", file=sys.stderr)
            return 1
        print(f"{len(targets)} file{'s' if len(targets) != 1 else ''} already tidy")
        return 0
    for path in changed:
        print(f"formatted {path}")
    if not changed:
        print(f"{len(targets)} file{'s' if len(targets) != 1 else ''} already tidy")
    return 0


def cmd_test(args):
    flags, rest = split_flags(args)
    targets = collect_files(rest or ["."])
    if not targets:
        print("she: I found no .she files to test", file=sys.stderr)
        return 1
    sandbox = build_sandbox(flags or ["--allow-all"], name="the tests")
    passed = failed = 0
    failures = []
    colour = sys.stdout.isatty()

    def paint(text, code):
        return f"\033[{code}m{text}\033[0m" if colour else text

    for path in targets:
        interp = Interpreter(sandbox=sandbox, file=path)
        try:
            with open(path, encoding="utf-8") as handle:
                interp.run(handle.read(), path)
        except SheError as error:
            print(paint(f"  ERROR  {path}", "1;31"))
            report(error, colour)
            failed += 1
            continue
        if not interp.tests:
            continue
        print(paint(f"\n{path}", "1"))
        for node, env in interp.tests:
            try:
                interp.exec_block(node.body, env)
                passed += 1
                print(f"  {paint('ok', '32')}    {node.name}")
            except SheError as error:
                failed += 1
                failures.append((path, node.name, error))
                print(f"  {paint('fail', '1;31')}  {node.name}")
                print("        " + error.message)
                if error.pos:
                    print(paint(f"        {error.pos.file}:{error.pos.line + 1}", "2;37"))
            finally:
                interp.shutdown()

    total = passed + failed
    if total == 0:
        print("no tests found — write one with `test \"name\" ... end`")
        return 0
    print()
    summary = f"{passed} passed, {failed} failed, {total} total"
    print(paint(summary, "1;32" if not failed else "1;31"))
    return 1 if failed else 0


def cmd_new(args):
    flags, rest = split_flags(args)
    if not rest:
        print("she: what should the project be called?", file=sys.stderr)
        print("try `she new my-project`", file=sys.stderr)
        return 2
    name = rest[0]
    if os.path.exists(name):
        print(f"she: `{name}` already exists", file=sys.stderr)
        return 1
    try:
        os.makedirs(name)
        with open(os.path.join(name, "main.she"), "w", encoding="utf-8") as handle:
            handle.write(EXAMPLE.format(name=name))
        with open(os.path.join(name, "she.toml"), "w", encoding="utf-8") as handle:
            handle.write(MANIFEST.format(name=name))
        with open(os.path.join(name, "README.md"), "w", encoding="utf-8") as handle:
            handle.write(README_TEMPLATE.format(name=name))
    except OSError as exc:
        print(f"she: I could not create the project: {exc}", file=sys.stderr)
        return 1
    print(f"created {name}/")
    print(f"  cd {name}")
    print("  she run main.she")
    return 0


def cmd_doc(args):
    from .stdlib import DOCS, load_module, module_names
    flags, rest = split_flags(args)
    interp = Interpreter(sandbox=Sandbox.trusted())
    if not rest:
        print("SHE modules\n")
        for name in module_names():
            print(f"  {name:<10} {DOCS.get(name, '')}")
        print("\nsee one with `she doc math`")
        return 0
    name = rest[0]
    try:
        module = load_module(interp, name)
    except SheError as error:
        report(error)
        return 1
    print(f"module {name}")
    if DOCS.get(name):
        print(f"  {DOCS[name]}\n")
    for key in sorted(module.values):
        value = module.values[key]
        doc = (getattr(value, "doc", "") or "").split("\n")[0]
        print(f"  {name}.{key:<20} {doc}")
    return 0


def cmd_lsp(args):
    from .lsp import serve
    return serve()


def collect_files(paths):
    out = []
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, names in os.walk(path):
                dirs[:] = [d for d in dirs
                           if not d.startswith(".") and d not in ("node_modules", "venv")]
                out.extend(os.path.join(root, n) for n in sorted(names)
                           if n.endswith(".she"))
        elif os.path.isfile(path):
            out.append(path)
        elif os.path.isfile(path + ".she"):
            out.append(path + ".she")
        else:
            print(f"she: I cannot find `{path}`", file=sys.stderr)
    return out


# --- the interactive prompt -------------------------------------------------

def repl():
    from .values import show
    try:
        import readline  # noqa: F401  — gives history and arrow keys where available
    except ImportError:
        pass

    colour = sys.stdout.isatty()
    if colour:
        print(BANNER)
    else:
        print(f"SHE {__version__} — type :help for help")

    sandbox = Sandbox.trusted(name="this session")
    interp = Interpreter(sandbox=sandbox, file="<repl>")
    buffer = []

    def prompt():
        base = "she> " if not buffer else "...  "
        return f"\033[95m{base}\033[0m" if colour else base

    while True:
        try:
            line = input(prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not buffer and line.strip().startswith(":"):
            if handle_command(line.strip(), interp, sandbox) == "quit":
                break
            continue

        if not line.strip() and not buffer:
            continue

        buffer.append(line)
        source = "\n".join(buffer)
        if incomplete(source):
            continue
        buffer = []

        try:
            result = interp.run(source, "<repl>")
            if result is not None:
                print(show(result, quote=True))
        except SheError as error:
            report(error, colour)
        except KeyboardInterrupt:
            print("\nstopped")
        except SystemExit:
            break
        except RecursionError:
            print("that nested too deeply", file=sys.stderr)

    interp.shutdown()
    print("bye")
    return 0


def incomplete(source):
    """True when the user is mid-block and we should keep collecting lines."""
    from .errors import SheError as _SheError
    from .parser import parse
    try:
        parse(source, "<repl>")
        return False
    except _SheError as error:
        message = (error.message or "").lower()
        return ("is never closed" in message
                or "expected `end`" in message
                or "the end of the file" in message
                or "needs a `catch`" in message
                or "at least one `case`" in message)


def handle_command(line, interp, sandbox):
    from .values import show, type_name
    parts = line[1:].split(None, 1)
    name = parts[0] if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    if name in ("quit", "q", "exit"):
        return "quit"
    if name in ("help", "h", "?"):
        print(REPL_HELP)
    elif name in ("clear", "cls"):
        os.system("cls" if os.name == "nt" else "clear")
    elif name == "env":
        names = sorted(n for n in interp.globals.values
                       if not n.startswith("_"))
        user = [n for n in names if n not in _builtin_names(interp)]
        print("  " + (", ".join(user) if user else "nothing defined yet"))
    elif name == "perms":
        print("  " + sandbox.summary())
    elif name == "grant":
        try:
            sandbox.add(rest.strip())
            print(f"  granted {rest.strip()}")
        except ValueError as exc:
            print(f"  {exc}")
    elif name == "load":
        path = rest.strip().strip('"')
        if not os.path.isfile(path):
            print(f"  I cannot find `{path}`")
        else:
            with open(path, encoding="utf-8") as handle:
                try:
                    interp.run(handle.read(), path)
                    print(f"  loaded {path}")
                except SheError as error:
                    report(error)
    elif name == "time":
        import time as _time
        start = _time.perf_counter()
        try:
            result = interp.run(rest, "<repl>")
            elapsed = (_time.perf_counter() - start) * 1000
            if result is not None:
                print(show(result, quote=True))
            print(f"  took {elapsed:.2f} ms")
        except SheError as error:
            report(error)
    elif name == "type":
        try:
            print("  " + type_name(interp.run(rest, "<repl>")))
        except SheError as error:
            report(error)
    else:
        print(f"  `:{name}` is not a command — try :help")
    return None


_BUILTIN_CACHE = {}


def _builtin_names(interp):
    if "names" not in _BUILTIN_CACHE:
        fresh = Interpreter(sandbox=Sandbox.locked())
        _BUILTIN_CACHE["names"] = set(fresh.globals.values)
        fresh.shutdown()
    return _BUILTIN_CACHE["names"]


if __name__ == "__main__":
    sys.exit(main())
