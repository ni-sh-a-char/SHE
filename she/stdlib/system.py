"""fs, http and os modules.

Everything here touches the outside world, so every function asks the sandbox
for permission first. Without the matching --allow-* flag the call fails with a
message naming the exact flag needed.
"""

import os as _os
import shutil as _shutil
import subprocess as _subprocess
import sys as _sys
from pathlib import Path as _Path

from ..errors import ValueErr
from ..values import iterate, show, type_name
from . import register

MAX_READ = 64 * 1024 * 1024        # a 64 MB ceiling keeps a typo from eating memory
MAX_RESPONSE = 32 * 1024 * 1024


@register("fs", "Files and folders. Needs --allow-read / --allow-write.")
def _fs_module():
    def _path(value):
        if not isinstance(value, str):
            raise ValueErr(f"a file path has to be text, not a {type_name(value)}")
        return _os.path.expanduser(value)

    def read(interp, path):
        """The whole file as text."""
        target = _path(path)
        interp.sandbox.check_path(target, "read")
        try:
            size = _os.path.getsize(target)
        except OSError as exc:
            raise ValueErr(f"I could not open `{path}`: {exc.strerror or exc}")
        if size > MAX_READ:
            raise ValueErr(f"`{path}` is {size // 1048576} MB, which is too big to read at once",
                           hint="use `fs.read_lines` and work through it a line at a time.")
        try:
            with open(target, encoding="utf-8") as handle:
                return handle.read()
        except UnicodeDecodeError:
            raise ValueErr(f"`{path}` is not text",
                           hint="use `fs.read_bytes` for images and other binary files.")
        except OSError as exc:
            raise ValueErr(f"I could not read `{path}`: {exc.strerror or exc}")

    def read_lines(interp, path):
        """The file as a list of lines, with the line endings removed."""
        return read(interp, path).splitlines()

    def read_bytes(interp, path):
        """The raw contents of a file."""
        target = _path(path)
        interp.sandbox.check_path(target, "read")
        try:
            with open(target, "rb") as handle:
                return handle.read(MAX_READ)
        except OSError as exc:
            raise ValueErr(f"I could not read `{path}`: {exc.strerror or exc}")

    def write(interp, path, content):
        """Write text to a file, replacing whatever was there."""
        target = _path(path)
        interp.sandbox.check_path(target, "write")
        text = content if isinstance(content, str) else show(content)
        try:
            _os.makedirs(_os.path.dirname(_os.path.abspath(target)) or ".", exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            raise ValueErr(f"I could not write `{path}`: {exc.strerror or exc}")
        return len(text)

    def append(interp, path, content):
        """Add text to the end of a file."""
        target = _path(path)
        interp.sandbox.check_path(target, "write")
        text = content if isinstance(content, str) else show(content)
        try:
            with open(target, "a", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            raise ValueErr(f"I could not write `{path}`: {exc.strerror or exc}")
        return len(text)

    def exists(interp, path):
        """True when something is there."""
        target = _path(path)
        interp.sandbox.check_path(target, "read")
        return _os.path.exists(target)

    def is_file(interp, path):
        """True when the path is a file."""
        target = _path(path)
        interp.sandbox.check_path(target, "read")
        return _os.path.isfile(target)

    def is_folder(interp, path):
        """True when the path is a folder."""
        target = _path(path)
        interp.sandbox.check_path(target, "read")
        return _os.path.isdir(target)

    def list_(interp, path=".", pattern=None):
        """The names inside a folder, optionally filtered by a pattern like *.txt."""
        target = _path(path)
        interp.sandbox.check_path(target, "read")
        try:
            names = sorted(_os.listdir(target))
        except OSError as exc:
            raise ValueErr(f"I could not list `{path}`: {exc.strerror or exc}")
        if pattern:
            import fnmatch
            names = [n for n in names if fnmatch.fnmatch(n, str(pattern))]
        return names

    def walk(interp, path=".", pattern="*"):
        """Every matching file inside a folder and all its sub-folders."""
        target = _path(path)
        interp.sandbox.check_path(target, "read")
        out = []
        for found in sorted(_Path(target).rglob(str(pattern))):
            if found.is_file():
                out.append(str(found))
                if len(out) > 100000:
                    break
        return out

    def make_folder(interp, path):
        """Create a folder, including any parents."""
        target = _path(path)
        interp.sandbox.check_path(target, "write")
        _os.makedirs(target, exist_ok=True)
        return target

    def remove(interp, path):
        """Delete a file, or an empty folder."""
        target = _path(path)
        interp.sandbox.check_path(target, "write")
        try:
            if _os.path.isdir(target):
                _os.rmdir(target)
            else:
                _os.remove(target)
        except OSError as exc:
            raise ValueErr(f"I could not remove `{path}`: {exc.strerror or exc}",
                           hint="use `fs.remove_folder` to delete a folder that is not empty.")
        return True

    def remove_folder(interp, path):
        """Delete a folder and everything inside it. Cannot be undone."""
        target = _path(path)
        interp.sandbox.check_path(target, "write")
        resolved = _os.path.abspath(target)
        if resolved in (_os.path.abspath(_os.sep), _os.path.expanduser("~")):
            raise ValueErr("refusing to delete that folder",
                           hint="deleting your home or root folder is never what you meant.")
        _shutil.rmtree(resolved, ignore_errors=False)
        return True

    def copy(interp, source, destination):
        """Copy a file."""
        src, dst = _path(source), _path(destination)
        interp.sandbox.check_path(src, "read")
        interp.sandbox.check_path(dst, "write")
        _shutil.copy2(src, dst)
        return dst

    def move(interp, source, destination):
        """Move or rename a file."""
        src, dst = _path(source), _path(destination)
        interp.sandbox.check_path(src, "write")
        interp.sandbox.check_path(dst, "write")
        _shutil.move(src, dst)
        return dst

    def size(interp, path):
        """How many bytes a file holds."""
        target = _path(path)
        interp.sandbox.check_path(target, "read")
        try:
            return _os.path.getsize(target)
        except OSError as exc:
            raise ValueErr(f"I could not measure `{path}`: {exc.strerror or exc}")

    def modified(interp, path):
        """When a file last changed, as a timestamp."""
        target = _path(path)
        interp.sandbox.check_path(target, "read")
        return _os.path.getmtime(target)

    def join(*parts):
        """Build a path from pieces, using the right separator for this system."""
        return _os.path.join(*[str(p) for p in parts])

    def name(path):
        """The last piece of a path."""
        return _os.path.basename(str(path))

    def folder(path):
        """Everything but the last piece of a path."""
        return _os.path.dirname(str(path))

    def extension(path):
        """The file extension, including the dot."""
        return _os.path.splitext(str(path))[1]

    def absolute(path):
        """The full path from the root of the filesystem."""
        return _os.path.abspath(_path(path))

    return {"read": read, "read_lines": read_lines, "read_bytes": read_bytes,
            "write": write, "append": append, "exists?": exists, "file?": is_file,
            "folder?": is_folder, "list": list_, "walk": walk,
            "make_folder": make_folder, "remove": remove,
            "remove_folder": remove_folder, "copy": copy, "move": move,
            "size": size, "modified": modified, "join": join, "name": name,
            "folder": folder, "extension": extension, "absolute": absolute}


@register("http", "Talking to the web. Needs --allow-net.")
def _http_module():
    import urllib.error
    import urllib.parse
    import urllib.request

    def _request(interp, method, url, body=None, headers=None, timeout=30):
        if not isinstance(url, str):
            raise ValueErr(f"a URL has to be text, not a {type_name(url)}")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueErr(f"`{url}` is not an http or https address",
                           hint="URLs start with https://")
        if parsed.scheme == "http" and not interp.sandbox.granted("net"):
            pass
        interp.sandbox.check_host(url)
        data = None
        send_headers = {"User-Agent": "she-lang/2.0"}
        for key, value in (headers or {}).items():
            send_headers[str(key)] = str(value)
        if body is not None:
            if isinstance(body, (dict, list)):
                import json as _json

                from .data import _to_plain
                data = _json.dumps(_to_plain(body)).encode()
                send_headers.setdefault("Content-Type", "application/json")
            else:
                data = str(body).encode()
        request = urllib.request.Request(url, data=data, headers=send_headers,
                                         method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=float(timeout)) as response:
                raw = response.read(MAX_RESPONSE)
                charset = response.headers.get_content_charset() or "utf-8"
                try:
                    text = raw.decode(charset, errors="replace")
                except LookupError:
                    text = raw.decode("utf-8", errors="replace")
                return {"status": response.status, "ok": 200 <= response.status < 300,
                        "body": text, "headers": dict(response.headers),
                        "url": response.url}
        except urllib.error.HTTPError as exc:
            body_text = exc.read(MAX_RESPONSE).decode("utf-8", errors="replace")
            return {"status": exc.code, "ok": False, "body": body_text,
                    "headers": dict(exc.headers or {}), "url": url}
        except urllib.error.URLError as exc:
            raise ValueErr(f"I could not reach `{url}`: {exc.reason}",
                           hint="check the address and that you are online.")
        except TimeoutError:
            raise ValueErr(f"`{url}` did not answer within {timeout} seconds")

    def get(interp, url, headers=None, timeout=30):
        """Fetch a page or an API response."""
        return _request(interp, "GET", url, None, headers, timeout)

    def post(interp, url, body=None, headers=None, timeout=30):
        """Send data. Maps and lists are sent as JSON."""
        return _request(interp, "POST", url, body, headers, timeout)

    def put(interp, url, body=None, headers=None, timeout=30):
        """Replace something at a URL."""
        return _request(interp, "PUT", url, body, headers, timeout)

    def patch(interp, url, body=None, headers=None, timeout=30):
        """Change part of something at a URL."""
        return _request(interp, "PATCH", url, body, headers, timeout)

    def delete(interp, url, headers=None, timeout=30):
        """Remove something at a URL."""
        return _request(interp, "DELETE", url, None, headers, timeout)

    def json_(interp, url, headers=None, timeout=30):
        """Fetch a URL and read the answer as JSON."""
        response = get(interp, url, headers, timeout)
        import json as _json
        try:
            return _json.loads(response["body"])
        except _json.JSONDecodeError:
            raise ValueErr(f"`{url}` did not answer with JSON",
                           hint="use `http.get` to see the raw body.")

    def download(interp, url, path, timeout=60):
        """Save what is at a URL into a file."""
        interp.sandbox.check_host(url)
        interp.sandbox.check_path(path, "write")
        response = _request(interp, "GET", url, None, None, timeout)
        with open(_os.path.expanduser(str(path)), "w", encoding="utf-8") as handle:
            handle.write(response["body"])
        return path

    def encode(value):
        """Make text safe to put inside a URL."""
        return urllib.parse.quote(str(value), safe="")

    def decode(value):
        """Read URL-encoded text back."""
        return urllib.parse.unquote(str(value))

    def query(values):
        """Turn a map into a ?key=value query string."""
        if not isinstance(values, dict):
            raise ValueErr("`http.query` needs a map")
        return urllib.parse.urlencode({str(k): show(v) if not isinstance(v, str) else v
                                       for k, v in values.items()})

    return {"get": get, "post": post, "put": put, "patch": patch,
            "delete": delete, "json": json_, "download": download,
            "encode": encode, "decode": decode, "query": query}


@register("os", "The machine SHE is running on. Needs --allow-env / --allow-run.")
def _os_module():
    def env(interp, name, fallback=None):
        """Read an environment variable."""
        interp.sandbox.require("env", str(name))
        return _os.environ.get(str(name), fallback)

    def env_all(interp):
        """Every environment variable as a map."""
        interp.sandbox.require("env")
        return dict(_os.environ)

    def args(interp):
        """Whatever was typed after the script name."""
        return list(getattr(interp, "script_args", []))

    def platform():
        """windows, macos, linux, or something else."""
        return {"win32": "windows", "darwin": "macos"}.get(_sys.platform, "linux")

    def cwd(interp):
        """The folder the program was started from."""
        interp.sandbox.require("read", action="see the current folder")
        return _os.getcwd()

    def user(interp):
        """The name of whoever is logged in."""
        interp.sandbox.require("env", "USER")
        return _os.environ.get("USER") or _os.environ.get("USERNAME") or "unknown"

    def run(interp, command, arguments=None, timeout=60):
        """Start another program and collect what it prints."""
        interp.sandbox.require("run", str(command))
        argv = [str(command)] + [str(a) for a in iterate(arguments or [])]
        try:
            done = _subprocess.run(argv, capture_output=True, text=True,
                                   timeout=float(timeout), shell=False, check=False)
        except FileNotFoundError:
            raise ValueErr(f"there is no program called `{command}`")
        except _subprocess.TimeoutExpired:
            raise ValueErr(f"`{command}` did not finish within {timeout} seconds")
        return {"code": done.returncode, "ok": done.returncode == 0,
                "output": done.stdout, "errors": done.stderr}

    def cpu_count():
        """How many processors this machine has."""
        return _os.cpu_count() or 1

    def she_version():
        """Which version of SHE is running."""
        from .. import __version__
        return __version__

    return {"env": env, "env_all": env_all, "args": args, "platform": platform,
            "cwd": cwd, "user": user, "run": run, "cpu_count": cpu_count,
            "version": she_version}
