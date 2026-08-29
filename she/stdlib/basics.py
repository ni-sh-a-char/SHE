"""text, list and map modules.

These three double as the method tables behind `"hi".upper()`, `[1,2].sum()`
and `{a: 1}.keys()`, so every function here takes its subject first.
"""

import textwrap as _textwrap

from ..errors import IndexErr, KeyErr, TypeErr, ValueErr
from ..values import equal, iterate, show, truthy, type_name
from . import register


def _need_text(value, what):
    if not isinstance(value, str):
        raise TypeErr(f"`text.{what}` works on text, not a {type_name(value)}",
                      hint="convert first with `text(value)`.")
    return value


def _need_list(value, what):
    if not isinstance(value, list):
        raise TypeErr(f"`list.{what}` works on lists, not a {type_name(value)}",
                      hint="convert first with `list_of(value)`.")
    return value


def _need_map(value, what):
    if not isinstance(value, dict):
        raise TypeErr(f"`maps.{what}` works on maps, not a {type_name(value)}")
    return value


# --- text -------------------------------------------------------------------

@register("text", "Working with words and characters.")
def _text_module():
    def upper(s):
        """ALL CAPITALS."""
        return _need_text(s, "upper").upper()

    def lower(s):
        """all lowercase."""
        return _need_text(s, "lower").lower()

    def title(s):
        """Capitalise The First Letter Of Each Word."""
        return _need_text(s, "title").title()

    def capitalise(s):
        """Capitalise the first letter only."""
        text = _need_text(s, "capitalise")
        return text[:1].upper() + text[1:]

    def trim(s, chars=None):
        """Remove spaces (or given characters) from both ends."""
        return _need_text(s, "trim").strip(chars)

    def trim_start(s, chars=None):
        """Remove spaces from the start."""
        return _need_text(s, "trim_start").lstrip(chars)

    def trim_end(s, chars=None):
        """Remove spaces from the end."""
        return _need_text(s, "trim_end").rstrip(chars)

    def split(s, separator=None, limit=-1):
        """Break text into a list. Splits on spaces when no separator is given."""
        text = _need_text(s, "split")
        if separator == "":
            return list(text)
        return text.split(separator, int(limit))

    def lines(s):
        """Break text into a list of lines."""
        return _need_text(s, "lines").splitlines()

    def join(parts, separator=""):
        """Glue a list together into text."""
        items = iterate(parts) if not isinstance(parts, str) else [parts]
        if isinstance(separator, list):
            separator, items = parts, iterate(separator)
        return str(separator).join(str(p) if isinstance(p, str) else show(p) for p in items)

    def replace(s, find, with_, limit=-1):
        """Swap every occurrence of one piece of text for another."""
        return _need_text(s, "replace").replace(str(find), str(with_), int(limit))

    def contains(s, part):
        """True when the text holds that piece."""
        return str(part) in _need_text(s, "contains")

    def starts_with(s, prefix):
        """True when the text begins with that piece."""
        return _need_text(s, "starts_with").startswith(str(prefix))

    def ends_with(s, suffix):
        """True when the text ends with that piece."""
        return _need_text(s, "ends_with").endswith(str(suffix))

    def find(s, part, start=0):
        """Position of the first match, or -1 when there is none."""
        return _need_text(s, "find").find(str(part), int(start))

    def find_last(s, part):
        """Position of the last match, or -1."""
        return _need_text(s, "find_last").rfind(str(part))

    def slice_(s, start=0, stop=None):
        """A piece of the text, from one position up to another."""
        text = _need_text(s, "slice")
        return text[int(start):None if stop is None else int(stop)]

    def at(s, index):
        """The character at a position. Negative counts from the end."""
        text = _need_text(s, "at")
        index = int(index)
        if not text or index < -len(text) or index >= len(text):
            raise IndexErr(f"position {index} is outside text of length {len(text)}")
        return text[index]

    def chars(s):
        """Every character as a list."""
        return list(_need_text(s, "chars"))

    def repeat(s, times):
        """The text over and over."""
        return _need_text(s, "repeat") * max(0, int(times))

    def pad_start(s, width, fill=" "):
        """Pad on the left until it reaches a width."""
        return _need_text(s, "pad_start").rjust(int(width), str(fill)[:1] or " ")

    def pad_end(s, width, fill=" "):
        """Pad on the right until it reaches a width."""
        return _need_text(s, "pad_end").ljust(int(width), str(fill)[:1] or " ")

    def centre(s, width, fill=" "):
        """Centre the text in a given width."""
        return _need_text(s, "centre").center(int(width), str(fill)[:1] or " ")

    def wrap(s, width=70):
        """Break long text into lines no wider than `width`."""
        return _textwrap.wrap(_need_text(s, "wrap"), int(width))

    def indent(s, prefix="  "):
        """Put a prefix in front of every line."""
        return _textwrap.indent(_need_text(s, "indent"), str(prefix))

    def reverse(s):
        """The text backwards."""
        return _need_text(s, "reverse")[::-1]

    def is_empty(s):
        """True when there is nothing in it (spaces do not count)."""
        return not _need_text(s, "empty?").strip()

    def is_number(s):
        """True when the text can be read as a number."""
        try:
            float(_need_text(s, "number?").strip())
            return True
        except ValueError:
            return False

    def is_digits(s):
        """True when every character is 0-9."""
        return _need_text(s, "digits?").isdigit()

    def is_letters(s):
        """True when every character is a letter."""
        return _need_text(s, "letters?").isalpha()

    def code(s):
        """The character number (code point) of the first character."""
        text = _need_text(s, "code")
        if not text:
            raise ValueErr("`text.code` needs at least one character")
        return ord(text[0])

    def from_code(number):
        """The character for a code point."""
        return chr(int(number))

    def count(s, part):
        """How many times a piece appears."""
        return _need_text(s, "count").count(str(part))

    def between(s, start, stop):
        """The text between two markers, or empty when not found."""
        text = _need_text(s, "between")
        i = text.find(str(start))
        if i < 0:
            return ""
        i += len(str(start))
        j = text.find(str(stop), i)
        return text[i:] if j < 0 else text[i:j]

    def remove(s, part):
        """Delete every occurrence of a piece."""
        return _need_text(s, "remove").replace(str(part), "")

    def slug(s):
        """A url-friendly version: lowercase, dashes instead of spaces."""
        text = _need_text(s, "slug").lower().strip()
        out = [c if c.isalnum() else "-" for c in text]
        result = "".join(out)
        while "--" in result:
            result = result.replace("--", "-")
        return result.strip("-")

    return {
        "upper": upper, "lower": lower, "title": title, "capitalise": capitalise,
        "capitalize": capitalise, "trim": trim, "trim_start": trim_start,
        "trim_end": trim_end, "split": split, "lines": lines, "join": join,
        "replace": replace, "contains": contains, "starts_with": starts_with,
        "ends_with": ends_with, "find": find, "find_last": find_last,
        "slice": slice_, "at": at, "chars": chars, "repeat": repeat,
        "pad_start": pad_start, "pad_end": pad_end, "centre": centre,
        "center": centre, "wrap": wrap, "indent": indent, "reverse": reverse,
        "empty?": is_empty, "number?": is_number, "digits?": is_digits,
        "letters?": is_letters, "code": code, "from_code": from_code,
        "count": count, "between": between, "remove": remove, "slug": slug,
    }


# --- list -------------------------------------------------------------------

@register("list", "Working with ordered collections.")
def _list_module():
    def push(xs, *values):
        """Add one or more items to the end. Changes the list."""
        _need_list(xs, "push").extend(values)
        return xs

    def pop(xs, index=-1):
        """Remove and hand back an item, the last one by default."""
        items = _need_list(xs, "pop")
        if not items:
            raise IndexErr("this list is empty, so there is nothing to pop")
        index = int(index)
        if index < -len(items) or index >= len(items):
            raise IndexErr(f"position {index} is outside a list of {len(items)} items")
        return items.pop(index)

    def insert(xs, index, value):
        """Put an item at a position, moving the rest along."""
        _need_list(xs, "insert").insert(int(index), value)
        return xs

    def remove(xs, value):
        """Delete the first item equal to this. True when something went."""
        items = _need_list(xs, "remove")
        for i, item in enumerate(items):
            if equal(item, value):
                items.pop(i)
                return True
        return False

    def remove_at(xs, index):
        """Delete the item at a position and hand it back."""
        return pop(xs, index)

    def clear(xs):
        """Empty the list."""
        _need_list(xs, "clear").clear()
        return xs

    def index_of(xs, value):
        """Position of the first match, or -1."""
        for i, item in enumerate(_need_list(xs, "index_of")):
            if equal(item, value):
                return i
        return -1

    def contains(xs, value):
        """True when the list holds this item."""
        return any(equal(item, value) for item in _need_list(xs, "contains"))

    def slice_(xs, start=0, stop=None):
        """A piece of the list."""
        items = _need_list(xs, "slice")
        return items[int(start):None if stop is None else int(stop)]

    def take(xs, n):
        """The first n items."""
        return _need_list(xs, "take")[:max(0, int(n))]

    def drop(xs, n):
        """Everything after the first n items."""
        return _need_list(xs, "drop")[max(0, int(n)):]

    def first(xs, fallback=None):
        """The first item, or a fallback."""
        items = _need_list(xs, "first")
        return items[0] if items else fallback

    def last(xs, fallback=None):
        """The last item, or a fallback."""
        items = _need_list(xs, "last")
        return items[-1] if items else fallback

    def reverse(xs):
        """A reversed copy."""
        return list(reversed(_need_list(xs, "reverse")))

    def rotate(xs, n):
        """Move the first n items to the end. A negative n goes the other way."""
        items = _need_list(xs, "rotate")
        if not items:
            return []
        n = int(n) % len(items)
        return items[n:] + items[:n]

    def sort(interp, xs, by=None, descending=False):
        """A sorted copy. Pass `by` to sort on a computed value."""
        items = list(_need_list(xs, "sort"))
        if by is not None:
            return sorted(items, key=lambda i: interp.call_value(by, [i]),
                          reverse=truthy(descending))
        if all(isinstance(i, str) for i in items):
            return sorted(items, reverse=truthy(descending))
        for item in items:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise TypeErr(f"`list.sort` needs numbers or text, "
                              f"found a {type_name(item)}",
                              hint="pass `by:` to say what to sort on.")
        return sorted(items, reverse=truthy(descending))

    def unique(xs):
        """A copy with duplicates removed, keeping the original order."""
        out = []
        for item in _need_list(xs, "unique"):
            if not any(equal(item, seen) for seen in out):
                out.append(item)
        return out

    def flatten(xs, depth=1):
        """Pull nested lists up into one list."""
        depth = int(depth)

        def go(items, level):
            out = []
            for item in items:
                if isinstance(item, list) and level > 0:
                    out.extend(go(item, level - 1))
                else:
                    out.append(item)
            return out

        return go(_need_list(xs, "flatten"), depth if depth >= 0 else 10 ** 6)

    def chunk(xs, size):
        """Break into groups of at most `size`."""
        items = _need_list(xs, "chunk")
        size = int(size)
        if size < 1:
            raise ValueErr("`list.chunk` needs a size of at least 1")
        return [items[i:i + size] for i in range(0, len(items), size)]

    def group_by(interp, xs, fn):
        """Bucket items into a map, keyed by what the function returns."""
        out = {}
        for item in _need_list(xs, "group_by"):
            out.setdefault(interp.call_value(fn, [item]), []).append(item)
        return out

    def find(interp, xs, fn, fallback=None):
        """The first item the function says true for."""
        for item in _need_list(xs, "find"):
            if truthy(interp.call_value(fn, [item])):
                return item
        return fallback

    def find_index(interp, xs, fn):
        """Position of the first item the function says true for, or -1."""
        for i, item in enumerate(_need_list(xs, "find_index")):
            if truthy(interp.call_value(fn, [item])):
                return i
        return -1

    def partition(interp, xs, fn):
        """Split into [matching, not matching]."""
        yes, no = [], []
        for item in _need_list(xs, "partition"):
            (yes if truthy(interp.call_value(fn, [item])) else no).append(item)
        return [yes, no]

    def sum_(xs):
        """Add up the numbers."""
        items = _need_list(xs, "sum")
        for item in items:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise TypeErr(f"`list.sum` needs numbers, found a {type_name(item)}")
        return sum(items)

    def average(xs):
        """The mean of the numbers."""
        items = _need_list(xs, "average")
        if not items:
            raise ValueErr("`list.average` needs at least one number")
        return sum_(items) / len(items)

    def zip_(xs, *others):
        """Line up several lists into a list of groups."""
        lists = [_need_list(xs, "zip")] + [iterate(o) for o in others]
        return [list(group) for group in zip(*lists)]

    def join(xs, separator=""):
        """Glue the items together into text."""
        items = _need_list(xs, "join")
        return str(separator).join(i if isinstance(i, str) else show(i) for i in items)

    def shuffle(xs, seed=None):
        """A randomly reordered copy."""
        import random as _random
        rng = _random.Random(seed) if seed is not None else _random
        items = list(_need_list(xs, "shuffle"))
        rng.shuffle(items)
        return items

    def concat(xs, *others):
        """One list holding everything from all of them."""
        out = list(_need_list(xs, "concat"))
        for other in others:
            out.extend(iterate(other))
        return out

    def copy(xs):
        """A shallow copy."""
        return list(_need_list(xs, "copy"))

    def is_empty(xs):
        """True when there is nothing in it."""
        return not _need_list(xs, "empty?")

    def map_(interp, xs, fn):
        """Apply a function to every item."""
        return [interp.call_value(fn, [item]) for item in _need_list(xs, "map")]

    def filter_(interp, xs, fn):
        """Keep only the items the function says true for."""
        return [item for item in _need_list(xs, "filter")
                if truthy(interp.call_value(fn, [item]))]

    def reduce_(interp, xs, fn, start=None):
        """Fold the list down to a single value."""
        items = _need_list(xs, "reduce")
        if start is None:
            if not items:
                raise ValueErr("`list.reduce` on an empty list needs a starting value")
            total, items = items[0], items[1:]
        else:
            total = start
        for item in items:
            total = interp.call_value(fn, [total, item])
        return total

    def each_(interp, xs, fn):
        """Run a function for every item, keeping nothing."""
        for item in _need_list(xs, "each"):
            interp.call_value(fn, [item])
        return None

    def count_(interp, xs, fn=None):
        """How many items match."""
        items = _need_list(xs, "count")
        if fn is None:
            return len(items)
        return sum(1 for i in items if truthy(interp.call_value(fn, [i])))

    return {
        "map": map_, "filter": filter_, "reduce": reduce_, "each": each_,
        "count": count_,
        "push": push, "append": push, "pop": pop, "insert": insert,
        "remove": remove, "remove_at": remove_at, "clear": clear,
        "index_of": index_of, "contains": contains, "slice": slice_,
        "take": take, "drop": drop, "first": first, "last": last,
        "reverse": reverse, "rotate": rotate, "sort": sort, "unique": unique,
        "flatten": flatten,
        "chunk": chunk, "group_by": group_by, "find": find,
        "find_index": find_index, "partition": partition, "sum": sum_,
        "average": average, "mean": average, "zip": zip_, "join": join,
        "shuffle": shuffle, "concat": concat, "copy": copy, "empty?": is_empty,
    }


# --- map --------------------------------------------------------------------

@register("maps", "Working with key/value collections. Usually written as methods: `m.get(key)`.")
def _map_module():
    def get(m, key, fallback=None):
        """The value for a key, or a fallback when it is missing."""
        return _need_map(m, "get").get(key, fallback)

    def set_(m, key, value):
        """Store a value under a key. Changes the map."""
        _need_map(m, "set")[key] = value
        return m

    def has(m, key):
        """True when the key is present."""
        return key in _need_map(m, "has")

    def remove(m, key):
        """Delete a key and hand back its value."""
        items = _need_map(m, "remove")
        if key not in items:
            raise KeyErr(f"this map has no key {show(key, True)}",
                         hint="check with `map.has(m, key)` first.")
        return items.pop(key)

    def keys(m):
        """Every key, in insertion order."""
        return list(_need_map(m, "keys").keys())

    def values_(m):
        """Every value, in insertion order."""
        return list(_need_map(m, "values").values())

    def items(m):
        """Every [key, value] pair."""
        return [[k, v] for k, v in _need_map(m, "items").items()]

    def merge(m, *others):
        """A new map with the others layered on top."""
        out = dict(_need_map(m, "merge"))
        for other in others:
            out.update(_need_map(other, "merge"))
        return out

    def clear(m):
        """Empty the map."""
        _need_map(m, "clear").clear()
        return m

    def copy(m):
        """A shallow copy."""
        return dict(_need_map(m, "copy"))

    def invert(m):
        """Swap keys and values."""
        return {v: k for k, v in _need_map(m, "invert").items()}

    def pick(m, keys_wanted):
        """A smaller map holding only the keys listed."""
        source = _need_map(m, "pick")
        return {k: source[k] for k in iterate(keys_wanted) if k in source}

    def omit(m, keys_dropped):
        """A copy without the keys listed."""
        drop = set(iterate(keys_dropped))
        return {k: v for k, v in _need_map(m, "omit").items() if k not in drop}

    def map_values(interp, m, fn):
        """Apply a function to every value."""
        return {k: interp.call_value(fn, [v]) for k, v in _need_map(m, "map_values").items()}

    def filter_(interp, m, fn):
        """Keep only the pairs the function says true for."""
        return {k: v for k, v in _need_map(m, "filter").items()
                if truthy(interp.call_value(fn, [k, v]))}

    def is_empty(m):
        """True when there is nothing in it."""
        return not _need_map(m, "empty?")

    def default(m, key, value):
        """Set a key only when it is missing, then hand back its value."""
        return _need_map(m, "default").setdefault(key, value)

    return {
        "get": get, "set": set_, "has": has, "remove": remove, "keys": keys,
        "values": values_, "items": items, "merge": merge, "clear": clear,
        "copy": copy, "invert": invert, "pick": pick, "omit": omit,
        "map_values": map_values, "filter": filter_, "empty?": is_empty,
        "default": default,
    }
