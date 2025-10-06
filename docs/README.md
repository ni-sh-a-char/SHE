# SHE – *A Programming Language*  
**Version:** 1.4.2 (2025‑09‑30)  
**Repository:** https://github.com/your-org/SHE  

---

## Table of Contents
1. [Overview](#overview)  
2. [Installation](#installation)  
   - [Prerequisites](#prerequisites)  
   - [Binary Releases](#binary-releases)  
   - [Building from Source](#building-from-source)  
   - [Docker Image](#docker-image)  
   - [Package Manager (Homebrew / Scoop)](#package-manager)  
3. [Usage](#usage)  
   - [REPL](#repl)  
   - [Compiling & Running](#compiling-and-running)  
   - [Project Layout](#project-layout)  
   - [Command‑Line Options](#command-line-options)  
4. [API Documentation](#api-documentation)  
   - [Core Packages](#core-packages)  
   - [Standard Library](#standard-library)  
   - [Embedding SHE in Other Apps](#embedding-she)  
5. [Examples](#examples)  
   - [Hello, World!](#hello-world)  
   - [Basic I/O](#basic-io)  
   - [Functions & Closures](#functions-closures)  
   - [Pattern Matching](#pattern-matching)  
   - [Concurrency (Actors)](#concurrency-actors)  
   - [Embedding SHE in Go](#embedding-in-go)  
6. [Contributing](#contributing)  
7. [License](#license)  

---  

## Overview <a name="overview"></a>

SHE (pronounced “sh”) is a modern, statically‑typed, functional‑imperative programming language designed for **simplicity**, **expressiveness**, and **high‑performance** execution. It ships with a fast ahead‑of‑time compiler (`shec`), an interactive REPL (`she`), and a small but powerful standard library.

Key features:

| Feature | Description |
|---------|-------------|
| **Static typing with type inference** | No need for explicit type annotations in most cases. |
| **Pattern matching** | Exhaustive, first‑class pattern matching on algebraic data types. |
| **Immutable by default** | Mutability is opt‑in via `mut`. |
| **Concurrent actors** | Lightweight actors with mailbox semantics. |
| **Seamless C/Go interop** | Call native functions directly from SHE. |
| **Extensible standard library** | Modules for I/O, networking, crypto, data structures, etc. |
| **Tooling** | REPL, LSP server, formatter (`shefmt`), and debugger (`shedb`). |

---  

## Installation <a name="installation"></a>

### Prerequisites <a name="prerequisites"></a>

| OS | Required |
|----|----------|
| Linux (glibc ≥ 2.28) | `gcc`/`clang` ≥ 10, `make`, `git` |
| macOS (Catalina+) | Xcode command‑line tools |
| Windows 10+ | Visual Studio Build Tools 2022 (or MSYS2) |
| Docker | Docker Engine ≥ 20.10 |

> **Tip:** The binary releases are built with `musl` on Linux, so they run on any glibc version.

### Binary Releases <a name="binary-releases"></a>

1. Download the appropriate archive from the **Releases** page:  

   ```bash
   # Linux (x86_64)
   curl -LO https://github.com/your-org/SHE/releases/download/v1.4.2/she-v1.4.2-linux-x86_64.tar.gz
   tar -xzf she-v1.4.2-linux-x86_64.tar.gz
   sudo mv she /usr/local/bin/
   ```

   ```powershell
   # Windows (x86_64)
   Invoke-WebRequest -Uri https://github.com/your-org/SHE/releases/download/v1.4.2/she-v1.4.2-windows-x86_64.zip -OutFile she.zip
   Expand-Archive she.zip -DestinationPath $env:USERPROFILE\bin
   ```

2. Verify the installation:

   ```bash
   $ shec --version
   SHE Compiler version 1.4.2
   ```

### Building from Source <a name="building-from-source"></a>

```bash
# Clone the repo
git clone https://github.com/your-org/SHE.git
cd SHE

# Checkout the latest stable tag (optional)
git checkout v1.4.2

# Build (requires Go ≥ 1.22)
make all          # builds shec, she (REPL), shefmt, shedb
sudo make install # installs binaries to /usr/local/bin (Linux/macOS)
```

**Makefile targets**

| Target | Description |
|--------|-------------|
| `all` | Build all executables (`shec`, `she`, `shefmt`, `shedb`). |
| `test` | Run the full test suite (`go test ./...`). |
| `bench` | Run benchmarks (`go test -bench=. ./...`). |
| `clean` | Remove generated files. |
| `install` | Copy binaries to `$PREFIX/bin` (`/usr/local` by default). |

### Docker Image <a name="docker-image"></a>

A minimal Docker image is published to Docker Hub:

```bash
docker pull yourorg/she:1.4.2
docker run --rm -it yourorg/she:1.4.2 she --help
```

You can also mount a local project:

```bash
docker run --rm -it \
  -v "$(pwd)":/workspace \
  -w /workspace \
  yourorg/she:1.4.2 \
  shec build .
```

### Package Manager (Homebrew / Scoop) <a name="package-manager"></a>

- **macOS (Homebrew)**  

  ```bash
  brew tap your-org/she
  brew install she
  ```

- **Windows (Scoop)**  

  ```powershell
  scoop bucket add she https://github.com/your-org/scoop-she.git
  scoop install she
  ```

---  

## Usage <a name="usage"></a>

### REPL <a name="repl"></a>

Start an interactive session:

```bash
$ she
SHE 1.4.2 (repl) ── type `:help` for commands
>>> let x = 42
>>> x * 2
84
>>> :quit
```

**REPL shortcuts**

| Shortcut | Action |
|----------|--------|
| `Ctrl‑L` | Clear screen |
| `:load <file>` | Load a script into the current session |
| `:type <expr>` | Show inferred type |
| `:reset` | Reset the REPL state |
| `:help` | Show help |

### Compiling & Running <a name="compiling-and-running"></a>

```bash
# Compile a single file
shec build hello.she -o hello

# Run the compiled binary
./hello

# Compile a whole project (looks for she.mod)
shec build . -o myapp
```

**Project layout**

```
myapp/
├─ she.mod          # module definition (name, version, dependencies)
├─ src/
│   ├─ main.she     # entry point (must contain `fn main() -> Int { … }`)
│   └─ lib/
│       └─ utils.she
└─ tests/
    └─ utils_test.she
```

### Command‑Line Options <a name="command-line-options"></a>

| Flag | Description |
|------|-------------|
| `-o <file>` | Output binary name (default: `a.out`). |
| `-I <dir>` | Add an import search path. |
| `-L <dir>` | Add a native library search path (for `extern`). |
| `-g` | Emit debug symbols (for `shedb`). |
| `-O0 … -O3` | Optimization level (default `-O2`). |
| `--target <arch>` | Cross‑compile (`x86_64`, `aarch64`, `wasm32`). |
| `--fmt` | Run the formatter on source files (alias for `shefmt`). |
| `--version` | Print version and exit. |
| `--help` | Show help. |

---  

## API Documentation <a name="api-documentation"></a>

> **NOTE:** The API docs are generated automatically with `godoc`‑style comments and are hosted at https://your