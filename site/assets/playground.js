/* The SHE playground.
 *
 * Runs the real interpreter in the browser: Pyodide provides CPython compiled
 * to WebAssembly, and the `she` package is fetched from this same site and
 * written into Pyodide's filesystem. No server, no backend, no install.
 *
 * Programs run inside SHE's own sandbox with no permissions and a step budget,
 * so a runaway loop in a stranger's snippet cannot lock the tab up for good.
 */

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";

const SAMPLES = {
  hello: `# Welcome to SHE. Press Run, or edit anything you like.

let name = "World"
say "Hello, {name}!"

# Text can hold values inside {braces}.
let numbers = [4, 8, 15, 16, 23, 42]
say "the list holds {numbers.length} numbers"
say "they add up to {numbers.sum()}"
`,

  pipeline: `# The pipeline operator reads left to right, like a sentence.

let numbers = [4, 8, 15, 16, 23, 42]

say numbers
  |> filter(fun(n) -> n % 2 is 0)
  |> map(fun(n) -> n / 2)
  |> sum()

# The same thing written inside out:
say sum(map(filter(numbers, fun(n) -> n % 2 is 0), fun(n) -> n / 2))

# Text works the same way.
say "the quick brown fox"
  |> text.split(" ")
  |> map(fun(w) -> w.capitalise())
  |> text.join(" ")
`,

  types: `# Your own types, with methods.

type Point has x, y
  fun length(self) -> math.sqrt(self.x ^ 2 + self.y ^ 2)
  fun plus(self, other) -> Point(self.x + other.x, self.y + other.y)
  fun to_text(self) -> "({self.x}, {self.y})"
end

let a = Point(3, 4)
let b = Point(1, 1)

say a
say a.length()
say a.plus(b)

# One type can build on another.
type Animal has name
  fun speak(self) -> "..."
  fun introduce(self) -> "{self.name} says {self.speak()}"
end

type Dog from Animal
  fun speak(self) -> "woof"
end

say Dog("Rex").introduce()
`,

  matching: `# Choose a branch by the shape of a value.

fun describe(value)
  return match value
    case 0 -> "nothing at all"
    case 1 | 2 | 3 -> "a small number"
    case number(n) if n < 0 -> "below zero"
    case 4..99 -> "a middling number"
    case [] -> "an empty list"
    case [only] -> "a list holding just {only}"
    case [first, ...rest] -> "a list starting with {first}, {rest.length} more"
    case {name: n} -> "something called {n}"
    case text(t) -> "some words: {t}"
    case _ -> "something else entirely"
  end
end

for each thing in [0, 2, -5, 50, [], [7], [1,2,3], {name: "Ada"}, "hi", true]
  say describe(thing)
end
`,

  errors: `# Errors point at the source and suggest a fix.
# Try breaking something and press Run.

fun withdraw(balance, amount)
  if amount <= 0 then throw "the amount has to be positive"
  if amount > balance then throw error("NotEnough", "you only have {balance}")
  return balance - amount
end

say withdraw(100, 30)

try
  say withdraw(100, 500)
catch e
  say "{e.kind}: {e.message}"
end

try
  say 1 / 0
catch e: MathError
  say "caught: {e.message}"
finally
  say "cleaned up either way"
end

# Now uncomment this line to see a helpful error:
# say totl
`,

  security: `# A SHE program starts with no power at all.
# In the playground nothing is granted, so every guarded step is refused.

import fs
import http

say "Working things out needs no permission:"
say "  {[1,2,3,4,5] |> filter(fun(n) -> n % 2 is 1) |> sum()}"
say ""

try
  say fs.read("/etc/passwd")
catch e
  say "Reading a file: {e.message}"
  say "  {e.hint}"
end

say ""

try
  say http.get("https://example.com").status
catch e
  say "Reaching the network: {e.message}"
  say "  {e.hint}"
end
`,

  crypto: `# Hashing, passwords and Kaalka time-keyed encryption.

import crypto

say "sha256      {crypto.hash("she")[0:32]}..."
say "hmac        {crypto.hmac("payload", "key")[0:32]}..."
say "token       {crypto.token(20)}"
say ""

let stored = crypto.password_hash("correct horse battery staple", 50000)
say "right password  {crypto.password_check("correct horse battery staple", stored)}"
say "wrong password  {crypto.password_check("hunter2", stored)}"
say ""

# Kaalka keys its cipher on a moment in time.
let moment = "14:35:22"
let sealed = crypto.seal("meet at the bridge", moment)
say "sealed      {sealed}"
say "opened      {crypto.open(sealed, moment)}"
say ""

let packet = crypto.envelope("the eagle has landed", "ada", "bob", moment)
say "bob reads   {crypto.open_envelope(packet, "bob")}"
try
  say crypto.open_envelope(packet, "eve")
catch e
  say "eve cannot  {e.message}"
end
`,

  tests: `# Tests live next to the code they check.
# In the playground they run as soon as you press Run.

fun celsius_to_fahrenheit(c) -> c * 9 / 5 + 32

fun initials(name)
  return name.trim().split(" ")
    |> filter(fun(part) -> not part.empty?())
    |> map(fun(part) -> part.at(0).upper())
    |> text.join(".")
end

test "converts freezing and boiling"
  expect celsius_to_fahrenheit(0) is 32
  expect celsius_to_fahrenheit(100) is 212
end

test "handles negative temperatures"
  expect celsius_to_fahrenheit(-40) is -40
end

test "builds initials from a name"
  expect initials("Ada Lovelace") is "A.L"
  expect initials("  grace  brewster  hopper ") is "G.B.H"
end

say "Press Run — the results appear on the right."
`,
};

const BOOT = `
import sys, io, json, traceback
sys.setrecursionlimit(3000)
sys.path.insert(0, "/she-src")

from she.interp import Interpreter
from she.sandbox import Sandbox
from she.errors import SheError

def she_run(source, allow_all=False):
    out = io.StringIO()
    box = Sandbox.trusted(name="this snippet") if allow_all else Sandbox.locked(name="this snippet")
    box.max_steps = 4_000_000
    box.max_depth = 120
    interp = Interpreter(sandbox=box, out=out, file="playground.she",
                         ask=lambda prompt: "")
    failures = []
    try:
        interp.run(source, "playground.she")
        for node, env in interp.tests:
            try:
                interp.exec_block(node.body, env)
                out.write("  ok    " + node.name + "\\n")
            except SheError as exc:
                failures.append(node.name)
                out.write("  fail  " + node.name + "\\n        " + exc.message + "\\n")
        if interp.tests:
            passed = len(interp.tests) - len(failures)
            out.write("\\n" + str(passed) + " passed, " + str(len(failures)) + " failed\\n")
        return json.dumps({"output": out.getvalue(), "error": None})
    except SheError as exc:
        return json.dumps({"output": out.getvalue(), "error": exc.render(color=False)})
    except SystemExit:
        return json.dumps({"output": out.getvalue(), "error": None})
    except RecursionError:
        return json.dumps({"output": out.getvalue(),
                           "error": "LimitError: that nested too deeply and was stopped"})
    except Exception:
        return json.dumps({"output": out.getvalue(), "error": traceback.format_exc()})
    finally:
        interp.shutdown()
`;

let pyodide = null;
let booting = null;

async function boot(onStatus) {
  if (pyodide) return pyodide;
  if (booting) return booting;

  booting = (async () => {
    onStatus("loading python…");
    await loadScript(PYODIDE);
    const py = await loadPyodide({ indexURL: PYODIDE.replace("/pyodide.js", "/") });

    onStatus("loading she…");
    const base = new URL("./she-src/", document.baseURI);
    const manifest = await fetch(new URL("manifest.json", base)).then((r) => {
      if (!r.ok) throw new Error("the interpreter source is not published yet");
      return r.json();
    });

    py.FS.mkdirTree("/she-src/she/stdlib");
    await Promise.all(
      manifest.files.map(async (name) => {
        const text = await fetch(new URL(name, base)).then((r) => r.text());
        py.FS.writeFile("/she-src/" + name, text);
      })
    );

    onStatus("starting…");
    await py.runPythonAsync(BOOT);
    pyodide = py;
    onStatus("ready");
    return py;
  })();

  return booting;
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const tag = document.createElement("script");
    tag.src = src;
    tag.onload = resolve;
    tag.onerror = () => reject(new Error("could not load " + src));
    document.head.appendChild(tag);
  });
}

export function createPlayground(root) {
  const editor = root.querySelector("[data-editor]");
  const console_ = root.querySelector("[data-console]");
  const runBtn = root.querySelector("[data-run]");
  const picker = root.querySelector("[data-sample]");
  const status = root.querySelector("[data-status]");
  const shareBtn = root.querySelector("[data-share]");
  const resetBtn = root.querySelector("[data-reset]");
  const allowBox = root.querySelector("[data-allow]");

  const setStatus = (text) => { if (status) status.textContent = text; };

  const write = (text, kind) => {
    const line = document.createElement("span");
    line.className = kind || "out";
    line.textContent = text;
    console_.appendChild(line);
    console_.scrollTop = console_.scrollHeight;
  };

  const clear = () => { console_.textContent = ""; };

  // A shared link carries the program in the URL fragment, so nothing is
  // stored anywhere and the link works offline once the page has loaded.
  const fromUrl = () => {
    const hash = location.hash.replace(/^#code=/, "");
    if (!hash || !location.hash.startsWith("#code=")) return null;
    try {
      return decodeURIComponent(escape(atob(decodeURIComponent(hash))));
    } catch (_) {
      return null;
    }
  };

  const restore = () => {
    const shared = fromUrl();
    if (shared) return shared;
    try {
      return localStorage.getItem("she:playground") || SAMPLES.hello;
    } catch (_) {
      return SAMPLES.hello;
    }
  };

  editor.value = restore();

  const remember = () => {
    try { localStorage.setItem("she:playground", editor.value); } catch (_) {}
  };

  if (picker) {
    picker.innerHTML = "";
    const labels = {
      hello: "Hello, World", pipeline: "Pipelines", types: "Types",
      matching: "Pattern matching", errors: "Errors", security: "Permissions",
      crypto: "Crypto & Kaalka", tests: "Tests",
    };
    for (const key of Object.keys(SAMPLES)) {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = labels[key] || key;
      picker.appendChild(option);
    }
    picker.addEventListener("change", () => {
      editor.value = SAMPLES[picker.value];
      remember();
      clear();
      write("loaded the " + picker.options[picker.selectedIndex].text + " example — press Run.\n", "note");
    });
  }

  editor.addEventListener("input", remember);

  // Tab indents rather than leaving the editor.
  editor.addEventListener("keydown", (event) => {
    if (event.key === "Tab") {
      event.preventDefault();
      const { selectionStart: a, selectionEnd: b, value } = editor;
      editor.value = value.slice(0, a) + "  " + value.slice(b);
      editor.selectionStart = editor.selectionEnd = a + 2;
      remember();
    }
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      run();
    }
  });

  async function run() {
    runBtn.disabled = true;
    clear();
    write("running…\n", "note");
    try {
      const py = await boot(setStatus);
      const source = editor.value;
      const allowAll = allowBox ? allowBox.checked : false;
      const raw = py.globals.get("she_run")(source, allowAll);
      const result = JSON.parse(raw);
      clear();
      if (result.output) write(result.output, "out");
      if (result.error) write((result.output ? "\n" : "") + result.error, "err");
      if (!result.output && !result.error) write("(the program printed nothing)", "note");
      setStatus("ready");
    } catch (error) {
      clear();
      write("The playground could not start.\n\n" + error.message +
            "\n\nYou can still install SHE locally:  pip install she-lang", "err");
      setStatus("unavailable");
    } finally {
      runBtn.disabled = false;
    }
  }

  runBtn.addEventListener("click", run);

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      editor.value = SAMPLES[picker ? picker.value : "hello"] || SAMPLES.hello;
      remember();
      clear();
    });
  }

  if (shareBtn) {
    shareBtn.addEventListener("click", async () => {
      const encoded = btoa(unescape(encodeURIComponent(editor.value)));
      const url = location.origin + location.pathname + "#code=" + encodeURIComponent(encoded);
      try {
        await navigator.clipboard.writeText(url);
        shareBtn.textContent = "link copied";
      } catch (_) {
        location.hash = "code=" + encodeURIComponent(encoded);
        shareBtn.textContent = "link in address bar";
      }
      setTimeout(() => { shareBtn.textContent = "share"; }, 1800);
    });
  }

  // Only start downloading Pyodide once the playground is actually on screen.
  const observer = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) {
      observer.disconnect();
      boot(setStatus).catch(() => setStatus("unavailable"));
    }
  }, { rootMargin: "300px" });
  observer.observe(root);

  return { run };
}
