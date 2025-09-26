# SHE – “A Programming Language”

> **SHE** (Simple, Human‑oriented, Extensible) is a modern, statically‑typed, multi‑paradigm programming language designed for readability, safety, and rapid prototyping. It ships with a powerful standard library, a fast native compiler, and an interactive REPL.

---

## Table of Contents
1. [Installation](#installation)  
2. [Quick‑Start / Usage](#usage)  
3. [API Documentation](#api-documentation)  
4. [Examples](#examples)  
5. [Contributing & Development](#contributing)  
6. [License](#license)  

---  

## Installation <a name="installation"></a>

### Prerequisites
| Tool | Minimum Version | Why |
|------|----------------|-----|
| **Git** | 2.30+ | To clone the repository |
| **CMake** | 3.18+ | Build system |
| **LLVM/Clang** | 15.0+ | Backend for native code generation |
| **Python** | 3.9+ (optional) | For the REPL and tooling scripts |
| **Node.js** | 18+ (optional) | For the optional web‑assembly target |

> **Note:** SHE can also be installed via pre‑built binaries (see the *Releases* page) if you don’t want to compile from source.

### 1. Clone the repository

```bash
git clone https://github.com/your-org/SHE.git
cd SHE
```

### 2. Build from source (Linux/macOS/WSL)

```bash
# Create a build directory
mkdir build && cd build

# Configure the project
cmake .. -DCMAKE_BUILD_TYPE=Release

# Compile (uses all available cores)
cmake --build . -- -j$(nproc)

# Install system‑wide (optional, may require sudo)
sudo cmake --install .
```

### 3. Build from source (Windows)

```powershell
# From PowerShell
mkdir build
cd build
cmake .. -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
# Optional: install
cmake --install . --config Release
```

### 4. Using pre‑built binaries

1. Go to the **Releases** page: <https://github.com/your-org/SHE/releases>
2. Download the archive matching your OS (`she-linux-x86_64.tar.gz`, `she-windows-x86_64.zip`, etc.).
3. Extract and add the `bin/` directory to your `PATH`.

```bash
# Example (Linux)
tar -xzf she-linux-x86_64.tar.gz
sudo mv she/bin/* /usr/local/bin/
```

### 5. Verify the installation

```bash
she --version
# Expected output, e.g.:
# SHE version 0.9.3 (commit abcdef1, built 2025-09-26)
```

---

## Usage <a name="usage"></a>

SHE can be used in three primary ways:

| Mode | Command | Description |
|------|---------|-------------|
| **REPL** | `she repl` | Interactive prompt for quick experiments. |
| **Script** | `she run <file.she>` | Execute a SHE source file without compilation. |
| **Compile** | `she build <file.she> -o <output>` | Produce a native executable (or WASM). |

### 1. REPL

```bash
$ she repl
SHE 0.9.3 (interactive)
>>> let x = 42
>>> x * 2
84
>>> :help
# ... list of REPL commands ...
>>> :exit
```

### 2. Running a script

```bash
# hello.she
print("Hello, SHE!")

# Execute
she run hello.she
# → Hello, SHE!
```

### 3. Compiling to a native binary

```bash
she build hello.she -o hello
./hello
# → Hello, SHE!
```

#### Common build flags

| Flag | Description |
|------|-------------|
| `-O0`, `-O1`, `-O2`, `-O3` | Optimization level (default: `-O2`). |
| `--target wasm32` | Emit WebAssembly module (`.wasm`). |
| `--no-stdlib` | Build without linking the standard library (advanced). |
| `-D<NAME>=<VALUE>` | Define a compile‑time constant (e.g., `-DDEBUG=1`). |
| `--emit-llvm` | Output LLVM IR (`.ll`) instead of native code. |

### 4. Project layout (recommended)

```
my_project/
├─ src/
│   ├─ main.she          # entry point
│   └─ utils.she
├─ tests/
│   └─ utils_test.she
├─ she.toml              # project manifest (see below)
└─ README.md
```

#### `she.toml` – Minimal manifest

```toml
[package]
name = "my_project"
version = "0.1.0"
edition = "2025"

[dependencies]
# Example: "json" = "0.3.2"
```

You can then build the whole project with:

```bash
she build src/main.she -p my_project -o my_project
```

---

## API Documentation <a name="api-documentation"></a>

> **All API docs are generated automatically** with `she doc`. The latest HTML docs are hosted at <https://your-org.github.io/SHE/docs>.

Below is a concise overview of the core language constructs and the most used standard‑library modules.

### 1. Language Core

| Construct | Syntax | Description |
|-----------|--------|-------------|
| **Variables** | `let name: Type = expr;` | Immutable by default. Use `var` for mutable bindings. |
| **Functions** | `fn name(arg: Type) -> ReturnType { … }` | First‑class, can be generic. |
| **Algebraic Data Types** | `enum Option<T> { Some(T), None }` | Sum types with pattern matching. |
| **Pattern Matching** | `match expr { pattern => expr, … }` | Exhaustive matching on enums, tuples, structs. |
| **Traits (Interfaces)** | `trait Drawable { fn draw(&self); }` | Define behavior that types can implement. |
| **Generics** | `fn map<T, U>(list: List<T>, f: fn(T) -> U) -> List<U>` | Parametric polymorphism. |
| **Modules** | `mod math { … }` | Namespaces; can be split across files (`mod foo;`). |
| **Error handling** | `Result<T, E>` | Use `?` operator to propagate errors. |
| **Concurrency** | `async fn`, `await`, `spawn` | Built‑in async/await and lightweight tasks. |

### 2. Standard Library Highlights

| Module | Primary Types / Functions | Example |
|--------|---------------------------|---------|
| `std::io` | `File`, `stdin`, `stdout`, `read_line` | `let line = std::io::read_line()?;` |
| `std::fs` | `read_to_string`, `write`, `metadata` | `std::fs::write("out.txt", data)?;` |
| `std::net` | `TcpListener`, `TcpStream`, `HttpClient` | `let srv = std::net::TcpListener::bind("0.0.0.0:8080")?;` |
| `std::collections` | `Vec<T>`, `HashMap<K,V>`, `HashSet<T>` | `let mut map = std::collections::HashMap::new();` |
| `std::fmt` | `format!`, `println!` | `println!("Value = {}", x);` |
| `std::time` | `Instant`, `Duration`, `sleep` | `std::time::sleep(Duration::seconds(1));` |
| `std::async` | `spawn`, `await`, `Task<T>` | `let handle = std::async::spawn(async { … });` |
| `std::json` | `parse`, `to_string` | `let obj = std::json::parse("{\"a\":1}")?;` |
| `std::crypto` | `sha256`, `hmac`, `rand_bytes` | `let digest = std::crypto::sha256(data);` |

### 3. Generating API Docs

```bash
# Generate HTML docs in ./target/doc
she doc

# Serve locally (auto‑reload on changes)
she doc --serve
```

The