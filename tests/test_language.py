"""The language test suite. Every feature SHE claims to have gets checked here."""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from she import run  # noqa: E402
from she.errors import SheError  # noqa: E402
from she.sandbox import Sandbox  # noqa: E402


def go(source, sandbox=None, answers=None):
    """Run SHE source and return everything it printed."""
    out = io.StringIO()
    replies = list(answers or [])
    result, error = run(source, "<test>", sandbox=sandbox or Sandbox.trusted(),
                        out=out, ask=lambda prompt: replies.pop(0) if replies else "")
    if error:
        raise error
    return out.getvalue()


def fails(source, sandbox=None):
    """Run source expecting a SHE error, and hand the error back."""
    with pytest.raises(SheError) as caught:
        go(source, sandbox)
    return caught.value


# --- the basics -------------------------------------------------------------

def test_hello_world():
    assert go('say "Hello, World!"') == "Hello, World!\n"


def test_interpolation():
    assert go('let n = "SHE"\nsay "hi {n}, {1 + 1} times"') == "hi SHE, 2 times\n"


def test_escaped_braces():
    assert go('say "a {{literal}} brace"') == "a {literal} brace\n"


def test_arithmetic():
    assert go("say 2 + 3 * 4").strip() == "14"
    assert go("say (2 + 3) * 4").strip() == "20"
    assert go("say 2 ^ 10").strip() == "1024"
    assert go("say 7 // 2").strip() == "3"
    assert go("say 7 % 2").strip() == "1"
    assert go("say 10 / 4").strip() == "2.5"


def test_whole_division_stays_whole():
    """10 / 2 should print 5, not 5.0 — beginners should never see a stray .0."""
    assert go("say 10 / 2").strip() == "5"


def test_number_formats():
    assert go("say 1_000_000").strip() == "1000000"
    assert go("say 0xff").strip() == "255"
    assert go("say 0b1010").strip() == "10"
    assert go("say 1.5e3").strip() == "1500"


def test_comparison_and_logic():
    assert go("say 5 is 5").strip() == "true"
    assert go("say 5 is not 4").strip() == "true"
    assert go('say "a" is "a"').strip() == "true"
    assert go("say 1 < 2 and 3 > 2").strip() == "true"
    assert go("say not false").strip() == "true"
    assert go("say 3 in [1, 2, 3]").strip() == "true"


def test_let_is_immutable():
    error = fails("let x = 1\nx = 2")
    assert "cannot be changed" in error.message
    assert "var x" in (error.hint or "")


def test_var_is_mutable():
    assert go("var x = 1\nx = 2\nsay x").strip() == "2"


def test_compound_assignment():
    assert go("var x = 10\nx += 5\nx *= 2\nsay x").strip() == "30"


# --- control flow -----------------------------------------------------------

def test_if_else_chain():
    source = """
let n = 5
if n > 10
  say "big"
else if n is 5
  say "five"
else
  say "small"
end
"""
    assert go(source).strip() == "five"


def test_inline_if():
    assert go('if true then say "yes"').strip() == "yes"


def test_if_as_a_value():
    assert go('say if 1 > 2 then "a" else "b"').strip() == "b"


def test_while_loop():
    assert go("var i = 0\nwhile i < 3\n  i += 1\nend\nsay i").strip() == "3"


def test_repeat_until_always_runs_once():
    assert go("var i = 10\nrepeat\n  i += 1\nuntil i > 0\nsay i").strip() == "11"


def test_for_each_over_list():
    assert go('for each x in [1, 2, 3]\n  say x\nend') == "1\n2\n3\n"


def test_for_each_over_range():
    assert go("var t = 0\nfor each n in 1..5\n  t += n\nend\nsay t").strip() == "15"


def test_range_with_step():
    assert go("for each n in 0..10 by 5\n  say n\nend") == "0\n5\n10\n"


def test_exclusive_range():
    assert go("say to_list(1..<4)").strip() == "[1, 2, 3]"


def test_for_each_index_and_value():
    assert go('for each i, v in ["a", "b"]\n  say "{i}={v}"\nend') == "0=a\n1=b\n"


def test_for_each_over_map():
    assert go('for each k, v in {a: 1, b: 2}\n  say "{k}:{v}"\nend') == "a:1\nb:2\n"


def test_break_and_skip():
    source = """
for each n in 1..10
  if n is 3 then skip
  if n > 4 then break
  say n
end
"""
    assert go(source) == "1\n2\n4\n"


# --- functions --------------------------------------------------------------

def test_function_and_default():
    assert go('fun greet(who = "you") -> "hi {who}"\nsay greet()\nsay greet("SHE")') \
        == "hi you\nhi SHE\n"


def test_block_function_with_return():
    source = """
fun classify(n)
  if n < 0 then return "negative"
  if n is 0 then return "zero"
  return "positive"
end
say classify(-1), classify(0), classify(7)
"""
    assert go(source).strip() == "negative zero positive"


def test_closures_capture():
    source = """
fun counter()
  var n = 0
  return fun() -> n
end
let c = counter()
say c()
"""
    assert go(source).strip() == "0"


def test_recursion():
    assert go("fun f(n) -> if n < 2 then n else f(n-1) + f(n-2)\nsay f(20)").strip() \
        == "6765"


def test_runaway_recursion_is_caught():
    error = fails("fun loop(n) -> loop(n + 1)\nsay loop(1)")
    assert "without stopping" in error.message


def test_named_arguments():
    assert go('fun at(x, y) -> "{x},{y}"\nsay at(y: 2, x: 1)').strip() == "1,2"


def test_rest_parameters():
    assert go("fun total(...nums) -> sum(nums)\nsay total(1, 2, 3)").strip() == "6"


def test_spread_into_call():
    assert go("fun add(a, b) -> a + b\nlet xs = [1, 2]\nsay add(...xs)").strip() == "3"


def test_missing_argument_is_explained():
    error = fails("fun greet(who) -> who\nsay greet()")
    assert "needs `who`" in error.message
    assert "greet(who)" in (error.hint or "")


def test_lambda():
    assert go("let double = fun(n) -> n * 2\nsay double(21)").strip() == "42"


def test_pipeline_operator():
    assert go("say [3, 1, 2] |> sorted() |> reversed()").strip() == "[3, 2, 1]"


def test_pipeline_with_extra_arguments():
    assert go('say "a,b" |> text.split(",") |> text.join("-")').strip() == "a-b"


# --- data -------------------------------------------------------------------

def test_lists():
    assert go("let xs = [1, 2, 3]\nsay xs[0], xs[-1], xs.length").strip() == "1 3 3"


def test_list_slicing():
    assert go("say [1,2,3,4,5][1:3]").strip() == "[2, 3]"


def test_list_is_not_aliased_by_addition():
    """v1's bug: `a + 4` quietly mutated `a`. It must not."""
    assert go("let a = [1, 2]\nlet b = a + [3]\nsay a\nsay b") == "[1, 2]\n[1, 2, 3]\n"


def test_maps():
    source = 'let m = {name: "Ada", age: 36}\nsay m.name, m["age"], m.keys()'
    assert go(source).strip() == 'Ada 36 ["name", "age"]'


def test_map_spread():
    assert go('let a = {x: 1}\nsay {...a, y: 2}').strip() == '{"x": 1, "y": 2}'


def test_destructuring():
    assert go("let [a, b] = [1, 2]\nsay a + b").strip() == "3"


def test_destructuring_with_rest():
    assert go("let [head, ...tail] = [1, 2, 3]\nsay head, tail").strip() == "1 [2, 3]"


def test_text_methods_and_module_agree():
    assert go('say "hi".upper()').strip() == "HI"
    assert go('say text.upper("hi")').strip() == "HI"


def test_missing_key_suggests():
    error = fails('let m = {name: "x"}\nsay m["nme"]')
    assert "no key" in error.message
    assert "name" in (error.hint or "")


def test_index_out_of_range_is_clear():
    error = fails("let xs = [1, 2]\nsay xs[5]")
    assert "outside" in error.message
    assert "0 to 1" in (error.hint or "")


# --- types ------------------------------------------------------------------

def test_type_with_methods():
    source = """
type Point has x, y
  fun length(self) -> math.sqrt(self.x ^ 2 + self.y ^ 2)
end
let p = Point(3, 4)
say p.x, p.length()
"""
    assert go(source).strip() == "3 5"


def test_type_to_text_hook():
    source = """
type Money has amount
  fun to_text(self) -> "${self.amount}"
end
say Money(5)
"""
    assert go(source).strip() == "$5"


def test_type_inheritance():
    source = """
type Shape has name
  fun describe(self) -> "a {self.name}"
end
type Circle has radius from Shape
let c = Circle("circle", 2)
say c.describe()
"""
    assert go(source).strip() == "a circle"


def test_type_setup_hook():
    source = """
type Counter has start
  fun setup(self)
    self.total = self.start * 2
  end
end
say Counter(5).total
"""
    assert go(source).strip() == "10"


def test_missing_field_is_explained():
    error = fails("type P has x, y\nlet p = P(1)")
    assert "needs `y`" in error.message


# --- pattern matching -------------------------------------------------------

def test_match_literals_and_wildcard():
    source = """
fun name(n)
  return match n
    case 0 -> "zero"
    case 1 | 2 -> "small"
    case _ -> "many"
  end
end
say name(0), name(2), name(9)
"""
    assert go(source).strip() == "zero small many"


def test_match_with_guard():
    source = """
say match 15
  case n if n > 10 -> "big"
  case _ -> "small"
end
"""
    assert go(source).strip() == "big"


def test_match_destructures_lists():
    source = """
say match [1, 2, 3]
  case [a] -> "one"
  case [a, ...rest] -> "{a} then {rest}"
end
"""
    assert go(source).strip() == "1 then [2, 3]"


def test_match_on_type():
    source = """
type Point has x, y
say match Point(0, 0)
  case Point(0, 0) -> "origin"
  case Point(x, y) -> "at {x},{y}"
end
"""
    assert go(source).strip() == "origin"


def test_match_on_map_shape():
    source = """
say match {kind: "cat", name: "Mo"}
  case {kind: "dog"} -> "woof"
  case {kind: "cat", name: n} -> "meow {n}"
end
"""
    assert go(source).strip() == "meow Mo"


def test_match_range_pattern():
    assert go('say match 5\n  case 1..3 -> "low"\n  case 4..9 -> "mid"\nend').strip() \
        == "mid"


def test_unmatched_value_is_explained():
    error = fails('say match 9\n  case 1 -> "one"\nend')
    assert "case _" in (error.hint or "")


# --- errors -----------------------------------------------------------------

def test_try_catch_finally():
    source = """
try
  throw "broken"
catch e
  say "caught {e.message}"
finally
  say "cleanup"
end
"""
    assert go(source) == "caught broken\ncleanup\n"


def test_catch_by_kind():
    source = """
try
  say 1 / 0
catch e: MathError
  say "math: {e.message}"
end
"""
    assert "divide by zero" in go(source)


def test_uncaught_kind_propagates():
    source = """
try
  throw error("Timeout", "too slow")
catch e: MathError
  say "wrong handler"
end
"""
    error = fails(source)
    assert error.message == "too slow"


def test_error_values_carry_kind():
    source = """
try
  throw error("Timeout", "too slow")
catch e
  say e.kind, e.message
end
"""
    assert go(source).strip() == "Timeout too slow"


def test_divide_by_zero():
    error = fails("say 1 / 0")
    assert error.kind == "MathError"
    assert "divide by zero" in error.message


def test_undefined_name_suggests():
    error = fails("let total = 1\nsay totl")
    assert "not been defined" in error.message
    assert "total" in (error.hint or "")


def test_type_mismatch_is_readable():
    error = fails('say 1 + "two"')
    assert "cannot add" in error.message


def test_errors_point_at_the_source():
    error = fails('let a = 1\nsay a + "x"')
    assert error.pos.line == 1
    rendered = error.render(color=False)
    assert "^" in rendered and "<test>:2" in rendered


# --- gradual types ----------------------------------------------------------

def test_declared_type_is_checked():
    error = fails('let n: number = "text"')
    assert "should be a number" in error.message


def test_parameter_type_is_checked():
    error = fails("fun double(n: number) -> n * 2\nsay double(\"x\")")
    assert "expects `n` to be a number" in error.message


def test_return_type_is_checked():
    error = fails('fun bad(): number -> "text"\nsay bad()')
    assert "should return a number" in error.message


def test_union_types():
    assert go('fun show_it(v: number|text) -> "{v}"\nsay show_it(1), show_it("a")') \
        .strip() == "1 a"


# --- the sandbox ------------------------------------------------------------

def test_files_are_denied_by_default():
    error = fails('import fs\nsay fs.read("anything.txt")', Sandbox.locked())
    assert error.kind == "PermissionError"
    assert "--allow-read" in (error.hint or "")


def test_network_is_denied_by_default():
    error = fails('import http\nsay http.get("https://example.com")', Sandbox.locked())
    assert error.kind == "PermissionError"
    assert "--allow-net" in (error.hint or "")


def test_processes_are_denied_by_default():
    error = fails('import os\nsay os.run("echo")', Sandbox.locked())
    assert error.kind == "PermissionError"


def test_environment_is_denied_by_default():
    error = fails('import os\nsay os.env("PATH")', Sandbox.locked())
    assert error.kind == "PermissionError"


def test_granting_read_scoped_to_a_folder(tmp_path):
    from she.sandbox import Grant
    allowed = tmp_path / "ok.txt"
    allowed.write_text("fine", encoding="utf-8")
    other = tmp_path.parent / "elsewhere.txt"
    other.write_text("secret", encoding="utf-8")

    box = Sandbox([Grant("read", [str(tmp_path)])])
    assert "fine" in go(f'import fs\nsay fs.read({str(allowed)!r})', box)

    error = fails(f'import fs\nsay fs.read({str(other)!r})', box)
    assert error.kind == "PermissionError"


def test_step_budget_stops_runaway_loops():
    box = Sandbox.trusted(max_steps=50_000)
    error = fails("var i = 0\nwhile true\n  i += 1\nend", box)
    assert error.kind == "LimitError"


def test_pure_code_needs_no_permissions():
    """The whole point: computation is free, reaching outside is not."""
    assert go("say [1,2,3] |> sum()", Sandbox.locked()).strip() == "6"


# --- standard library -------------------------------------------------------

def test_text_module():
    assert go('say "  hi  ".trim()').strip() == "hi"
    assert go('say "a-b-c".split("-")').strip() == '["a", "b", "c"]'
    assert go('say "Hello World".slug()').strip() == "hello-world"
    assert go('say "abc".reverse()').strip() == "cba"
    assert go('say "hi".repeat(3)').strip() == "hihihi"


def test_list_module():
    assert go("say [3,1,2].sort()").strip() == "[1, 2, 3]"
    assert go("say [1,1,2].unique()").strip() == "[1, 2]"
    assert go("say [[1,2],[3]].flatten()").strip() == "[1, 2, 3]"
    assert go("say [1,2,3,4].chunk(2)").strip() == "[[1, 2], [3, 4]]"
    assert go("say [1,2,3].average()").strip() == "2"


def test_list_sort_by():
    source = 'say [{n: 2}, {n: 1}] |> list.sort(by: fun(m) -> m.n) |> to_text()'
    assert "1" in go(source)


def test_maps_module():
    """The dictionary module is `maps`, so it can never shadow `map` the function."""
    assert go('import maps\nsay maps.get({a: 1}, "b", 0)').strip() == "0"
    assert go('import maps\nsay maps.merge({a: 1}, {b: 2})').strip() == '{"a": 1, "b": 2}'
    assert go('import maps\nsay maps.invert({a: 1})').strip() == '{1: "a"}'


def test_map_function_is_never_shadowed():
    source = 'import maps\nsay [1, 2] |> map(fun(n) -> n * 3)'
    assert go(source).strip() == "[3, 6]"


def test_maps_read_better_as_methods():
    """`map` the function is global, so dictionaries use method syntax."""
    assert go('say {a: 1}.get("b", 0)').strip() == "0"
    assert go('say {a: 1}.merge({b: 2})').strip() == '{"a": 1, "b": 2}'
    assert go('say {a: 1, b: 2}.keys()').strip() == '["a", "b"]'


def test_math_module():
    assert go("say math.sqrt(16)").strip() == "4"
    assert go("say math.round(3.14159, 2)").strip() == "3.14"
    assert go("say math.clamp(15, 0, 10)").strip() == "10"
    assert go("say math.prime?(17)").strip() == "true"
    assert go("say math.median([1, 3, 2])").strip() == "2"


def test_math_errors_are_friendly():
    error = fails("say math.sqrt(-1)")
    assert "no real square root" in error.message


def test_json_module():
    assert go(r'''say json.parse('{"a": 1}').a''').strip() == "1"
    assert go('say json.stringify({a: 1})').strip() == '{"a":1}'


def test_json_rejects_bad_input():
    error = fails(r'''say json.parse('{oops')''')
    assert "not valid JSON" in error.message


def test_re_module():
    assert go('say re.find_all("a1b2", "[0-9]")').strip() == '["1", "2"]'
    assert go('say re.replace("a-b", "-", "+")').strip() == "a+b"
    assert go('say re.matches?("hello", "^h")').strip() == "true"


def test_random_is_repeatable_with_a_seed():
    source = "random.seed(7)\nlet a = random.whole(1, 100)\nrandom.seed(7)\nsay a is random.whole(1, 100)"
    assert go(source).strip() == "true"


def test_csv_module():
    source = 'import csv\nsay csv.parse("a,b\\n1,2")'
    assert go(source).strip() == '[{"a": "1", "b": "2"}]'


def test_higher_order_helpers():
    assert go("say [1,2,3,4] |> filter(fun(n) -> n % 2 is 0)").strip() == "[2, 4]"
    assert go("say [1,2,3] |> map(fun(n) -> n * 10)").strip() == "[10, 20, 30]"
    assert go("say reduce([1,2,3], fun(a, b) -> a + b)").strip() == "6"
    assert go("say [1,2,3] |> any(fun(n) -> n > 2)").strip() == "true"


# --- crypto and the two integrated libraries -------------------------------

def test_hashing_and_hmac():
    assert len(go("import crypto\nsay crypto.hash(\"x\")").strip()) == 64
    assert go('import crypto\nsay crypto.compare("a", "a")').strip() == "true"


def test_password_round_trip():
    source = """
import crypto
let stored = crypto.password_hash("hunter2", 50000)
say crypto.password_check("hunter2", stored)
say crypto.password_check("wrong", stored)
"""
    assert go(source).strip() == "true\nfalse"


def test_password_hash_rejects_weak_settings():
    error = fails('import crypto\nsay crypto.password_hash("x", 10)')
    assert "at least 50000 rounds" in error.message


def test_base64_round_trip():
    source = 'import crypto\nsay crypto.base64_decode(crypto.base64_encode("hi there"))'
    assert go(source).strip() == "hi there"


kaalka = pytest.importorskip("kaalka", reason="kaalka is an optional extra")


def test_kaalka_round_trip():
    source = """
import crypto
let secret = crypto.kaalka_encrypt("Hello, SHE!", "14:35:22")
say crypto.kaalka_decrypt(secret, "14:35:22")
"""
    assert go(source).strip() == "Hello, SHE!"


def test_kaalka_timestamp_is_optional():
    """v1 documented this as optional but it always failed. It works now."""
    source = """
import crypto
let secret = crypto.kaalka_encrypt("no timestamp")
say crypto.kaalka_decrypt(secret)
"""
    assert go(source).strip() == "no timestamp"


def test_seal_survives_a_round_trip_through_text():
    """Raw Kaalka output is not text-safe; `seal` armours it so it can travel."""
    source = """
import crypto
let sealed = crypto.seal("travels safely", "01:02:03")
say sealed is text.trim(sealed)
say crypto.open(sealed, "01:02:03")
"""
    assert go(source).strip() == "true\ntravels safely"


def test_envelope_detects_tampering():
    source = """
import crypto
let packet = crypto.envelope("hi", "ada", "bob", "01:02:03")
say crypto.open_envelope(packet, "bob")
try
  packet.body = crypto.seal("evil", "01:02:03")
  say crypto.open_envelope(packet, "bob")
catch e
  say "rejected: {e.message}"
end
"""
    output = go(source)
    assert "hi" in output
    assert "tampered with" in output


def test_envelope_checks_the_recipient():
    source = """
import crypto
let packet = crypto.envelope("hi", "ada", "bob", "01:02:03")
try
  say crypto.open_envelope(packet, "eve")
catch e
  say "rejected"
end
"""
    assert go(source).strip() == "rejected"


# --- modules and imports ----------------------------------------------------

def test_import_alias():
    assert go("import math as m\nsay m.floor(2.9)").strip() == "2"


def test_from_import():
    assert go("from math import sqrt\nsay sqrt(9)").strip() == "3"


def test_unknown_module_suggests():
    error = fails("import maths")
    assert "math" in (error.hint or "")


def test_use_another_file(tmp_path):
    helper = tmp_path / "helpers.she"
    helper.write_text('fun double(n) -> n * 2\n', encoding="utf-8")
    main = tmp_path / "main.she"
    main.write_text('use "./helpers.she" as helpers\nsay helpers.double(21)\n',
                    encoding="utf-8")
    out = io.StringIO()
    result, error = run(main.read_text(encoding="utf-8"), str(main),
                        sandbox=Sandbox.trusted(), out=out)
    assert error is None, error
    assert out.getvalue().strip() == "42"


# --- concurrency ------------------------------------------------------------

def test_async_and_await():
    source = """
async fun slow(n)
  return n * 2
end
let task = slow(21)
say await task
"""
    assert go(source).strip() == "42"


def test_await_many_tasks():
    source = """
async fun work(n) -> n * n
let tasks = [work(2), work(3)]
say await tasks
"""
    assert go(source).strip() == "[4, 9]"


# --- input ------------------------------------------------------------------

def test_ask_reads_input():
    assert go('let name = ask "Who?"\nsay "hi {name}"', answers=["Ada"]).strip() \
        == "hi Ada"


# --- tests inside SHE -------------------------------------------------------

def test_test_blocks_are_collected():
    from she.interp import Interpreter
    interp = Interpreter(sandbox=Sandbox.trusted())
    interp.run('test "adds"\n  expect 1 + 1 is 2\nend', "<test>")
    assert len(interp.tests) == 1
    node, env = interp.tests[0]
    interp.exec_block(node.body, env)      # passes silently
    interp.shutdown()


def test_failing_expectation_reports_both_sides():
    from she.errors import AssertErr
    from she.interp import Interpreter
    interp = Interpreter(sandbox=Sandbox.trusted())
    interp.run('test "wrong"\n  expect 1 is 2\nend', "<test>")
    node, env = interp.tests[0]
    with pytest.raises(AssertErr) as caught:
        interp.exec_block(node.body, env)
    assert "1" in caught.value.message and "2" in caught.value.message
    interp.shutdown()


# --- optional chaining and defaults -----------------------------------------

def test_safe_navigation():
    assert go("let m = nothing\nsay m?.name").strip() == "nothing"


def test_default_operator():
    assert go("let m = nothing\nsay m ?? \"fallback\"").strip() == "fallback"


def test_nothing_is_not_zero():
    assert go("say nothing is 0").strip() == "false"


def test_true_is_not_one():
    """v1 used 1/0 for booleans. Real booleans are their own thing now."""
    assert go("say true is 1").strip() == "false"


# --- optional extras degrade instead of crashing ----------------------------

def test_missing_optional_module_is_catchable():
    """`web` and `crypto` are optional extras. A program must be able to notice
    one is absent and carry on, rather than dying at the import."""
    source = """
import web
fun available?()
  try
    web.version()
    return true
  catch e: ImportError
    return false
  end
end
say type_of(available?())
"""
    assert go(source).strip() == "bool"


def test_import_of_an_optional_module_never_fails():
    """Importing is always fine; only reaching for a function can fail."""
    assert go("import web\nimport crypto\nsay 1").strip() == "1"
