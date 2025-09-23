# SHE – A Programming Language  
**Repository:** `SHE`  
**Description:** *A Programming Language*  

---  

## Table of Contents
1. [Overview](#overview)  
2. [Installation](#installation)  
   - [Prerequisites](#prerequisites)  
   - [Binary Release (Linux/macOS/Windows)](#binary-release)  
   - [Build from Source](#build-from-source)  
   - [Docker Image](#docker-image)  
3. [Quick‑Start Usage](#quick-start-usage)  
   - [Running a SHE script](#running-a-she-script)  
   - [REPL (Read‑Eval‑Print Loop)](#repl)  
   - [Compiler Options](#compiler-options)  
4. [API Documentation](#api-documentation)  
   - [Core Packages](#core-packages)  
   - [Standard Library](#standard-library)  
   - [Embedding SHE in Other Projects](#embedding-she)  
5. [Examples](#examples)  
   - [Hello World](#hello-world)  
   - [Data‑Processing Pipeline](#data-processing-pipeline)  
   - [Web Server with SHE](#web-server-with-she)  
   - [Embedding SHE in Python](#embedding-she-in-python)  
6. [Contributing](#contributing)  
7. [License](#license)  
8. [Resources & Community](#resources)  

---  

## Overview
SHE (pronounced “sh‑ee”) is a modern, statically‑typed, compiled programming language designed for **simplicity**, **performance**, and **extensibility**. It blends the ergonomics of scripting languages with the speed of low‑level compiled languages, making it ideal for:

* System utilities and command‑line tools  
* High‑performance data pipelines  
* Embedded scripting in larger applications  
* Rapid prototyping of algorithms  

The language ships with a **single‑binary toolchain** (`shec` – the compiler, `she` – the REPL/runtime) and a **standard library** that covers I/O, networking, concurrency, and more.

---  

## Installation  

### Prerequisites
| Platform | Required Tools |
|----------|----------------|
| **Linux** (glibc ≥ 2.17) | `glibc`, `gcc`/`clang` (only for building from source) |
| **macOS** (10.14+) | Xcode command‑line tools (`xcode-select --install`) |
| **Windows** (10+) | Visual Studio Build Tools 2019+ (for source builds) or PowerShell 5+ |
| **Docker** | Docker Engine ≥ 20.10 |

> **Tip:** The binary releases are **statically linked** on Linux/macOS, so you don’t need any runtime dependencies.

---

### Binary Release (Linux/macOS/Windows)

1. **Download** the latest release from the GitHub releases page:  

   ```bash
   # Linux (x86_64)
   curl -L -o she.tar.gz https://github.com/yourorg/SHE/releases/download/vX.Y.Z/she-linux-x86_64.tar.gz

   # macOS (Apple Silicon)
   curl -L -o she.tar.gz https://github.com/yourorg/SHE/releases/download/vX.Y.Z/she-macos-arm64.tar.gz

   # Windows (x86_64)
   curl -L -o she.zip https://github.com/yourorg/SHE/releases/download/vX.Y.Z/she-windows-x86_64.zip
   ```

2. **Extract** the archive and add the `bin/` directory to your `PATH`:

   ```bash
   # Linux/macOS
   tar -xzf she.tar.gz
   sudo mv she/bin/* /usr/local/bin/
   ```

   ```powershell
   # Windows PowerShell
   Expand-Archive .\she.zip -DestinationPath $env:USERPROFILE\she
   $env:Path += ";$env:USERPROFILE\she\bin"
   ```

3. Verify the installation:

   ```bash
   shec --version
   # → shec version X.Y.Z
   ```

---

### Build from Source  

If you prefer to compile the toolchain yourself (or want the latest `main` branch), follow these steps:

```bash
# 1. Clone the repository
git clone https://github.com/yourorg/SHE.git
cd SHE

# 2. Install Rust (required for the bootstrap compiler)
#    Recommended via rustup:
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 3. Build the compiler and runtime
cargo build --release

# 4. Install the binaries (optional)
sudo cp target/release/shec /usr/local/bin/
sudo cp target/release/she  /usr/local/bin/
```

> **Why Rust?** The first‑stage compiler (`shec`) is written in Rust for safety and fast iteration. The final native code generator is written in SHE itself, compiled by the bootstrap compiler.

---

### Docker Image  

A ready‑to‑run Docker image is published on Docker Hub:

```bash
docker pull yourorg/she:latest
docker run --rm -it yourorg/she:latest she --repl
```

You can also mount a local project:

```bash
docker run --rm -it \
  -v "$(pwd)":/workspace \
  -w /workspace \
  yourorg/she:latest shec my_program.she -o my_program
```

---  

## Quick‑Start Usage  

### Running a SHE script  

```bash
# Compile
shec hello.she -o hello

# Execute the binary
./hello
```

Or use the **single‑command mode** (no explicit compilation step):

```bash
she run hello.she
```

### REPL (Read‑Eval‑Print Loop)  

```bash
she --repl
# or simply
she
```

The REPL supports:

* Multi‑line input with automatic indentation  
* History (`↑`/`↓`) and tab‑completion for identifiers  
* `:load <file>` – load a script into the current session  
* `:type <expr>` – query the inferred type of an expression  

### Compiler Options  

| Flag | Description |
|------|-------------|
| `-o <path>` | Output binary path (default: `a.out`) |
| `-O0 … -O3` | Optimization level (default: `-O2`) |
| `-g` | Emit debug symbols (useful with `gdb` or `lldb`) |
| `--target <triple>` | Cross‑compile target (e.g., `x86_64-pc-windows-gnu`) |
| `--emit <what>` | Emit intermediate artifacts (`llvm-ir`, `asm`, `obj`) |
| `--no-stdlib` | Build without linking the standard library (for bare‑metal) |
| `-D <feature>` | Enable a compile‑time feature flag (see `features.toml`) |

Run `shec --help` for the full list.

---  

## API Documentation  

> **NOTE:** The API docs are generated automatically with `cargo doc` and are also hosted at https://yourorg.github.io/SHE/docs.

### Core Packages  

| Package | Description | Primary Types |
|---------|-------------|---------------|
| `core` | Language runtime primitives (memory, panic, traits) | `Any`, `Result<T,E>`, `Option<T>` |
| `std` | Full‑featured standard library (I/O, collections, concurrency) | `File`, `Vec<T>`, `Thread`, `Channel<T>` |
| `net` | Networking abstractions (TCP, UDP, HTTP client) | `TcpListener`, `TcpStream`, `HttpClient` |
| `async` | Asynchronous runtime based on lightweight tasks | `Task`, `Future<T>` |
| `proc_macro` | Compile‑time code generation (macros) | `Macro`, `TokenStream` |

### Standard Library Highlights  

* **Collections** – `Array<T>`, `Map<K,V>`, `Set<T>` with ergonomic literals.  
* **Concurrency** – `spawn`, `join`, `Mutex<T>`, `RwLock<T>`, `Channel<T>`.  
* **File System** – `Path`, `File`, `read_to_string`, `write_all`.  
* **Error Handling** – `Result<T,E>` with `?` operator and custom error types.  
* **Formatting** – `println!`, `format!`, `debug!` macros.  

### Embedding SHE in Other Projects  

SHE can be embedded as a scripting engine via the **C API** (`libshe.so` / `she.dll`). The API is deliberately minimal:

```c
// Initialize the runtime (must be called once per process)
int she_init(void);

// Compile a source string to a module
she_module_t* she_compile(const char* src, const char* name);

// Execute a compiled module
int she_execute(she_module_t* mod);

// Register a native function (C ↔ SHE bridge)
int she_register_function(const char* name, void* fn_ptr, const char* signature);

// Shut down the runtime
void