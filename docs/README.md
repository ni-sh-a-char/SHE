# SHE – “A Programming Language”

> **SHE** (Simple, Human‑oriented, Extensible) is a modern, statically‑typed, multi‑paradigm programming language designed for readability, safety, and rapid development.  
> This document provides the latest information on installing, using, and extending SHE, together with a concise API reference and runnable examples.

---

## Table of Contents
1. [Installation](#installation)  
   1.1. [Pre‑built Binaries](#pre-built-binaries)  
   1.2. [Package Managers](#package-managers)  
   1.3. [Building from Source](#building-from-source)  
   1.4. [Docker & VS Code Extension](#docker--vscode-extension)  
2. [Usage](#usage)  
   2.1. [Command‑Line Interface (CLI)](#cli)  
   2.2. [REPL (Read‑Eval‑Print Loop)](#repl)  
   2.3. [Project Layout & Build System](#project-layout)  
   2.4. [Common Flags & Environment Variables](#flags)  
3. [API Documentation](#api-documentation)  
   3.1. [Core Language Constructs](#core-constructs)  
   3.2. [Standard Library Overview](#stdlib)  
   3.3. [Compiler & Runtime APIs](#compiler-runtime)  
   3.4. [Embedding SHE in Other Applications](#embedding)  
4. [Examples](#examples)  
   4.1. [Hello, World!](#hello-world)  
   4.2. [Basic Types & Control Flow](#basic-types)  
   4.3. [Functions & Generics](#functions-generics)  
   4.4. [Modules & Packages](#modules)  
   4.5. [Concurrency with `async`/`await`](#concurrency)  
   4.6. [Interoperability with C / Rust](#interop)  
5. [Contributing & Development Workflow](#contributing)  
6. [License](#license)  

---

<a name="installation"></a>
## 1. Installation

SHE can be installed on Windows, macOS, and Linux. Choose the method that best fits your workflow.

### 1.1. Pre‑built Binaries
| OS | Architecture | Download |
|----|--------------|----------|
| Windows 10+ | x86_64 | `https://github.com/yourorg/SHE/releases/latest/download/she-windows-x86_64.zip` |
| macOS 12+ | arm64 (Apple Silicon) | `https://github.com/yourorg/SHE/releases/latest/download/she-macos-arm64.tar.gz` |
| macOS 12+ | x86_64 | `https://github.com/yourorg/SHE/releases/latest/download/she-macos-x86_64.tar.gz` |
| Linux | x86_64 | `https://github.com/yourorg/SHE/releases/latest/download/she-linux-x86_64.tar.gz` |
| Linux | aarch64 | `https://github.com/yourorg/SHE/releases/latest/download/she-linux-aarch64.tar.gz` |

**Installation steps (Linux/macOS):**
```bash
# Example for Linux x86_64
curl -L -o she.tar.gz \
  https://github.com/yourorg/SHE/releases/latest/download/she-linux-x86_64.tar.gz
tar -xzf she.tar.gz -C $HOME/.local/bin
chmod +x $HOME/.local/bin/she
# Add to PATH if not already there
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

**Installation steps (Windows):**
1. Download the `.zip` file.
2. Extract to a folder, e.g., `C:\Program Files\SHE`.
3. Add that folder to **System → Environment Variables → Path**.
4. Open a new PowerShell window and run `she --version`.

### 1.2. Package Managers

| Manager | Command |
|---------|---------|
| **Homebrew (macOS/Linux)** | `brew install she-lang` |
| **Scoop (Windows)** | `scoop bucket add she https://github.com/yourorg/scoop-she && scoop install she` |
| **Cargo (Rust ecosystem)** | `cargo install she-cli` |
| **NPM (Node ecosystem)** | `npm i -g she-lang` |
| **Conda** | `conda install -c conda-forge she` |

> **Tip:** All package managers automatically keep SHE up‑to‑date. Use the manager’s upgrade command (`brew upgrade she`, `scoop update she`, etc.) to get the latest release.

### 1.3. Building from Source

> **Prerequisites**  
> - **Rust** (≥ 1.70) – `curl https://sh.rustup.rs -sSf | sh`  
> - **CMake** (≥ 3.20) – required for the native runtime.  
> - **Git** – to clone the repository.

```bash
# Clone the repo
git clone https://github.com/yourorg/SHE.git
cd SHE

# Build the compiler, standard library, and CLI
cargo build --release

# Install the binary to ~/.local/bin (or %USERPROFILE%\bin on Windows)
cargo install --path . --locked
```

**Optional components**
- `she-docs` – generates HTML API docs (`cargo install she-docs`).
- `she-lsp` – Language Server Protocol server for IDE integration (`cargo install she-lsp`).

### 1.4. Docker & VS Code Extension

**Docker image** (official, multi‑arch):
```bash
docker pull ghcr.io/yourorg/she:latest
docker run --rm -v "$(pwd)":/workspace -w /workspace ghcr.io/yourorg/she:latest she run main.she
```

**VS Code**: Install the **SHE Language Support** extension from the Marketplace. It bundles the LSP server, syntax highlighting, and a built‑in debugger.

---

<a name="usage"></a>
## 2. Usage

SHE ships a single binary (`she`) that doubles as a compiler, interpreter, and package manager.

### 2.1. Command‑Line Interface (CLI)

```text
she <command> [options] [args]

Commands:
  run <file>            Execute a SHE script (interpreted mode)
  build <dir>           Compile a project to a native binary
  test [<dir>]          Run unit tests
  fmt [<path>]          Format source files (uses shefmt)
  fmt-check [<path>]    Verify formatting without changing files
  doc [<path>]          Generate API documentation (HTML)
  repl                  Start an interactive REPL session
  new <project-name>    Scaffold a new SHE project
  add <crate>           Add a dependency to the manifest (she.toml)
  publish               Publish a package to the SHE registry
  version               Print version information
  help                  Show this help message
```

**Typical workflow**
```bash
# Create a new project
she new my_app
cd my_app

# Write code in src/main.she ...

# Run it instantly (interpreted)
she run src/main.she

# Or compile to a native binary
she build .
./target/release/my_app
```

### 2.2. REPL (Read‑Eval‑Print Loop)

```bash
$ she repl
SHE 0.9.3 (REPL) ── type :help for help
>>> let x = 42
>>> x * 2
84
>>> :exit
```

**REPL shortcuts**

| Shortcut | Action |
|----------|--------|
| `:help`  | Show REPL commands |
| `:reset` | Clear all definitions |
| `:load <file>` | Load a script into the current session |
| `:type <expr>` | Show the inferred type of an expression |
| `Ctrl‑D` | Exit REPL |

### 2.3. Project Layout & Build System

A **SHE project** follows the conventional layout:

```
my_app/
├─ she.toml          # Manifest (name, version, dependencies)
├─ src/
│   ├─ main.she      # Entry point (optional)
│   └─ lib.she       # Library code
├─ tests/
│   └─ lib_test.she # Unit tests
└─ examples/
    └─ hello.she    # Example programs
```

**`she.toml` example**

```toml
[package]
name = "my_app"
version = "0.1.0