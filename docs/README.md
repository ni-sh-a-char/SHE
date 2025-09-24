# SHE – A Programming Language  

**Repository:** `github.com/your-org/SHE`  
**Current Version:** `v2.3.1` (2025‑09‑24)  
**License:** MIT  

> **SHE** (pronounced “shē”) is a modern, statically‑typed, compiled programming language designed for simplicity, safety, and high‑performance systems programming. It ships with a fast native compiler, an interactive REPL, and a rich standard library.

---  

## Table of Contents  

1. [Installation](#installation)  
   - Binary releases  
   - Building from source  
   - Docker & VS Code extension  
2. [Quick‑Start Usage](#quick-start-usage)  
   - REPL  
   - Compiling & running programs  
   - Project layout & `shec` commands  
3. [API Documentation](#api-documentation)  
   - Language fundamentals  
   - Standard library overview  
   - Compiler & tooling API  
4. [Examples](#examples)  
   - Hello World  
   - Data structures & generics  
   - File I/O  
   - Concurrency (actors)  
   - Embedding SHE in a host application  
5. [Contributing & Development](#contributing)  
6. [License & Acknowledgements](#license)  

---  

## Installation  

### 1. Binary releases (recommended)

| OS / Architecture | Download | SHA‑256 |
|-------------------|----------|---------|
| Linux x86_64      | `she-v2.3.1-linux-x86_64.tar.gz` | `c1e2…` |
| macOS arm64       | `she-v2.3.1-macos-arm64.tar.gz` | `a9f3…` |
| Windows x86_64    | `she-v2.3.1-windows-x86_64.zip` | `d4b7…` |

```bash
# Example for Linux
curl -L -O https://github.com/your-org/SHE/releases/download/v2.3.1/she-v2.3.1-linux-x86_64.tar.gz
tar -xzf she-v2.3.1-linux-x86_64.tar.gz
sudo mv she /usr/local/bin/
```

The archive contains three executables:

| Executable | Purpose |
|------------|---------|
| `shec`     | The native compiler (`shec <source>.she -o <binary>`). |
| `she-repl` | Interactive REPL (`she-repl`). |
| `she-doc`  | Generates API docs from source (`she-doc ./src`). |

All binaries are **statically linked** and have **zero‑runtime dependencies**.

---

### 2. Building from source  

> **Prerequisites**  
> - **Rust** ≥ 1.73 (the compiler is written in Rust)  
> - **CMake** ≥ 3.20 (for the optional C‑interop layer)  
> - **Git**  

```bash
# Clone the repository
git clone https://github.com/your-org/SHE.git
cd SHE

# Build the compiler, REPL and docs generator
cargo build --release

# Install to $HOME/.local/bin (or any directory on $PATH)
cargo install --path . --root $HOME/.local
```

**Optional:** Build the C‑interop library (`libshe.so` / `she.dll`) for embedding:

```bash
cd interop/c
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make
```

---

### 3. Docker image  

```bash
docker pull your-org/she:2.3.1
docker run --rm -v "$(pwd)":/src -w /src your-org/she:2.3.1 shec main.she -o main
```

The image contains `shec`, `she-repl`, and the full standard library.

---

### 4. VS Code extension  

Install **SHE Language Support** from the VS Code Marketplace. It provides:

- Syntax highlighting & IntelliSense  
- On‑the‑fly compilation diagnostics  
- Debugger integration (via `sheldbg`)  

---  

## Quick‑Start Usage  

### REPL  

```bash
$ she-repl
>>> let x: i32 = 42;
>>> x * 2
84
>>> :exit
```

Special REPL commands:

| Command | Description |
|---------|-------------|
| `:help` | Show REPL help |
| `:load <file>` | Load a script into the session |
| `:type <expr>` | Show inferred type |
| `:exit` | Quit REPL |

---

### Compiling & Running a Program  

```bash
# 1. Write a source file (example: hello.she)
cat > hello.she <<'EOF'
pub fn main() -> i32 {
    println("Hello, SHE!");
    0
}
EOF

# 2. Compile
shec hello.she -o hello

# 3. Run
./hello
# → Hello, SHE!
```

**Common flags**

| Flag | Meaning |
|------|---------|
| `-O` | Optimize (default: `-O2`). |
| `-g` | Emit debug info for `sheldbg`. |
| `--target <triple>` | Cross‑compile (e.g., `x86_64-pc-windows-gnu`). |
| `--emit <asm|llvm|obj>` | Emit intermediate representation. |
| `--no-stdlib` | Build a freestanding binary. |

---

### Project Layout  

```
my_project/
├─ src/
│   ├─ main.she          # entry point (must contain `pub fn main()`)
│   └─ lib/
│       └─ utils.she
├─ tests/
│   └─ utils_test.she
├─ Cargo.she.toml        # SHE’s package manifest (similar to Cargo.toml)
└─ sheconfig.toml        # optional compiler configuration
```

**`Cargo.she.toml` example**

```toml
[package]
name = "my_project"
version = "0.1.0"
edition = "2025"

[dependencies]
std = "2.3"
serde = { version = "1.0", optional = true }

[features]
default = ["serde"]
```

Build the whole project:

```bash
shec build          # equivalent to `cargo build`
shec test           # runs all `*_test.she` files
shec run            # builds and executes `src/main.she`
```

---  

## API Documentation  

The API docs are generated with `she-doc` and published at https://your-org.github.io/SHE/. Below is a concise overview.

### 1. Language Fundamentals  

| Construct | Syntax | Description |
|-----------|--------|-------------|
| **Primitive Types** | `i8, i16, i32, i64, u8, u16, u32, u64, f32, f64, bool, char, str` | Fixed‑size integers, floating‑point, boolean, Unicode scalar, UTF‑8 string. |
| **Compound Types** | `Array<T, N>`, `Slice<T>`, `Tuple<T1, T2, …>`, `Struct`, `Enum` | Statically sized arrays, dynamically sized slices, tuples, user‑defined structs/enums. |
| **Generics** | `fn foo<T: Copy>(x: T) -> T { x }` | Parametric polymorphism with trait bounds. |
| **Traits** | `trait Display { fn fmt(&self) -> str; }` | Interface‑like abstraction; can be auto‑implemented via `impl`. |
| **Pattern Matching** | `match expr { pattern => expr, … }` | Exhaustive, compile‑time checked. |
| **Error Handling** | `Result<T, E>` and `?` operator | Propagate errors without exceptions. |
| **Concurrency** | `actor`, `async fn`, `await` | Lightweight actors + async/await built on a work‑stealing scheduler. |
| **Unsafe Block** | `unsafe { … }` | Allows raw pointer manipulation, FFI, and other low‑level ops. |

### 2. Standard Library Overview  

| Module | Highlights |
|--------|------------|
| `std::io` | `File`, `BufReader`, `BufWriter`, `stdin`, `stdout`. |
| `std::fs` | `read_to_string`, `write`, `metadata`, `create_dir_all`. |
| `std::collections` | `HashMap<K, V>`, `HashSet<T>`, `Vec<T>`, `Deque<T>`. |
| `std::fmt` | `println!`, `format!`, `Display`/`Debug` traits. |
| `std::net` |