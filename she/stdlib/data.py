"""json, re (patterns), time and csv modules."""

import datetime as _dt
import json as _json
import re as _re
import time as _time

from ..errors import TypeErr, ValueErr
from ..values import Instance, Range, iterate, show, type_name
from . import register


def _to_plain(value, seen=None):
    """SHE value -> something the json module can write."""
    seen = seen or set()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if id(value) in seen:
        raise ValueErr("this value refers to itself, so it cannot become JSON")
    seen = seen | {id(value)}
    if isinstance(value, list):
        return [_to_plain(v, seen) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_plain(v, seen) for k, v in value.items()}
    if isinstance(value, Instance):
        return {k: _to_plain(v, seen) for k, v in value.fields.items()}
    if isinstance(value, Range):
        return list(value)
    raise TypeErr(f"a {type_name(value)} cannot be written as JSON",
                  hint="JSON holds text, numbers, true/false, nothing, lists and maps.")


@register("json", "Reading and writing JSON.")
def _json_module():
    def parse(text):
        """Read JSON text into SHE values."""
        if not isinstance(text, str):
            raise TypeErr(f"`json.parse` needs text, not a {type_name(text)}")
        try:
            return _json.loads(text)
        except _json.JSONDecodeError as exc:
            raise ValueErr(f"this is not valid JSON: {exc.msg} (line {exc.lineno})",
                           hint="check for a missing comma, quote or bracket.")

    def stringify(value, pretty=False, indent=2):
        """Write a value as JSON text."""
        plain = _to_plain(value)
        if pretty:
            return _json.dumps(plain, indent=int(indent), ensure_ascii=False)
        return _json.dumps(plain, separators=(",", ":"), ensure_ascii=False)

    def pretty(value, indent=2):
        """Write a value as nicely indented JSON."""
        return stringify(value, True, indent)

    def valid(text):
        """True when the text is valid JSON."""
        try:
            _json.loads(text)
            return True
        except (_json.JSONDecodeError, TypeError):
            return False

    return {"parse": parse, "stringify": stringify, "pretty": pretty,
            "write": stringify, "read": parse, "valid?": valid}


@register("re", "Finding and replacing with patterns.")
def _re_module():
    def _compile(pattern, ignore_case=False):
        try:
            return _re.compile(str(pattern), _re.IGNORECASE if ignore_case else 0)
        except _re.error as exc:
            raise ValueErr(f"this pattern is not valid: {exc}",
                           hint="patterns use the usual regular-expression syntax.")

    def matches(text, pattern, ignore_case=False):
        """True when the pattern is found anywhere in the text."""
        return _compile(pattern, ignore_case).search(str(text)) is not None

    def find(text, pattern, ignore_case=False):
        """The first match as text, or nothing."""
        found = _compile(pattern, ignore_case).search(str(text))
        return found.group(0) if found else None

    def find_all(text, pattern, ignore_case=False):
        """Every match as a list."""
        return _compile(pattern, ignore_case).findall(str(text))

    def groups(text, pattern, ignore_case=False):
        """The captured groups of the first match."""
        found = _compile(pattern, ignore_case).search(str(text))
        if not found:
            return []
        return [g if g is not None else None for g in found.groups()]

    def named(text, pattern, ignore_case=False):
        """The named groups of the first match, as a map."""
        found = _compile(pattern, ignore_case).search(str(text))
        return dict(found.groupdict()) if found else {}

    def replace(text, pattern, with_, limit=0, ignore_case=False):
        """Swap every match for something else."""
        return _compile(pattern, ignore_case).sub(str(with_), str(text), count=int(limit))

    def split(text, pattern, ignore_case=False):
        """Break text apart wherever the pattern matches."""
        return _compile(pattern, ignore_case).split(str(text))

    def escape(text):
        """Treat text as literal characters inside a pattern."""
        return _re.escape(str(text))

    def count(text, pattern, ignore_case=False):
        """How many times the pattern matches."""
        return len(_compile(pattern, ignore_case).findall(str(text)))

    return {"matches?": matches, "match?": matches, "find": find,
            "find_all": find_all, "groups": groups, "named": named,
            "replace": replace, "split": split, "escape": escape, "count": count}


@register("time", "Clocks, dates and waiting. Needs --allow-time to sleep.")
def _time_module():
    def now():
        """The current date and time as text (ISO 8601)."""
        return _dt.datetime.now().isoformat(timespec="seconds")

    def today():
        """Today as YYYY-MM-DD."""
        return _dt.date.today().isoformat()

    def clock():
        """The current time of day as HH:MM:SS."""
        return _dt.datetime.now().strftime("%H:%M:%S")

    def timestamp():
        """Seconds since 1 January 1970."""
        return _time.time()

    def monotonic():
        """A steadily rising number of seconds. Good for measuring durations."""
        return _time.monotonic()

    def sleep(interp, seconds):
        """Pause for a while."""
        seconds = float(seconds)
        if seconds < 0:
            raise ValueErr("you cannot sleep for a negative time")
        if seconds > 300:
            raise ValueErr("sleeping longer than 5 minutes is probably a mistake")
        interp.sandbox.require("time", action="pause the program")
        _time.sleep(seconds)
        return None

    def format(when=None, pattern="%Y-%m-%d %H:%M:%S"):
        """Format a timestamp or ISO text with a pattern."""
        moment = _coerce(when)
        return moment.strftime(str(pattern))

    def parse(text, pattern=None):
        """Read a date from text into a timestamp."""
        try:
            if pattern:
                return _dt.datetime.strptime(str(text), str(pattern)).timestamp()
            return _dt.datetime.fromisoformat(str(text)).timestamp()
        except ValueError as exc:
            raise ValueErr(f"I could not read `{text}` as a date: {exc}",
                           hint="try an ISO date like 2026-08-27, or pass a pattern.")

    def parts(when=None):
        """A date broken into year, month, day, hour, minute, second."""
        moment = _coerce(when)
        return {"year": moment.year, "month": moment.month, "day": moment.day,
                "hour": moment.hour, "minute": moment.minute,
                "second": moment.second, "weekday": moment.strftime("%A")}

    def add(when, days=0, hours=0, minutes=0, seconds=0):
        """Move a moment forward (or back, with negatives)."""
        moment = _coerce(when) + _dt.timedelta(days=days, hours=hours,
                                               minutes=minutes, seconds=seconds)
        return moment.timestamp()

    def difference(a, b):
        """Seconds between two moments."""
        return abs(_coerce(a).timestamp() - _coerce(b).timestamp())

    def _coerce(when):
        if when is None:
            return _dt.datetime.now()
        if isinstance(when, (int, float)) and not isinstance(when, bool):
            return _dt.datetime.fromtimestamp(when)
        if isinstance(when, str):
            try:
                return _dt.datetime.fromisoformat(when)
            except ValueError:
                raise ValueErr(f"I could not read `{when}` as a date")
        raise TypeErr(f"a {type_name(when)} is not a moment in time")

    return {"now": now, "today": today, "clock": clock, "timestamp": timestamp,
            "monotonic": monotonic, "sleep": sleep, "format": format,
            "parse": parse, "parts": parts, "add": add, "difference": difference}


@register("csv", "Reading and writing comma-separated tables.")
def _csv_module():
    import csv as _csv
    import io as _io

    def parse(text, headers=True, separator=","):
        """Read CSV text. With headers you get a list of maps."""
        reader = _csv.reader(_io.StringIO(str(text)), delimiter=str(separator)[:1] or ",")
        rows = [list(row) for row in reader]
        if not headers:
            return rows
        if not rows:
            return []
        head, *rest = rows
        return [{key: row[i] if i < len(row) else None for i, key in enumerate(head)}
                for row in rest]

    def stringify(rows, headers=None, separator=","):
        """Write a list of maps or lists as CSV text."""
        items = iterate(rows)
        buffer = _io.StringIO()
        writer = _csv.writer(buffer, delimiter=str(separator)[:1] or ",",
                             lineterminator="\n")
        if items and isinstance(items[0], dict):
            keys = list(headers) if headers else list(items[0].keys())
            writer.writerow(keys)
            for row in items:
                writer.writerow([_cell(row.get(k)) for k in keys])
        else:
            if headers:
                writer.writerow(list(headers))
            for row in items:
                writer.writerow([_cell(c) for c in iterate(row)])
        return buffer.getvalue()

    def _cell(value):
        return "" if value is None else (value if isinstance(value, str) else show(value))

    return {"parse": parse, "stringify": stringify, "read": parse, "write": stringify}
