"""math and random modules."""

import math as _math
import random as _random

from ..errors import MathErr, ValueErr
from ..values import iterate, to_number, type_name
from . import register


def _num(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MathErr(f"`math.{what}` needs a number, not a {type_name(value)}")
    return value


@register("math", "Numbers, rounding, trigonometry and statistics.")
def _math_module():
    def sqrt(x):
        """Square root."""
        x = _num(x, "sqrt")
        if x < 0:
            raise MathErr("a negative number has no real square root",
                          hint="check the value is not negative first.")
        return _math.sqrt(x)

    def root(x, n):
        """The nth root."""
        x, n = _num(x, "root"), _num(n, "root")
        if n == 0:
            raise MathErr("the 0th root has no meaning")
        if x < 0 and int(n) % 2 == 0:
            raise MathErr("a negative number has no real even root")
        return -((-x) ** (1 / n)) if x < 0 else x ** (1 / n)

    def power(x, n):
        """x raised to the power n."""
        return _num(x, "power") ** _num(n, "power")

    def floor(x):
        """Round down to a whole number."""
        return _math.floor(_num(x, "floor"))

    def ceil(x):
        """Round up to a whole number."""
        return _math.ceil(_num(x, "ceil"))

    def round_(x, places=0):
        """Round to a number of decimal places."""
        result = round(_num(x, "round"), int(places))
        return int(result) if places == 0 else result

    def truncate(x):
        """Drop the decimal part."""
        return _math.trunc(_num(x, "truncate"))

    def absolute(x):
        """Distance from zero."""
        return abs(_num(x, "absolute"))

    def sign(x):
        """-1, 0 or 1."""
        x = _num(x, "sign")
        return 0 if x == 0 else (1 if x > 0 else -1)

    def clamp(x, low, high):
        """Keep a number inside a range."""
        x, low, high = _num(x, "clamp"), _num(low, "clamp"), _num(high, "clamp")
        if low > high:
            low, high = high, low
        return max(low, min(high, x))

    def between(x, low, high):
        """True when low <= x <= high."""
        return _num(low, "between") <= _num(x, "between") <= _num(high, "between")

    def log(x, base=None):
        """Natural logarithm, or in the base you give."""
        x = _num(x, "log")
        if x <= 0:
            raise MathErr("the logarithm of zero or a negative number has no meaning")
        return _math.log(x) if base is None else _math.log(x, _num(base, "log"))

    def log2(x):
        """Logarithm in base 2."""
        return log(x, 2)

    def log10(x):
        """Logarithm in base 10."""
        return log(x, 10)

    def exp(x):
        """e raised to the power x."""
        return _math.exp(_num(x, "exp"))

    def factorial(n):
        """n! — the product of every whole number up to n."""
        n = _num(n, "factorial")
        if n < 0 or n != int(n):
            raise MathErr("factorial only works on whole numbers of zero or more")
        if n > 5000:
            raise MathErr("that factorial is far too large to work out")
        return _math.factorial(int(n))

    def gcd(a, b):
        """Greatest common divisor."""
        return _math.gcd(int(_num(a, "gcd")), int(_num(b, "gcd")))

    def lcm(a, b):
        """Lowest common multiple."""
        a, b = int(_num(a, "lcm")), int(_num(b, "lcm"))
        if a == 0 or b == 0:
            return 0
        return abs(a * b) // _math.gcd(a, b)

    def is_prime(n):
        """True when n has no divisors but 1 and itself."""
        n = _num(n, "prime?")
        if n != int(n) or n < 2:
            return False
        n = int(n)
        if n < 4:
            return True
        if n % 2 == 0:
            return False
        for i in range(3, _math.isqrt(n) + 1, 2):
            if n % i == 0:
                return False
        return True

    def is_even(n):
        """True when the number divides by 2."""
        return _num(n, "even?") % 2 == 0

    def is_odd(n):
        """True when the number does not divide by 2."""
        return _num(n, "odd?") % 2 != 0

    def mean(values):
        """The average."""
        items = _numbers(values, "mean")
        if not items:
            raise ValueErr("`math.mean` needs at least one number")
        return sum(items) / len(items)

    def median(values):
        """The middle value."""
        items = sorted(_numbers(values, "median"))
        if not items:
            raise ValueErr("`math.median` needs at least one number")
        mid = len(items) // 2
        return items[mid] if len(items) % 2 else (items[mid - 1] + items[mid]) / 2

    def mode(values):
        """The most common value."""
        items = _numbers(values, "mode")
        if not items:
            raise ValueErr("`math.mode` needs at least one number")
        counts = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        return max(counts, key=lambda k: (counts[k], -items.index(k)))

    def stdev(values):
        """Standard deviation of a whole population."""
        items = _numbers(values, "stdev")
        if len(items) < 2:
            raise ValueErr("`math.stdev` needs at least two numbers")
        avg = sum(items) / len(items)
        return _math.sqrt(sum((x - avg) ** 2 for x in items) / len(items))

    def variance(values):
        """Variance of a whole population."""
        return stdev(values) ** 2

    def sin(x):
        """Sine, in radians."""
        return _math.sin(_num(x, "sin"))

    def cos(x):
        """Cosine, in radians."""
        return _math.cos(_num(x, "cos"))

    def tan(x):
        """Tangent, in radians."""
        return _math.tan(_num(x, "tan"))

    def asin(x):
        """Inverse sine."""
        x = _num(x, "asin")
        if not -1 <= x <= 1:
            raise MathErr("`math.asin` needs a value between -1 and 1")
        return _math.asin(x)

    def acos(x):
        """Inverse cosine."""
        x = _num(x, "acos")
        if not -1 <= x <= 1:
            raise MathErr("`math.acos` needs a value between -1 and 1")
        return _math.acos(x)

    def atan(x, y=None):
        """Inverse tangent. Give two values for atan2."""
        return _math.atan(_num(x, "atan")) if y is None \
            else _math.atan2(_num(x, "atan"), _num(y, "atan"))

    def degrees(x):
        """Radians to degrees."""
        return _math.degrees(_num(x, "degrees"))

    def radians(x):
        """Degrees to radians."""
        return _math.radians(_num(x, "radians"))

    def hypotenuse(a, b):
        """The long side of a right triangle."""
        return _math.hypot(_num(a, "hypotenuse"), _num(b, "hypotenuse"))

    def is_nan(x):
        """True when the value is 'not a number'."""
        return isinstance(x, float) and x != x

    def is_finite(x):
        """True when the number is neither infinite nor nan."""
        return isinstance(x, (int, float)) and not isinstance(x, bool) \
            and _math.isfinite(x)

    def to_base(n, base):
        """Whole number as text in another base, up to 36."""
        n, base = int(_num(n, "to_base")), int(_num(base, "to_base"))
        if not 2 <= base <= 36:
            raise ValueErr("`math.to_base` supports bases 2 to 36")
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"
        sign_text = "-" if n < 0 else ""
        n = abs(n)
        if n == 0:
            return "0"
        out = ""
        while n:
            n, rem = divmod(n, base)
            out = digits[rem] + out
        return sign_text + out

    def from_base(text, base):
        """Read text in another base back into a number."""
        try:
            return int(str(text), int(base))
        except ValueError:
            raise ValueErr(f"`{text}` is not a valid base-{int(base)} number")

    return {
        "pi": _math.pi, "e": _math.e, "tau": _math.tau,
        "infinity": _math.inf, "nan": _math.nan,
        "sqrt": sqrt, "root": root, "power": power, "floor": floor,
        "ceil": ceil, "round": round_, "truncate": truncate,
        "absolute": absolute, "abs": absolute, "sign": sign, "clamp": clamp,
        "between": between, "log": log, "log2": log2, "log10": log10,
        "exp": exp, "factorial": factorial, "gcd": gcd, "lcm": lcm,
        "prime?": is_prime, "even?": is_even, "odd?": is_odd,
        "mean": mean, "average": mean, "median": median, "mode": mode,
        "stdev": stdev, "variance": variance,
        "sin": sin, "cos": cos, "tan": tan, "asin": asin, "acos": acos,
        "atan": atan, "degrees": degrees, "radians": radians,
        "hypotenuse": hypotenuse, "nan?": is_nan, "finite?": is_finite,
        "to_base": to_base, "from_base": from_base,
    }


def _numbers(values, what):
    items = iterate(values)
    for item in items:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise MathErr(f"`math.{what}` needs numbers, found a {type_name(item)}")
    return items


@register("random", "Dice, shuffles and random choices.")
def _random_module():
    state = {"rng": _random.Random()}

    def seed(value=None):
        """Fix the sequence so runs repeat. Useful for tests."""
        state["rng"] = _random.Random(value)
        return None

    def number(low=0.0, high=1.0):
        """A random decimal between two values."""
        return state["rng"].uniform(to_number(low), to_number(high))

    def whole(low, high=None):
        """A random whole number, both ends included."""
        if high is None:
            low, high = 0, low
        low, high = int(to_number(low)), int(to_number(high))
        if low > high:
            low, high = high, low
        return state["rng"].randint(low, high)

    def choice(items):
        """One item picked at random."""
        values = iterate(items)
        if not values:
            raise ValueErr("`random.choice` needs something to choose from")
        return state["rng"].choice(values)

    def sample(items, count):
        """Several different items picked at random."""
        values = iterate(items)
        count = int(to_number(count))
        if count > len(values):
            raise ValueErr(f"cannot take {count} different items from {len(values)}")
        return state["rng"].sample(values, count)

    def shuffle(items):
        """A randomly reordered copy."""
        values = list(iterate(items))
        state["rng"].shuffle(values)
        return values

    def chance(probability=0.5):
        """True with the given probability, 0 to 1."""
        return state["rng"].random() < to_number(probability)

    def dice(sides=6, count=1):
        """Roll dice and add them up."""
        sides, count = int(to_number(sides)), int(to_number(count))
        if sides < 2 or count < 1:
            raise ValueErr("dice need at least 2 sides and 1 roll")
        return sum(state["rng"].randint(1, sides) for _ in range(count))

    def uuid():
        """A random unique identifier."""
        import uuid as _uuid
        return str(_uuid.uuid4())

    return {"seed": seed, "number": number, "whole": whole, "integer": whole,
            "choice": choice, "sample": sample, "shuffle": shuffle,
            "chance": chance, "dice": dice, "uuid": uuid}
