# Security

## What SHE promises

A SHE program run without permission flags cannot:

- read or write files
- open network connections
- start other programs
- read environment variables
- sleep

and, when given `--max-steps` or `--timeout`, cannot run indefinitely.

`tools/check_sandbox.py` asserts every one of these on each push. If you find a way
to break one of them, that is a vulnerability and we want to hear about it.

## What SHE does not promise

The sandbox governs what a SHE program can ask the SHE runtime to do. It is a
strong boundary for scripts, marking student work, plugins and snippets from the
internet. It is **not**:

- a replacement for an OS-level sandbox, container or VM;
- a defence against a malicious *Python* extension loaded into the interpreter;
- a guarantee against resource exhaustion beyond the step and time budgets — a
  program granted `--allow-write` can still fill a disk;
- a side-channel or timing-attack defence.

If you are running code from people you have concrete reason to distrust, run SHE
inside a container as well. The two together are much stronger than either alone.

## `--allow-run` is transitive, and that is not fixable

**Granting `--allow-run` without naming a program is equivalent to
`--allow-all`.** It is not one grant among six.

A program that can start any other program can start `python`, `curl`, `sh`, or
another `she` with wider flags:

```she
import os
os.run("she", ["run", "child.she", "--allow-all"])
os.run("python", ["-c", "print(open('secret.txt').read())"])
```

A child `she` process builds its own sandbox from its own command line. There is
no inheritance from the parent and no intersection with the parent's grants.

Capping `she` children specifically would be theatre, because the second line
above reaches exactly as far without involving `she` at all. Any capability
system that lets a program exec an arbitrary binary has this property; Deno's
`--allow-run` carries the same warning for the same reason.

**What helps is scoping**, and that does work:

```
$ she run x.she --allow-run=git
PermissionError: x.she tried to start other programs (python),
                 but was not given permission
```

So `--allow-run=git` is a real restriction and bare `--allow-run` is not — with
the caveat that a permitted binary may itself be a launcher, since `git` will run
arbitrary code through hooks and aliases. Scoping narrows the hole rather than
closing it.

SHE prints a warning when `--allow-run` is granted with no program named. Treat
that flag as "I trust this program completely", and if that is not what you mean,
name the program.

## Cryptography

The `crypto` module has two halves and the distinction matters.

**Vetted primitives** — `hash`, `hash_file`, `hmac`, `compare`, `token`,
`random_bytes`, `password_hash`, `password_check`, `base64_*`, `hex_*` — are thin
wrappers over Python's `hashlib`, `hmac` and `secrets`. Use these to protect
anything real. `password_hash` uses PBKDF2-SHA256 with 200,000 rounds by default
and refuses fewer than 50,000.

**Kaalka** — `kaalka_encrypt`, `kaalka_decrypt`, `seal`, `open`, `envelope`,
`open_envelope` — wraps the
[Kaalka Encryption Algorithm](https://github.com/PIYUSH-MISHRA-00/Kaalka-Encryption-Algorithm),
a novel time-keyed construction that has **not been through public
cryptanalysis**. SHE ships it for time-keyed session handoff, puzzles and
teaching. Do not use it to protect data whose disclosure would matter. This is
stated in the module docstring, the README, the website and the API docs, in the
same words.

`envelope` adds an HMAC-SHA256 checksum over the sealed body and its addressing,
so tampering is detected — but that integrity check is the part carrying vetted
cryptography, not the cipher underneath it.

## Supported versions

| Version | Supported |
|---|---|
| 2.x | ✅ |
| 1.x | ❌ — archived on the `v1.0.0` branch, no fixes |

## Reporting a vulnerability

**Do not open a public issue.**

Use GitHub's [private vulnerability reporting](https://github.com/ni-sh-a-char/SHE/security/advisories/new),
or email **dev@gratefulworldventures.in**.

Please include:

- what the issue is and what it lets an attacker do
- the smallest SHE program that demonstrates it
- the exact command used to run it, including any permission flags
- the SHE version (`she --version`) and Python version

You can expect an acknowledgement within 72 hours and an assessment within a week.
Fixes for confirmed sandbox escapes are released as soon as they are ready, and
you will be credited in the advisory and the changelog unless you prefer not to be.

Please give us a reasonable window to ship a fix before publishing.

## Scope

**In scope:** sandbox escapes, permission-scope bypasses (for example a path that
escapes `--allow-read=./data`), budget bypasses, crashes that leak host paths or
environment data, and anything that turns SHE source into arbitrary host code
execution without a grant.

**Out of scope:** anything a program does with permissions you granted it; denial
of service in a program run without `--max-steps` or `--timeout`; weaknesses in
Kaalka itself, which are documented above rather than treated as vulnerabilities
in SHE (report those to the Kaalka project); and issues in Python itself.
