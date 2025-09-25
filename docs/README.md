# SHE – “A Programming Language”

> **SHE** (Simple, Human‑friendly, Extensible) is a lightweight, interpreted programming language designed for rapid prototyping, scripting, and teaching.  
> It ships with a REPL, a standard library, and a clean, extensible API that lets you embed the interpreter in your own applications.

---  

## Table of Contents
1. [Installation](#installation)  
2. [Quick Start / Usage](#quick-start--usage)  
3. [Command‑Line Interface (CLI)](#command-line-interface-cli)  
4. [Embedding SHE in Your Projects (API)](#embedding-she-in-your-projects-api)  
5. [Standard Library Overview](#standard-library-overview)  
6. [Examples](#examples)  
7. [Contributing & Development](#contributing--development)  
8. [License](#license)  

---  

## Installation

### Prerequisites
| Tool | Minimum version |
|------|-----------------|
| **Python** | 3.9 (used for the build tools) |
| **C compiler** | GCC ≥ 7 or Clang ≥ 6 (required only for optional native extensions) |
| **Git** | any recent version (for cloning) |

> **Note** – The core interpreter is pure‑Python, so you can run SHE on any platform that supports Python 3.9+. Native extensions (e.g., JIT, FFI) are optional.

### 1. Install from PyPI (recommended)

```bash
pip install she-lang
```

This command installs:

* `she` – the interpreter binary (`she` command)  
* `she-runtime` – the standard library package  
* `she-dev` – optional development tools (linters, formatters)

### 2. Install from source (latest development version)

```bash
# Clone the repository
git clone https://github.com/your-org/SHE.git
cd SHE

# Create a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install the package in editable mode
pip install -e .
```

> **Tip** – After a source install, the `she` command points to the local checkout, so you can test changes instantly.

### 3. Verify the installation

```bash
she --version
# Expected output, e.g.: SHE 1.4.2
```

If you see the version string, you’re ready to go!

---  

## Quick Start / Usage

### Running a script

```bash
she path/to/script.she
```

### Starting an interactive REPL

```bash
she
```

You’ll see the familiar prompt:

```
SHE 1.4.2 >>> 
```

### One‑liner execution

```bash
she -c "print('Hello, SHE!')"
```

### Passing arguments to a script

Inside a SHE script you can access the command‑line arguments via the built‑in `argv` array:

```she
# hello.she
print("Script name:", argv[0])
print("Arguments:", argv[1:])
```

```bash
she hello.she foo bar
# Output:
# Script name: hello.she
# Arguments: ['foo', 'bar']
```

---  

## Command Line Interface (CLI)

| Option | Alias | Description |
|--------|-------|-------------|
| `-c <code>` | – | Execute the supplied code string and exit. |
| `-i` | – | Force interactive mode after executing a script or `-c` code. |
| `-v` | `--version` | Print the interpreter version and exit. |
| `-h` | `--help` | Show the help message. |
| `--no-stdlib` | – | Run the interpreter without loading the standard library (useful for sandboxing). |
| `--log <file>` | – | Write runtime logs to the specified file (debugging). |
| `--opt <level>` | – | Set optimization level (`0` = none, `1` = basic, `2` = aggressive). |

**Example – Running with logging and no standard library**

```bash
she --no-stdlib --log she.log my_script.she
```

---  

## Embedding SHE in Your Projects (API)

SHE can be embedded as a library, allowing you to evaluate SHE code, expose host functions, or build custom REPLs.

### 1. Import the interpreter

```python
from she import Interpreter, RuntimeError
```

### 2. Create an interpreter instance

```python
interp = Interpreter()
```

### 3. Execute code

```python
result = interp.eval("2 + 2")
print(result)   # → 4
```

### 4. Register a host function

```python
def py_greet(name: str) -> str:
    return f"Hello from Python, {name}!"

interp.register_function("greet", py_greet)

# Now usable from SHE:
interp.eval('print(greet("SHE"))')
# → Hello from Python, SHE!
```

### 5. Capture stdout / stderr

```python
from io import StringIO

out_buf = StringIO()
err_buf = StringIO()

interp.set_output(out_buf, err_buf)

interp.eval('print("Hello")')
print("Captured:", out_buf.getvalue())   # → Captured: Hello\n
```

### 6. Using the REPL programmatically

```python
from she.repl import REPL

repl = REPL(interpreter=interp)
repl.run()   # Starts an interactive session inside your Python process
```

### 7. Loading modules dynamically

```python
interp.import_module("math")   # Loads the built‑in math module
print(interp.eval("math.sqrt(16)"))   # → 4.0
```

### 8. Error handling

```python
try:
    interp.eval("unknown_var + 1")
except RuntimeError as exc:
    print("SHE error:", exc)
```

---  

## Standard Library Overview

| Module | Description | Example |
|--------|-------------|---------|
| `io` | File I/O, streams, and buffered readers/writers. | `f = open("data.txt", "r")` |
| `math` | Common mathematical functions (`sin`, `cos`, `sqrt`, …). | `math.sqrt(9)` |
| `json` | Encode/decode JSON data. | `json.encode({a:1})` |
| `time` | Time utilities (`now`, `sleep`, `format`). | `time.sleep(0.5)` |
| `os` | OS interaction (env vars, process control). | `os.getenv("HOME")` |
| `collections` | Data structures (`list`, `map`, `set`, `queue`). | `queue = collections.Queue()` |
| `http` | Simple HTTP client (`get`, `post`). | `http.get("https://api.example.com")` |
| `ffi` *(optional)* | Foreign Function Interface for calling C libraries. | `ffi.load("libc.so").printf("Hi\n")` |

> **Tip** – To keep the runtime minimal, the interpreter loads the standard library lazily (on first use). Use `--no-stdlib` to disable it entirely.

---  

## Examples

### 1. Hello World

```she
# hello.she
print("Hello, SHE!")
```

```bash
she hello.she
```

### 2. Fibonacci (recursive)

```she
# fib.she
def fib(n) {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}

for i in 0..10 {
    print(i, "→", fib(i))
}
```

### 3. Simple HTTP GET

```she
import http

resp = http.get("https://api.github.com/repos/your-org/SHE")
if resp.status == 200 {
    data = json.decode(resp.body)
    print("Stars:", data["stargazers_count"])
} else {
    print("Request failed:", resp.status)
}
```

### 4. Embedding SHE in a Python CLI tool

```python
# cli_tool.py
import argparse
from she import Interpreter

parser = argparse.ArgumentParser(description="Run SHE snippets")
parser.add_argument("code", help="SHE code to execute")
args = parser.parse_args()

interp = Interpreter()
result = interp.eval(args.code)
print("Result →", result)
```

```bash
python cli_tool.py "len([1,2,3,4]) * 2"
# Output: Result → 8
```

### 5. Using the FFI (optional native extension)

```she
# ffi_example.she
import ffi

# Load the C standard library (platform‑specific name)
libc = ffi.load("libc.so.6")   # Linux; use "msvcrt.dll" on Windows

# Call printf directly
libc.printf("Hello from C! Number: %d\n", 42)
```

### 6. Building a tiny web server (using `http`)

```she
import http

fn handler(req) {
    return {
        "status": 200,
        "headers": {"Content-Type