# The SHE language

The complete reference. Every snippet here runs as written — paste any of them
into [the playground](https://she-lang.dev/playground) or a `.she` file.

- [Values](#values)
- [Text](#text)
- [Names](#names)
- [Operators](#operators)
- [Control flow](#control-flow)
- [Lists and maps](#lists-and-maps)
- [Functions](#functions)
- [Types](#types)
- [Pattern matching](#pattern-matching)
- [Errors](#errors)
- [Gradual typing](#gradual-typing)
- [Doing things at once](#doing-things-at-once)
- [Modules](#modules)
- [Testing](#testing)
- [Permissions](#permissions)
- [Grammar](#grammar)

---

## Values

| Kind | Examples |
|---|---|
| `number` | `42`, `3.14`, `1_000_000`, `0xff`, `0b1010`, `1.5e3` |
| `text` | `"hello"`, `'also hello'`, `"""a block"""`, `r"raw\n"` |
| `bool` | `true`, `false` |
| `nothing` | `nothing` |
| `list` | `[1, 2, 3]`, `[]` |
| `map` | `{name: "Ada", age: 36}`, `{}` |
| `range` | `1..10` (both ends), `1..<10` (stops before 10) |

`type_of(value)` tells you which one you have.

**Truthiness.** `false`, `nothing`, `0`, empty text, an empty list and an empty
map count as false. Everything else is true.

**Booleans are not numbers.** `true is 1` is `false`, and `nothing is 0` is
`false`. Convert deliberately with `to_number(true)`.

**Whole numbers stay whole.** `10 / 2` prints `5`, not `5.0`.

---

## Text

Anything inside `{braces}` is worked out and dropped in.

```she
let name = "Ada"
say "Hello, {name}! You have {2 + 3} messages."
say "joined: {names |> text.join(", ")}"
```

A `{` that does not hold a valid expression is left exactly as typed, so JSON,
CSS and patterns need no escaping:

```she
say '{"name": "Ada", "age": 36}'    # printed as written
say "a pattern like {2,3} is fine"
say "body {{ color: red }}"          # or double them to be explicit
```

Escapes: `\n` `\t` `\r` `\0` `\\` `\"` `\'` `\{` `\}` `\e`.
`r"..."` takes no escapes. `"""..."""` spans lines.

---

## Names

```she
let pi = 3.14159     # named once, never changes
var count = 0        # this one can change
count += 1
```

`let` is the default. Reassigning one is an error that tells you to use `var`.

Names may end in `?` when they answer a question: `empty?`, `prime?`, `valid?`.

---

## Operators

| Group | Operators |
|---|---|
| arithmetic | `+` `-` `*` `/` `//` `%` `^` |
| comparison | `is` `is not` `==` `!=` `<` `>` `<=` `>=` |
| logic | `and` `or` `not` |
| membership | `in` `not in` |
| ranges | `1..10` `1..<10` `1..10 by 2` |
| access | `.` `?.` `[]` `[a:b]` |
| defaults | `??` |
| pipeline | `\|>` |
| assignment | `=` `+=` `-=` `*=` `/=` `//=` `%=` `^=` `??=` |

`x |> f(a)` means `f(x, a)`. A line starting with `|>` or `.` continues the line
above, so a long chain can be written one step per line.

---

## Control flow

```she
if age >= 18
  say "you can vote"
else if age >= 16
  say "nearly there"
else
  say "not yet"
end

if ready then start()                      # one line
let price = if member then 20 else 40      # as a value
```

```she
for each item in shopping         end
for each i, item in shopping      end      # position and value
for each key, value in settings   end      # over a map
for each n in 1..10 by 2          end      # over a range

while countdown > 0               end
repeat ... until tries >= 3                # always runs at least once
```

`break` leaves the loop, `skip` moves to the next turn.

---

## Lists and maps

```she
let numbers = [4, 8, 15, 16]

numbers[0]        # 4
numbers[-1]       # 16, counting from the end
numbers[1:3]      # [8, 15]
numbers.length    # 4

let person = {name: "Ada", born: 1815}
person.name
person["born"]
person.get("email", "not given")
```

Every stdlib function is also a method: `text.upper(s)` and `s.upper()` are the
same call.

```she
let [first, second, ...rest] = numbers     # destructuring
let combined = [...a, ...b, 99]            # spreading
let updated = {...settings, theme: "dark"}
add(...arguments)
```

Lists are never shared behind your back: `a + [3]` gives a new list and leaves
`a` alone. Only `push`, `pop` and friends change one in place.

---

## Functions

```she
fun greet(who = "world") -> "Hello, {who}!"        # one expression

fun classify(n)                                    # several steps
  "Say whether a number is negative, zero or positive."
  if n < 0 then return "negative"
  if n is 0 then return "zero"
  return "positive"
end
```

A bare piece of text at the top of a body is its documentation, shown by `help`.

| Feature | How |
|---|---|
| Defaults | `fun greet(who = "world")` |
| Named arguments | `rectangle(width: 4, height: 3)` |
| Any number of values | `fun total(...numbers)` |
| Spreading a list in | `add(...pair)` |
| Anonymous | `let double = fun(n) -> n * 2` |
| Closures | An inner function keeps what it can see |

---

## Types

```she
type Point has x, y
  "A place on a flat grid."

  fun length(self) -> math.sqrt(self.x ^ 2 + self.y ^ 2)
  fun to_text(self) -> "({self.x}, {self.y})"
end

say Point(3, 4)            # (3, 4)
say Point(3, 4).length()   # 5
```

Two hooks: `setup(self)` runs just after a value is built, and `to_text(self)`
runs whenever it is printed.

```she
type Account has owner: text, balance: number = 0   # kinds and defaults

type Animal has name
  fun speak(self) -> "..."
  fun introduce(self) -> "{self.name} says {self.speak()}"
end

type Dog from Animal                                 # inheritance
  fun speak(self) -> "woof"
end
```

A type body holds functions. Re-declaring an inherited field replaces it rather
than adding a second one.

---

## Pattern matching

```she
match value
  case 0                    -> "nothing at all"
  case 1 | 2 | 3            -> "a small number"
  case number(n) if n < 0   -> "below zero"
  case 4..99                -> "a middling number"
  case []                   -> "an empty list"
  case [only]               -> "just {only}"
  case [first, ...rest]     -> "{first}, {rest.length} more"
  case {name: n}            -> "something called {n}"
  case Point(0, 0)          -> "the origin"
  case Point(x, y)          -> "at {x},{y}"
  case text(t)              -> "some words: {t}"
  case _                    -> "something else"
end
```

| Pattern | Matches |
|---|---|
| `42`, `"hi"`, `true` | Exactly that value |
| `n` | Anything, and names it |
| `_` | Anything, without naming it |
| `1 \| 2 \| 3` | Any one of several |
| `4..99` | A number in that range |
| `[a, b]` | A list of exactly two |
| `[first, ...rest]` | A list of one or more |
| `{name: n}` | A map holding at least `name` |
| `Point(x, y)` | That type, naming its fields in order |
| `number(n)`, `text(t)` | Any value of that kind |
| `case p if p > 0` | A condition on any pattern |

If nothing matches, SHE stops and says which value went unhandled.

A guard that raises propagates — `case n if n < 0` on a list is a type error,
not a silent non-match. Use `case number(n) if n < 0` when the subject may be
anything.

---

## Errors

```she
try
  risky()
catch e: MathError
  say "a maths problem: {e.message}"
catch e: IndexError | KeyError
  say "looked for something that was not there"
catch e
  say "anything else: {e.kind}"
finally
  say "cleaned up either way"
end

throw "the amount has to be positive"          # kind is "Error"
throw error("NotEnough", "you only have {balance}")

assert numbers.length > 0, "average needs a number"
```

Kinds SHE raises: `SyntaxError`, `NameError`, `TypeError`, `ValueError`,
`IndexError`, `KeyError`, `MathError`, `ImportError`, `PermissionError`,
`LimitError`, `AssertionError`.

---

## Gradual typing

Optional everywhere; checked as the program runs where present.

```she
let count: number = 0
fun area(w: number, h: number): number -> w * h
fun show(v: number|text) -> "{v}"
type Account has owner: text, balance: number = 0
```

Names: `number`, `text`, `bool`, `list`, `map`, `range`, `function`, `nothing`,
`error`, `any`, or any type you define. Join with `|`.

---

## Doing things at once

```she
async fun fetch_price(symbol)
  return http.json("https://api.example.com/{symbol}").price
end

let tasks = ["AAPL", "MSFT"] |> map(fetch_price)
for each price in await tasks
  say price
end
```

An `async fun` runs on a worker thread; calling it hands back a task straight
away, and `await` waits for the answer. That makes waiting on files and the
network genuinely parallel. It is not a green-threaded event loop, and SHE does
not pretend otherwise.

---

## Modules

```she
import math                    # math.sqrt(16)
import math as m               # m.sqrt(16)
from math import sqrt, pi      # sqrt(16)

use "./helpers.she" as helpers
from "./helpers.she" import double
```

`text`, `list`, `math`, `json`, `re`, `time` and `random` are always available.
Everything that can reach outside the program — `fs`, `http`, `os`, `crypto`,
`web`, `csv`, `maps` — must be imported on purpose.

---

## Testing

```she
test "converts freezing and boiling"
  expect celsius_to_fahrenheit(0) is 32
  expect celsius_to_fahrenheit(100) is 212
end
```

```sh
she test
  ok    converts freezing and boiling
  1 passed, 0 failed, 1 total
```

`expect` takes `is`, `is not`, `<`, `>`, `<=`, `>=`, `in`, or nothing at all
(meaning "this should be true"). Add a message with a comma. `assert` is the
same check for use outside tests.

---

## Permissions

A program starts with no authority at all.

| Flag | Allows |
|---|---|
| `--allow-read[=path]` | Reading files |
| `--allow-write[=path]` | Writing or deleting files |
| `--allow-net[=host]` | Network connections |
| `--allow-run[=program]` | Starting other programs |
| `--allow-env[=name]` | Reading environment variables |
| `--allow-time` | Sleeping |
| `--allow-all`, `-A` | Everything |
| `--max-steps=N` | Stop after N steps |
| `--timeout=N` | Stop after N seconds |
| `--max-depth=N` | How deep calls may nest (default 200) |

```sh
she run report.she --allow-read=./data --allow-net=api.stripe.com
she run untrusted.she --max-steps=5000000 --timeout=10
```

Scopes resolve paths before checking, so `--allow-read=./data` refuses
`./data/../../secrets.txt`.

Working things out — arithmetic, text, lists, maps, your own functions and
types — never needs a permission. See [SECURITY.md](../SECURITY.md) for what the
sandbox does and does not promise.

---

## Grammar

```
program     = statement*

statement   = ("let" | "var") target [":" type] "=" expression
            | target ("=" | "+=" | "-=" | ...) expression
            | "say" [expression ("," expression)*]
            | "if" expression ("then" statement | block ("else" ...)? "end")
            | "while" expression block "end"
            | "repeat" block "until" expression
            | "for" ["each"] targets "in" expression ["by" expression] block "end"
            | "fun" NAME params ["->" expression | block "end"]
            | "type" NAME ["has" fields] ["from" NAME] [methods "end"]
            | "try" block ("catch" [NAME [":" kinds]] block)* ["finally" block] "end"
            | "throw" expression
            | "import" NAME ["as" NAME] | "from" NAME "import" names
            | "use" TEXT ["as" NAME]
            | "test" TEXT block "end"
            | ("expect" | "assert") expression [op expression] ["," expression]
            | "return" [expression] | "break" | "skip"
            | expression

expression  = pipeline
pipeline    = coalesce ("|>" coalesce)*
coalesce    = or ("??" or)*
or          = and ("or" and)*
and         = compare ("and" compare)*
compare     = range (("is"|"is not"|"=="|"!="|"<"|">"|"<="|">="|"in") range)*
range       = sum ((".." | "..<") sum)*
sum         = product (("+" | "-") product)*
product     = power (("*" | "/" | "//" | "%") power)*
power       = unary ("^" power)*
unary       = ("not" | "-" | "+" | "await") unary | postfix
postfix     = primary (call | "." NAME | "?." NAME | "[" index "]")*
primary     = NUMBER | TEXT | "true" | "false" | "nothing" | NAME
            | "(" expression ")" | list | map | lambda
            | "if" e "then" e "else" e | "match" e case+ "end" | "ask" [e]
```
