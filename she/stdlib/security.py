"""crypto and web modules.

`crypto` has two halves and it matters which one you reach for:

  * Standard primitives (hash, hmac, password_hash, token, compare) are thin
    wrappers over Python's hashlib/hmac/secrets. Use these to protect anything
    real.
  * Kaalka (kaalka_encrypt / seal / open) is the time-driven cipher from
    https://github.com/PIYUSH-MISHRA-00/Kaalka-Encryption-Algorithm. It is a
    novel construction and has not been through public cryptanalysis, so SHE
    ships it for time-keyed session handoff, puzzles and teaching, and says so
    plainly rather than quietly implying it is a substitute for AES.

`web` wraps WebWeaveX (https://github.com/ni-sh-a-char/WebWeaveX), which turns a
live app, repo or document into a deterministic graph you can query and replay.
Anything that reaches the network needs --allow-net.
"""

import base64 as _base64
import binascii as _binascii
import hashlib as _hashlib
import hmac as _hmac
import secrets as _secrets

from ..errors import ImportErr, ValueErr
from ..values import show, type_name
from . import register

HASHES = ("sha256", "sha512", "sha1", "sha3_256", "blake2b", "md5")


def _require(name, install, why):
    try:
        return __import__(name)
    except ImportError:
        raise ImportErr(
            f"the `{name}` package is not installed",
            hint=f"install it with `pip install {install}` — {why}")


def _as_bytes(value, what):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    raise ValueErr(f"`{what}` needs text, not a {type_name(value)}")


@register("crypto", "Hashing, tokens and Kaalka time-keyed encryption.")
def _crypto_module():
    kaalka_state = {}

    def _kaalka():
        if "instance" not in kaalka_state:
            module = _require("kaalka", "kaalka",
                              "it provides the Kaalka time-driven cipher.")
            kaalka_state["instance"] = module.Kaalka()
        return kaalka_state["instance"]

    # --- standard primitives ------------------------------------------------
    def hash_(value, algorithm="sha256"):
        """A hex fingerprint of some text. sha256 by default."""
        name = str(algorithm).lower()
        if name not in HASHES:
            raise ValueErr(f"`{algorithm}` is not a hash I know",
                           hint="choose one of: " + ", ".join(HASHES))
        if name == "md5":
            # Allowed for checksums against legacy systems, never for secrets.
            return _hashlib.md5(_as_bytes(value, "hash"), usedforsecurity=False).hexdigest()
        return _hashlib.new(name, _as_bytes(value, "hash")).hexdigest()

    def hash_file(interp, path, algorithm="sha256"):
        """A hex fingerprint of a file, read in chunks."""
        interp.sandbox.check_path(str(path), "read")
        digest = _hashlib.new(str(algorithm).lower())
        with open(str(path), "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def hmac_(value, key, algorithm="sha256"):
        """A keyed fingerprint, so only someone with the key can produce it."""
        return _hmac.new(_as_bytes(key, "hmac"), _as_bytes(value, "hmac"),
                         str(algorithm).lower()).hexdigest()

    def compare(a, b):
        """Compare two secrets without leaking how much matched."""
        return _hmac.compare_digest(_as_bytes(a, "compare"), _as_bytes(b, "compare"))

    def token(length=32):
        """A random token safe to use as a session id or api key."""
        length = int(length)
        if not 8 <= length <= 4096:
            raise ValueErr("a token should be between 8 and 4096 characters")
        return _secrets.token_urlsafe(length)[:length]

    def random_bytes(count=32):
        """Cryptographically random bytes, as hex text."""
        count = int(count)
        if not 1 <= count <= 1_000_000:
            raise ValueErr("ask for between 1 and 1000000 bytes")
        return _secrets.token_hex(count)

    def password_hash(password, rounds=200_000):
        """Turn a password into something safe to store. Uses PBKDF2-SHA256."""
        rounds = int(rounds)
        if rounds < 50_000:
            raise ValueErr("use at least 50000 rounds",
                           hint="fewer rounds makes guessing the password cheap.")
        salt = _secrets.token_bytes(16)
        digest = _hashlib.pbkdf2_hmac("sha256", _as_bytes(password, "password_hash"),
                                      salt, rounds)
        return f"pbkdf2$sha256${rounds}${salt.hex()}${digest.hex()}"

    def password_check(password, stored):
        """True when a password matches something `password_hash` made."""
        try:
            scheme, algorithm, rounds, salt, expected = str(stored).split("$")
        except ValueError:
            raise ValueErr("that does not look like a stored password hash")
        if scheme != "pbkdf2":
            raise ValueErr(f"`{scheme}` is not a password format I know")
        digest = _hashlib.pbkdf2_hmac(algorithm, _as_bytes(password, "password_check"),
                                      bytes.fromhex(salt), int(rounds))
        return _hmac.compare_digest(digest.hex(), expected)

    def base64_encode(value):
        """Text as base64, safe to put in JSON or a URL."""
        return _base64.b64encode(_as_bytes(value, "base64_encode")).decode("ascii")

    def base64_decode(value):
        """Read base64 text back."""
        try:
            return _base64.b64decode(str(value), validate=True).decode("utf-8", "replace")
        except (_binascii.Error, ValueError):
            raise ValueErr("that is not valid base64 text")

    def hex_encode(value):
        """Text as hexadecimal."""
        return _as_bytes(value, "hex_encode").hex()

    def hex_decode(value):
        """Read hexadecimal text back."""
        try:
            return bytes.fromhex(str(value)).decode("utf-8", "replace")
        except ValueError:
            raise ValueErr("that is not valid hexadecimal text")

    # --- Kaalka -------------------------------------------------------------
    def kaalka_encrypt(message, at=None):
        """Encrypt with Kaalka. `at` is a time key like "14:35:22"; the current
        second is used when you leave it out."""
        text = message if isinstance(message, str) else show(message)
        if at is None:
            return _kaalka().encrypt(text)
        return _kaalka().encrypt(text, str(at))

    def kaalka_decrypt(secret, at=None):
        """Undo `kaalka_encrypt`, using the same time key."""
        text = secret if isinstance(secret, str) else show(secret)
        if at is None:
            return _kaalka().decrypt(text)
        return _kaalka().decrypt(text, str(at))

    def seal(message, at=None):
        """Kaalka-encrypt and armour the result as base64.

        Raw Kaalka output holds characters that do not survive a file, a URL or
        a JSON field. `seal` and `open` are the pair you want whenever the
        ciphertext has to travel."""
        raw = kaalka_encrypt(message, at)
        return _base64.b64encode(raw.encode("utf-8", "surrogatepass")).decode("ascii")

    def open_(sealed, at=None):
        """Undo `seal`."""
        try:
            raw = _base64.b64decode(str(sealed), validate=True).decode("utf-8", "surrogatepass")
        except (_binascii.Error, ValueError, UnicodeDecodeError):
            raise ValueErr("that is not something `crypto.seal` produced")
        return kaalka_decrypt(raw, at)

    def envelope(message, sender, receiver, at=None):
        """Seal a message with who it is from and who it is for, plus a checksum."""
        body = seal(message, at)
        stamp = str(at) if at is not None else _clock()
        header = {"from": str(sender), "to": str(receiver), "at": stamp}
        checksum = hmac_(body, f"{header['from']}>{header['to']}@{stamp}")
        return {**header, "body": body, "checksum": checksum}

    def open_envelope(packet, receiver, at=None):
        """Read an envelope, checking it was meant for you and is unchanged."""
        if not isinstance(packet, dict):
            raise ValueErr("`crypto.open_envelope` needs an envelope map")
        for key in ("from", "to", "at", "body", "checksum"):
            if key not in packet:
                raise ValueErr(f"this envelope is missing `{key}`")
        if str(packet["to"]) != str(receiver):
            raise ValueErr(f"this envelope is addressed to `{packet['to']}`, "
                           f"not `{receiver}`")
        stamp = str(packet["at"])
        expected = hmac_(packet["body"], f"{packet['from']}>{packet['to']}@{stamp}")
        if not _hmac.compare_digest(expected, str(packet["checksum"])):
            raise ValueErr("this envelope has been tampered with")
        return open_(packet["body"], at if at is not None else stamp)

    def _clock():
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S")

    def clock_key():
        """The current time as a Kaalka time key."""
        return _clock()

    return {
        "hash": hash_, "hash_file": hash_file, "hmac": hmac_, "compare": compare,
        "token": token, "random_bytes": random_bytes,
        "password_hash": password_hash, "password_check": password_check,
        "base64_encode": base64_encode, "base64_decode": base64_decode,
        "hex_encode": hex_encode, "hex_decode": hex_decode,
        "kaalka_encrypt": kaalka_encrypt, "kaalka_decrypt": kaalka_decrypt,
        "seal": seal, "open": open_, "envelope": envelope,
        "open_envelope": open_envelope, "clock_key": clock_key,
    }


@register("web", "Turn live apps, repos and documents into queryable graphs (WebWeaveX).")
def _web_module():
    state = {}

    def _wwx():
        if "module" not in state:
            state["module"] = _require(
                "webweavex", "webweavex",
                "it powers SHE's `web` module.")
        return state["module"]

    def _plain(value):
        """WebWeaveX hands back dataclasses and nested objects; flatten them."""
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(k): _plain(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_plain(v) for v in value]
        if hasattr(value, "__dict__"):
            return {str(k): _plain(v) for k, v in vars(value).items()
                    if not str(k).startswith("_")}
        return show(value)

    def extract(interp, source, kind="auto", session=None, options=None):
        """Pull the structure out of a web app, repo, document or API."""
        wwx = _wwx()
        if str(source).startswith(("http://", "https://")):
            interp.sandbox.check_host(str(source))
        else:
            interp.sandbox.require("read", str(source), action="read a source")
        payload = wwx.UniversalInput(
            source=str(source), source_type=str(kind),
            session=dict(session) if isinstance(session, dict) else None,
            options=dict(options) if isinstance(options, dict) else {})
        return _plain(wwx.run_canonical_pipeline(payload))

    def crawl(interp, url, **options):
        """Walk a site and collect what is there."""
        interp.sandbox.check_host(str(url))
        return _plain(_wwx().crawl(str(url), **dict(options)))

    def repo(interp, source):
        """Read a code repository into a graph."""
        if str(source).startswith(("http://", "https://")):
            interp.sandbox.check_host(str(source))
        else:
            interp.sandbox.require("read", str(source), action="read a repository")
        return _plain(_wwx().extract_repo(str(source)))

    def docs(interp, source):
        """Read documentation into a graph."""
        if str(source).startswith(("http://", "https://")):
            interp.sandbox.check_host(str(source))
        else:
            interp.sandbox.require("read", str(source), action="read documents")
        return _plain(_wwx().extract_docs(str(source)))

    def graph(result):
        """The graph part of an extraction."""
        if isinstance(result, dict):
            return result.get("graph", result)
        return _plain(result)

    def nodes(result, name=""):
        """Every node in a graph, or the ones matching a name."""
        return _plain(_wwx().query_nodes(graph(result), str(name)))

    def edges(result, name=""):
        """Every connection in a graph, or the ones touching a name."""
        return _plain(_wwx().query_edges(graph(result), str(name)))

    def query(result, name=""):
        """Search a graph for a node and what surrounds it."""
        return _plain(_wwx().query_graph(result if isinstance(result, dict) else None,
                                         str(name)))

    def fingerprint(payload, token="she"):
        """A deterministic identity for a payload. The same input always
        produces the same fingerprint."""
        return _wwx().fingerprint(_plain(payload), str(token))

    def kaalka_hash(payload):
        """WebWeaveX's Kaalka-backed content hash."""
        return _wwx().compute_kaalka_hash(_plain(payload))

    def analyze(payload, edges_=None):
        """Summarise a graph: how big it is and how it connects."""
        return _plain(_wwx().analyze(_plain(payload), edges_))

    def version():
        """Which WebWeaveX is installed."""
        return getattr(_wwx(), "version", "unknown")

    return {"extract": extract, "crawl": crawl, "repo": repo, "docs": docs,
            "graph": graph, "nodes": nodes, "edges": edges, "query": query,
            "fingerprint": fingerprint, "kaalka_hash": kaalka_hash,
            "analyze": analyze, "version": version}
