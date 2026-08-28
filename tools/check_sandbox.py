"""Prove the sandbox holds.

CI runs this on every push. If a SHE program with no grants can reach the disk,
the network, the process table or the environment, this fails loudly — which is
exactly what should happen, because that guarantee is the whole point.
"""

import sys

sys.path.insert(0, ".")

from she import run  # noqa: E402
from she.sandbox import Sandbox  # noqa: E402

MUST_BE_REFUSED = [
    ("read a file", 'import fs\nsay fs.read("/etc/passwd")'),
    ("list a folder", 'import fs\nsay fs.list("/")'),
    ("write a file", 'import fs\nfs.write("/tmp/escaped.txt", "nope")'),
    ("delete a folder", 'import fs\nfs.remove_folder("/tmp/anything")'),
    ("reach the network", 'import http\nsay http.get("https://example.com")'),
    ("download a file", 'import http\nhttp.download("https://example.com", "/tmp/x")'),
    ("read the environment", 'import os\nsay os.env("PATH")'),
    ("read every variable", 'import os\nsay os.env_all()'),
    ("start a program", 'import os\nsay os.run("id")'),
    ("sleep", "import time\ntime.sleep(1)"),
    ("crawl with WebWeaveX", 'import web\nsay web.crawl("https://example.com")'),
]

MUST_BE_ALLOWED = [
    ("arithmetic", "say 2 + 2"),
    ("text", 'say "hello".upper()'),
    ("lists", "say [3,1,2] |> sorted() |> sum()"),
    ("your own functions", "fun f(n) -> n * 2\nsay f(21)"),
    ("your own types", "type P has x\nsay P(1).x"),
    ("hashing", 'import crypto\nsay crypto.hash("x")'),
    ("json", "say json.stringify({a: 1})"),
]


def main():
    problems = []

    for label, source in MUST_BE_REFUSED:
        _, error = run(source, "<check>", sandbox=Sandbox.locked())
        if error is None:
            problems.append(f"ESCAPED: a locked program could {label}")
        elif error.kind != "PermissionError":
            problems.append(
                f"WRONG ERROR: {label} raised {error.kind}, expected PermissionError "
                f"({error.message})")
        else:
            print(f"  refused  {label}")

    for label, source in MUST_BE_ALLOWED:
        _, error = run(source, "<check>", sandbox=Sandbox.locked())
        if error is not None:
            problems.append(f"BLOCKED: pure {label} should never need permission "
                            f"({error.kind}: {error.message})")
        else:
            print(f"  allowed  {label}")

    # Scoping `--allow-run` has to be a real restriction, not decoration. This
    # is the mitigation SECURITY.md points people at, so it is checked here.
    from she.sandbox import Grant
    scoped = Sandbox([Grant("run", ["git"])])
    probe = 'import os\nsay os.run("python", ["-c", "print(1)"])'
    _, error = run(probe, "<check>", sandbox=scoped)
    if error is None or error.kind != "PermissionError":
        problems.append("SCOPE IGNORED: --allow-run=git allowed a different program")
    else:
        print("  refused  a program outside --allow-run=git")

    # And the documented escalation stays documented: an unscoped run grant is
    # equivalent to full authority, because the child chooses its own flags.
    # If this ever starts being refused, SECURITY.md needs rewriting, not this.
    wide = Sandbox([Grant("run")])
    _, error = run(probe, "<check>", sandbox=wide)
    if error is not None:
        problems.append(f"UNEXPECTED: an unscoped run grant was refused ({error.kind}) — "
                        "SECURITY.md documents this as permitted, so one of them is wrong")
    else:
        print("  allowed  any program under an unscoped --allow-run (documented)")

    # A runaway loop must be stopped by the step budget rather than hanging.
    _, error = run("while true\n  var x = 1\nend", "<check>",
                   sandbox=Sandbox.locked(max_steps=200_000))
    if error is None or error.kind != "LimitError":
        problems.append("NOT STOPPED: an endless loop was not caught by the step budget")
    else:
        print("  stopped  an endless loop")

    if problems:
        print("\n" + "\n".join(problems), file=sys.stderr)
        return 1
    print(f"\nthe sandbox held: {len(MUST_BE_REFUSED)} refused, "
          f"{len(MUST_BE_ALLOWED)} allowed, budgets enforced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
