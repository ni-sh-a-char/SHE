"""Capability-based sandbox.

A SHE program starts with **no** ambient authority. It cannot read a file, open
a socket, spawn a process or read an environment variable until you grant that
capability explicitly:

    she run report.she --allow-read=./data --allow-net=api.github.com

Anything ungranted raises a PermissionError that names the exact flag needed, so
running untrusted SHE code is a decision you make on purpose rather than one you
discover afterwards. This mirrors the Deno model, which is the only model that
has actually worked in practice for scripting languages.
"""

import fnmatch
import os
import time
from pathlib import Path

from .errors import LimitErr, PermissionErr

CAPABILITIES = ("read", "write", "net", "run", "env", "time")

DESCRIPTIONS = {
    "read": "read files from disk",
    "write": "write or delete files on disk",
    "net": "make network connections",
    "run": "start other programs",
    "env": "read environment variables",
    "time": "sleep or read the wall clock",
}


class Grant:
    """One capability, optionally narrowed to a set of paths or hosts."""

    __slots__ = ("name", "scopes")

    def __init__(self, name, scopes=None):
        self.name = name
        self.scopes = list(scopes) if scopes else []

    def allows(self, target=None):
        if not self.scopes or target is None:
            return True
        return any(self._match(scope, target) for scope in self.scopes)

    def _match(self, scope, target):
        if self.name in ("read", "write"):
            try:
                base = Path(scope).expanduser().resolve()
                want = Path(target).expanduser().resolve()
            except (OSError, ValueError):
                return False
            return want == base or base in want.parents
        return fnmatch.fnmatch(str(target).lower(), scope.lower())

    def __repr__(self):
        return self.name + (("=" + ",".join(self.scopes)) if self.scopes else "")


class Sandbox:
    """Holds what a program is allowed to do, plus its resource budget."""

    def __init__(self, grants=None, max_steps=None, max_depth=200, timeout=None,
                 name="this program"):
        self.grants = {}
        for grant in grants or []:
            self.add(grant)
        self.max_steps = max_steps
        self.max_depth = max_depth
        self.timeout = timeout
        self.name = name
        self.steps = 0
        self.started = time.monotonic()

    # --- granting ----------------------------------------------------------
    def add(self, grant):
        if isinstance(grant, str):
            grant = parse_grant(grant)
        existing = self.grants.get(grant.name)
        if existing is None:
            self.grants[grant.name] = grant
        elif not existing.scopes or not grant.scopes:
            existing.scopes = []           # a bare grant widens to everything
        else:
            existing.scopes.extend(grant.scopes)
        return self

    @classmethod
    def trusted(cls, **kwargs):
        """Everything allowed. What `--allow-all` and the REPL default to."""
        return cls([Grant(name) for name in CAPABILITIES], **kwargs)

    @classmethod
    def locked(cls, **kwargs):
        """Nothing allowed. What the web playground and `she run` default to."""
        return cls([], **kwargs)

    def granted(self, name):
        return name in self.grants

    # --- checking ----------------------------------------------------------
    def require(self, name, target=None, action=None):
        grant = self.grants.get(name)
        if grant is not None and grant.allows(target):
            return True
        what = action or DESCRIPTIONS.get(name, name)
        detail = f" ({target})" if target is not None else ""
        if grant is not None:
            hint = (f"`--allow-{name}` is set but does not cover {target}. "
                    f"Add it: --allow-{name}={target}")
        else:
            flag = f"--allow-{name}={target}" if target is not None else f"--allow-{name}"
            hint = (f"run it with `{flag}` to permit this, "
                    f"or `--allow-all` while you are developing.")
        raise PermissionErr(
            f"{self.name} tried to {what}{detail}, but was not given permission",
            hint=hint,
        )

    def check_path(self, path, mode="read"):
        self.require(mode, os.fspath(path))
        return path

    def check_host(self, url):
        host = url
        if "://" in url:
            host = url.split("://", 1)[1]
        host = host.split("/", 1)[0].split("@")[-1].split(":")[0]
        self.require("net", host)
        return host

    # --- budgets -----------------------------------------------------------
    def tick(self, amount=1):
        """Called by the interpreter on every step. Keeps runaway code bounded."""
        if self.max_steps is None and self.timeout is None:
            return
        self.steps += amount
        if self.max_steps is not None and self.steps > self.max_steps:
            raise LimitErr(
                f"{self.name} ran for more than {self.max_steps:,} steps and was stopped",
                hint="this usually means a loop never finishes. "
                     "Raise the ceiling with --max-steps if it is genuinely long-running.",
            )
        if self.timeout is not None and self.steps % 2048 == 0:
            if time.monotonic() - self.started > self.timeout:
                raise LimitErr(
                    f"{self.name} ran longer than {self.timeout} seconds and was stopped",
                    hint="raise the ceiling with --timeout if that is expected.",
                )

    def summary(self):
        if not self.grants:
            return "no permissions"
        return ", ".join(str(g) for g in self.grants.values())


def parse_grant(text):
    """`read`, `--allow-read`, `net=api.github.com,*.example.com`."""
    text = text.strip()
    for prefix in ("--allow-", "allow-"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    name, _, scopes = text.partition("=")
    name = name.strip().lower()
    if name == "all":
        raise ValueError("all")
    if name not in CAPABILITIES:
        known = ", ".join(CAPABILITIES)
        raise ValueError(f"unknown permission `{name}`. Known permissions: {known}")
    parts = [s.strip() for s in scopes.split(",") if s.strip()]
    return Grant(name, parts)


def grants_from_args(args):
    """Turn a list of --allow-* CLI flags into a Sandbox."""
    grants = []
    for arg in args:
        if arg in ("--allow-all", "-A"):
            return [Grant(name) for name in CAPABILITIES]
        try:
            grants.append(parse_grant(arg))
        except ValueError as exc:
            if str(exc) == "all":
                return [Grant(name) for name in CAPABILITIES]
            raise
    return grants
