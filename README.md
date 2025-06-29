![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

# SHE - A Programming Language

SHE is a beginner-friendly programming language with a simple syntax for arithmetic, variables, conditionals, loops, functions, strings, lists, and more. This manual provides clear examples for every feature.

---

## 🚀 Getting Started

1. **Install Python** (if not already installed).
2. **Install the Kaalka encryption package** (required for encryption features):

    ```sh
    pip install kaalka
    ```

3. Open a terminal and navigate to the SHE directory.
4. Run SHE with:

    ```sh
    python3 shell.py
    ```

---

## 🧮 Arithmetic Operations

SHE supports all basic arithmetic operations and power:

```she
5 + 5        # 10
5 - 2        # 3
5 * 3        # 15
5 / 2        # 2.5
5 % 2        # 1
2 ^ 3        # 8 (power)
(1 + 2) * 3  # 9
```

---

## 📦 Variables

Store values using the `VAR` keyword:

```she
VAR a = 5
VAR b = 10
VAR sum = a + b
PRINT(sum)  # 15
```

---

## 🔎 Comparison Operations

Evaluate expressions and get boolean results (1 for True, 0 for False):

```she
PRINT(5 == 5)         # 1
PRINT(5 != 4)         # 1
PRINT(5 > 3)          # 1
PRINT(5 < 3)          # 0
PRINT(5 >= 5)         # 1
PRINT(5 <= 4)         # 0
PRINT(5 == 5 AND 5 == 4)  # 0
PRINT(5 == 5 OR 5 == 4)   # 1
```

---

## 🧭 Conditional Statements

Control flow with `IF`, `ELIF`, `ELSE`:

```she
VAR age = 19
VAR price = IF age >= 18 THEN 40 ELSE 20
PRINT(price)  # 40

VAR x = 5
VAR result = IF x > 10 THEN "big" ELIF x == 5 THEN "five" ELSE "small"
PRINT(result)  # five
```

---

## 🔁 Loops

### FOR Loop

```she
VAR result = 1
FOR i = 1 TO 5 THEN VAR result = result * i
PRINT(result)  # 120 (factorial of 5)
```

With step:

```she
FOR i = 10 TO 0 STEP -2 THEN PRINT(i)
# 10 8 6 4 2 0
```

### WHILE Loop

```she
VAR i = 0
WHILE i < 5 THEN
    PRINT(i)
    VAR i = i + 1
END
# 0 1 2 3 4
```

---

## 🧩 Functions

Define and use functions:

```she
FUN add(a, b) -> a + b
PRINT(add(6, 6))  # 12

VAR any = add
PRINT(any(5, 4))  # 9

VAR inc = FUN(a) -> a + 6
PRINT(inc(12))    # 18
```

---

## 📝 Strings

Work with strings:

```she
PRINT("This is a String")
PRINT("Hello " + "World")  # Hello World
PRINT("Hi! " * 3)           # Hi! Hi! Hi! 

FUN greet(person, times) -> "Hello, " * times + person
PRINT(greet("Piyush", 3))  # Hello, Hello, Hello, Piyush
```

---

## 📚 Lists

Create and manipulate lists:

```she
VAR list = [1, 2, 3]
PRINT(list)
VAR list2 = list + 4
PRINT(list2)  # [1, 2, 3, 4]
VAR concat = [1, 2, 3] * [4, 5]
PRINT(concat) # [1, 2, 3, 4, 5]
PRINT(list / 0)  # 1 (element at index 0)
```

Loop with lists:

```she
FOR i = 1 TO 5 THEN PRINT(i ^ 2)
# 1 4 9 16 25
```

---

## 🛠️ Built-in Functions

- `PRINT(value)` — Print a value
- `PRINT_RET(value)` — Return value as string
- `INPUT()` — Get user input
- `INPUT_INT()` — Get integer input
- `CLEAR()` or `CLS()` — Clear the screen
- `IS_NUM(value)` — Check if value is a number
- `IS_STRING(value)` — Check if value is a string
- `IS_FUN(value)` — Check if value is a function
- `IS_LIST(value)` — Check if value is a list
- `APPEND(list, value)` — Add value to list
- `POP(list, index)` — Remove and return value at index
- `EXTEND(list, other_list)` — Extend list
- `LEN(list)` — Length of list
- `RUN(filename)` — Run a SHE file
- `KAALKA_ENCRYPT(message, timestamp)` — Encrypt message
- `KAALKA_DECRYPT(encrypted_message, timestamp)` — Decrypt message

### Examples

```she
VAR list = [1, 2, 3]
APPEND(list, 4)
PRINT(list)  # [1, 2, 3, 4]
PRINT(POP(list, 2))  # 3
EXTEND(list, [5, 6])
PRINT(list)  # [1, 2, 4, 5, 6]
PRINT(LEN(list))  # 5
```

---

## 🖊️ Multiline Statements

You can chain statements on a single line using `;`:

```she
VAR result = IF 5 == 5 THEN; PRINT("math"); PRINT("works") ELSE PRINT("broken")
```

---

## ⏹️ Break and Continue

Control loop execution:

```she
FOR i = 0 TO 10 THEN
    IF i == 4 THEN CONTINUE
    ELIF i == 0 THEN BREAK
    VAR a = a + i
END
```

---

## 📂 Running SHE Files

Save your SHE code in a file (e.g., `example.she`) and run:

```she
RUN("example.she")
```

---

## 🔒 Kaalka Encryption Integration

SHE supports encryption and decryption using the Kaalka Encryption Algorithm as built-in functions.

### Kaalka Encryption Functions

- `KAALKA_ENCRYPT(message, timestamp)`
  - Encrypts the given message using the provided time (e.g., "14:35:22") as the key.
- `KAALKA_DECRYPT(encrypted_message, timestamp)`
  - Decrypts the given encrypted message using the provided time as the key.

#### Example Usage

```she
VAR msg = "Hello, SHE!"
VAR ts = "14:35:22"  # Use a time string (HH:MM:SS) as key
VAR encrypted = KAALKA_ENCRYPT(msg, ts)
PRINT(encrypted)
VAR decrypted = KAALKA_DECRYPT(encrypted, ts)
PRINT(decrypted)
```

---

## 🔐 Security and Encryption

With Kaalka, SHE can be used for secure message handling and cryptographic experiments. Always use the correct time key for encryption and decryption.

---

## 🤝 Contributing

Contributions are welcome! If you have suggestions, bug reports, or feature requests, please create an issue or submit a pull request.

---

## 📄 License

See the LICENSE file for details.
