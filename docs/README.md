# SHE – A Programming Language  
**Repository:** `github.com/your-org/SHE`  
**Current version:** `v2.4.1` (released 2025‑09‑20)  

> **SHE** (pronounced “sh‑ee”) is a modern, statically‑typed, compiled language designed for rapid prototyping, safe concurrency, and seamless inter‑op with existing C/C++/Rust ecosystems. It ships with a fast LLVM‑based compiler, an interactive REPL, and a rich standard library.

---

## Table of Contents
1. [Installation](#installation)  
2. [Quick Start / Usage](#quick-start--usage)  
3. [Command‑Line Interface (CLI)](#command-line-interface-cli)  
4. [API Documentation](#api-documentation)  
5. [Standard Library Overview](#standard-library-overview)  
6. [Examples](#examples)  
7. [Contributing & Development](#contributing--development)  
8. [License](#license)  

---  

## Installation  

SHE can be installed on Linux, macOS, and Windows. Choose the method that best fits your workflow.

### 1. Pre‑built Binaries (recommended)

| OS | Architecture | Download |
|----|--------------|----------|
| Linux (glibc) | x86_64 | `curl -L https://github.com/your-org/SHE/releases/download/v2.4.1/she-linux-x86_64.tar.gz \| tar -xz && sudo mv she /usr/local/bin/` |
| macOS (Apple Silicon) | arm64 | `brew install your-org/tap/she` |
| macOS (Intel) | x86_64 | `brew install your-org/tap/she` |
| Windows | x86_64 | Download `she-windows-x86_64.zip` from the releases page, extract, and add the `she.exe` folder to your `PATH`. |

> **Tip:** Verify the installation with `she --version`. You should see `she version 2.4.1`.

### 2. Install via Package Managers  

| Manager | Command |
|---------|---------|
| **Homebrew (macOS/Linux)** | `brew install your-org/tap/she` |
| **Scoop (Windows)** | `scoop bucket add your-org https://github.com/your-org/scoop-bucket.git`<br>`scoop install she` |
| **Cargo (Rust)** | `cargo install shec` *(installs only the compiler front‑end)* |
| **Conda** | `conda install -c conda-forge she` |

### 3. Build from Source  

> **Prerequisites**  
> - **LLVM 16+** (or use the bundled LLVM via `./scripts/setup-llvm.sh`)  
> - **CMake ≥ 3.20**  
> - **Git**  
> - **A C++20‑compatible compiler** (gcc‑13, clang‑16, MSVC 19.38+)

```bash
# Clone the repo
git clone https://github.com/your-org/SHE.git
cd SHE

# Optional: fetch sub‑modules (e.g., stdlib tests)
git submodule update --init --recursive

# Build (Release)
mkdir -p build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --target all -j$(nproc)

# Install system‑wide (requires sudo on *nix)
sudo cmake --install .
```

The build produces three primary artifacts:

| Artifact | Description |
|----------|-------------|
| `shec`   | The compiler driver (`shec <source> -o <binary>`). |
| `she-repl` | Interactive REPL (`she-repl`). |
| `she-lib` | Static library (`libshe.a`) for embedding the runtime in other projects. |

### 4. Docker (for CI / sandboxed environments)

```dockerfile
FROM ghcr.io/your-org/she:2.4.1
WORKDIR /app
COPY . .
RUN shec main.she -o /app/main
CMD ["/app/main"]
```

Pull the image: `docker pull ghcr.io/your-org/she:2.4.1`.

---

## Quick Start / Usage  

### 1. Hello, World!

Create a file `hello.she`:

```she
// hello.she
import std.io;

fn main() -> i32 {
    io.println("Hello, SHE!");
    return 0;
}
```

Compile and run:

```bash
shec hello.she -o hello
./hello
# → Hello, SHE!
```

### 2. REPL

```bash
she-repl
>>> let x: i32 = 42;
>>> x * 2
84
>>> :quit
```

### 3. Project Layout (recommended)

```
my_project/
├─ src/
│   ├─ main.she
│   └─ utils.she
├─ tests/
│   └─ utils_test.she
├─ she.toml          # project manifest (see below)
└─ README.md
```

#### `she.toml` – Minimal Manifest

```toml
[package]
name = "my_project"
version = "0.1.0"
edition = "2025"

[dependencies]
std = "2.4"
```

Build the whole project with the **project mode**:

```bash
shec build          # equivalent to `shec src/main.she -o my_project`
```

### 4. Common CLI Flags

| Flag | Description |
|------|-------------|
| `-o <file>` | Output binary name (default: `a.out`). |
| `-O0 … -O3` | Optimization level (default: `-O2`). |
| `-g` | Emit debug symbols (useful with `lldb` or `gdb`). |
| `--target <triple>` | Cross‑compile (e.g., `x86_64-pc-windows-msvc`). |
| `--emit <type>` | Emit intermediate artifacts (`llvm-ir`, `obj`, `asm`). |
| `--run` | Compile **and** execute in one step (`shec foo.she --run`). |
| `--repl` | Shortcut to start the REPL (`shec --repl`). |
| `--test` | Run all `*_test.she` files under `tests/`. |
| `--fmt` | Auto‑format source files (uses `shefmt`). |
| `--doc` | Generate API docs (see **API Documentation** section). |

---

## Command‑Line Interface (CLI)

```
shec [OPTIONS] <INPUT>...

Options:
  -o <FILE>            Write output to <FILE>
  -O0|-O1|-O2|-O3      Optimization level (default -O2)
  -g                   Generate debug info
  --target <TRIPLE>    Cross‑compile target
  --emit <TYPE>        Emit intermediate files (llvm-ir|obj|asm)
  --run                Compile and immediately run
  --repl               Start interactive REPL
  --test               Run test suite
  --fmt                Format source files
  --doc                Generate documentation (HTML)
  -h, --help           Print help information
  -V, --version        Print version information
```

**Examples**

```bash
# Compile with maximum optimizations and run
shec -O3 main.she --run

# Cross‑compile for ARM Linux
shec -O2 --target aarch64-unknown-linux-gnu src/main.she -o myapp

# Generate LLVM IR for inspection
shec --emit llvm-ir src/main.she -o main.ll

# Run all tests
shec --test
```

---

## API Documentation  

SHE ships with a built‑in documentation generator (`shec --doc`). The generated HTML lives under `target/doc/` and can be served locally with any static file server.

### 1. Core Language Constructs  

| Construct | Syntax | Description |
|-----------|--------|-------------|
| **Functions** | `fn name(arg: Type) -> ReturnType { … }` | First‑class, can be generic, supports overloading. |
| **Structs** | `struct Point { x: f64, y: f64 }` | Value types with optional `impl` blocks. |
| **Enums** | `enum Result<T, E> { Ok(T), Err(E) }` | Tagged unions with pattern matching. |
| **Traits** | `trait Display { fn fmt(&self) -> String; }` | Similar to Rust traits; can be auto‑implemented. |
| **Generics** | `fn map<T, U>(arr: []T, f: fn(T) -> U) -> []U` | Fully monomorphized at compile time. |
| **Concurrency** | `spawn fn foo() { … }` | Light‑weight green threads (fibers) built on top of OS threads. |
| **Unsafe** | `unsafe { … }` | Allows raw pointer manipulation, FFI, and manual memory