# SHE – A Programming Language  

**Repository:** `github.com/your-org/SHE`  
**Current version:** `v2.4.1` (2025‑09)  
**License:** MIT  

> **SHE** (pronounced “shē”) is a modern, statically‑typed, compiled programming language designed for safety, performance, and expressiveness. It ships with a fast native compiler, an interactive REPL, a rich standard library, and seamless inter‑op with C, Rust, and WebAssembly.

---  

## Table of Contents  

1. [Installation](#installation)  
   - Binary releases  
   - Package managers  
   - Building from source  
   - Docker & VS Code extension  
2. [Quick‑Start Usage](#quick-start-usage)  
   - The REPL  
   - Compiling & running programs  
   - Project layout & `shec` commands  
3. [API Documentation](#api-documentation)  
   - Language fundamentals  
   - Standard library overview  
   - Compiler & tooling API  
   - FFI & inter‑op  
4. [Examples](#examples)  
   - Hello World  
   - Data structures & generics  
   - Concurrency with actors  
   - WebAssembly target  
   - Embedding SHE in another application  
5. [Contributing & Development](#contributing)  
6. [License & Acknowledgements](#license)  

---  

## Installation  

> **Tip:** All commands below assume a Unix‑like shell (`bash`, `zsh`, `fish`). Windows users can use PowerShell or the Windows Subsystem for Linux (WSL).

### 1. Binary releases (recommended)

Pre‑built binaries are published on the **Releases** page.

```bash
# Choose the appropriate archive for your OS/arch
VERSION=v2.4.1
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Example for Linux x86_64
curl -L "https://github.com/your-org/SHE/releases/download/${VERSION}/she-${VERSION}-${OS}-${ARCH}.tar.gz" \
  -o she.tar.gz
tar -xzf she.tar.gz -C /usr/local/bin she
chmod +x /usr/local/bin/she
```

The archive contains three executables:

| Executable | Purpose |
|------------|---------|
| `she`      | The REPL and script runner |
| `shec`     | The native compiler (`shec <source> -o <binary>`) |
| `shefmt`   | Code formatter (compatible with `gofmt` style) |

Verify the installation:

```bash
she --version
# SHE v2.4.1 (commit abcdef123)
```

### 2. Package managers  

| Platform | Command |
|----------|---------|
| **Homebrew (macOS / Linux)** | `brew install she-lang` |
| **Scoop (Windows)** | `scoop bucket add she https://github.com/your-org/scoop-she && scoop install she` |
| **Cargo (Rust)** | `cargo install shec` (installs the compiler only) |
| **NPM (Node.js)** | `npm i -g she-lang` (installs the REPL for scripting) |

> Packages are automatically updated when a new release is cut.

### 3. Building from source  

> **Prerequisites**  
> - `git`  
> - `rustc` ≥ 1.73 (the compiler is written in Rust)  
> - `cmake` (for native dependencies)  

```bash
# Clone the repo
git clone https://github.com/your-org/SHE.git
cd SHE

# Build everything (debug)
cargo build

# Build an optimized release binary
cargo build --release
# Binaries end up in ./target/release/
```

Optional features (enabled via Cargo features):

| Feature | Description |
|---------|-------------|
| `wasm`  | Build the WebAssembly backend (`shec --target wasm32-unknown-unknown`) |
| `llvm`  | Use LLVM as the code‑gen backend (experimental) |
| `serde` | Enable `serde`‑compatible serialization for the standard library |

### 4. Docker image  

```bash
docker pull ghcr.io/your-org/she:2.4.1
docker run --rm -v "$(pwd)":/src -w /src ghcr.io/your-org/she:2.4.1 shec main.she -o main
```

The image contains `she`, `shec`, and `shefmt`, plus the full standard library.

### 5. VS Code extension  

Install **SHE Language Support** from the Marketplace. It provides:

- Syntax highlighting & IntelliSense  
- On‑save formatting (`shefmt`)  
- Debugger integration (via `lldb`)  

---  

## Quick‑Start Usage  

### 1. The REPL  

```bash
$ she
SHE 2.4.1 (interactive)
>>> let x = 42
>>> x * 2
84
>>> :help
```

Built‑in commands (`:` prefix) include `:quit`, `:load <file>`, `:type <expr>`, and `:doc <symbol>`.

### 2. Compiling & running a program  

```she
// file: hello.she
fn main() -> i32 {
    println!("Hello, SHE!");
    0
}
```

```bash
shec hello.she -o hello   # compile to native binary
./hello                    # run
# → Hello, SHE!
```

#### Common compiler flags  

| Flag | Meaning |
|------|---------|
| `-O0` | No optimizations (fast compile) |
| `-O2` | Balanced optimizations (default) |
| `-O3` | Aggressive optimizations (may increase compile time) |
| `--target <triple>` | Cross‑compile (e.g. `wasm32-unknown-unknown`) |
| `--emit asm` | Emit assembly to stdout |
| `--debug` | Include debug symbols for `lldb`/`gdb` |

### 3. Project layout  

```
my_project/
├─ src/
│   ├─ main.she          # entry point
│   ├─ lib/
│   │   └─ utils.she
│   └─ tests/
│       └─ utils_test.she
├─ Cargo.toml            # optional – enables Cargo‑style dependency management
├─ she.toml              # SHE‑specific manifest (required for `shec build`)
└─ README.md
```

#### `she.toml` (minimal example)

```toml
[package]
name = "my_project"
version = "0.1.0"
edition = "2025"

[dependencies]
std = "2.4"
serde = { version = "1.0", optional = true }
```

Build the whole project:

```bash
shec build          # reads she.toml, compiles src/**/*.she
shec test           # runs all `*_test.she` files
```

---  

## API Documentation  

> The full API reference is generated automatically and hosted at  
> **https://your-org.github.io/SHE/docs**. Below is a concise overview.

### 1. Language fundamentals  

| Construct | Syntax | Description |
|-----------|--------|-------------|
| **Primitive types** | `i8, i16, i32, i64, u8, u16, u32, u64, f32, f64, bool, char, str` | Fixed‑size integers, floating point, boolean, Unicode scalar, UTF‑8 string |
| **Compound types** | `Array<T, N>`, `Slice<T>`, `Tuple<T...>`, `Struct`, `Enum` | Statically sized arrays, dynamically sized slices, tuples, user‑defined structs/enums |
| **Generics** | `fn foo<T>(x: T) -> T { x }` | Type parameters are inferred or explicitly bound (`where T: Copy`) |
| **Pattern matching** | `match expr { pattern => expr, ... }` | Exhaustive, supports destructuring, guards |
| **Error handling** | `Result<T, E>` and `?` operator | Propagate errors without exceptions |
| **Concurrency** | `actor`, `async fn`, `await` | Lightweight actors + async/await built on the same runtime |
| **Modules** | `mod foo { … }` | Namespaces; `pub` controls visibility |
| **Attributes** | `#[derive(Debug, Clone)]` | Meta‑programming, custom derives, compiler hints |

### 2. Standard library overview  

| Module | Highlights |
|--------|------------|
| `std::io` | `File`, `BufReader`, `BufWriter`, `stdin`, `stdout` |
