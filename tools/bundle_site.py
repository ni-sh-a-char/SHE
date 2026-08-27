"""Copy the interpreter into the website so the playground can load it.

Pyodide runs real CPython in the browser, so the playground needs the actual
`she` package files. This copies them into `site/she-src/` and writes a
manifest the playground fetches. Run it before publishing the site:

    python tools/bundle_site.py
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "she"
TARGET = ROOT / "site" / "she-src"

# The playground never shells out, so the CLI and language server stay behind.
SKIP = {"cli.py", "lsp.py", "__main__.py"}


def main():
    if not SOURCE.is_dir():
        print(f"cannot find the she package at {SOURCE}", file=sys.stderr)
        return 1

    if TARGET.exists():
        shutil.rmtree(TARGET)
    (TARGET / "she" / "stdlib").mkdir(parents=True)

    files = []
    for path in sorted(SOURCE.rglob("*.py")):
        if path.name in SKIP or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(SOURCE.parent)
        destination = TARGET / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        files.append(relative.as_posix())

    version = "unknown"
    for line in (SOURCE / "__init__.py").read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            version = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

    manifest = {"version": version, "files": files}
    (TARGET / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total = sum((TARGET / name).stat().st_size for name in files)
    print(f"bundled {len(files)} files ({total // 1024} KB) into site/she-src/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
