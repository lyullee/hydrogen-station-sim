"""Small allow-listed expression language; no eval, attribute access, or code execution."""
from __future__ import annotations

import math
import re
from functools import lru_cache

TAG = re.compile(r"(?:PT|TT|FT|GD|FD)-\d{4}|MASS_HOSE_[12]|MASS_HEADER")
CALLS = {"RATE": 2, "DIFF": 2, "ABS_DIFF": 2, "BALANCE": 4, "AGE": 1, "P_ISOTHERM": 2}
CONDITION = re.compile(r"([a-z][a-z0-9_.]*)\s*(==|>=|<=|>|<)\s*(true|false|[A-Z_]+|-?\d+(?:\.\d+)?)")


class Unknown(ValueError):
    pass


def split_top(text: str, separator: str) -> list[str]:
    level, start, result = 0, 0, []
    for i, c in enumerate(text):
        level += (c == "(") - (c == ")")
        if level < 0 or level > 16: raise ValueError("Invalid expression nesting")
        if c == separator and level == 0:
            result.append(text[start:i].strip()); start = i + 1
    if level: raise ValueError("Unbalanced expression")
    return result + [text[start:].strip()]


@lru_cache(maxsize=1024)
def parse(text: str):
    text = text.strip()
    if len(text) > 1024: raise ValueError("Expression too long")
    pieces = split_top(text, "+")
    if len(pieces) > 1: return ("SUM", tuple(parse(x) for x in pieces))
    if TAG.fullmatch(text): return ("TAG", text)
    if re.fullmatch(r"\d+(?:\.\d+)?", text): return ("NUMBER", float(text))
    match = re.fullmatch(r"([A-Z_]+)\((.*)\)", text)
    if not match or match[1] not in CALLS: raise ValueError(f"Unsupported expression: {text}")
    args = tuple(parse(a) for a in split_top(match[2], ","))
    if len(args) != CALLS[match[1]]: raise ValueError("Invalid argument count")
    if match[1] in ("RATE", "BALANCE") and (args[-1][0] != "NUMBER" or args[-1][1] <= 0):
        raise ValueError("Positive numeric window required")
    if match[1] == "AGE" and args[0][0] != "TAG": raise ValueError("AGE requires a tag")
    return (match[1], args)


def validate_expression(text):
    parse(text)


def dependencies(text: str) -> set[str]:
    def walk(tree):
        if tree[0] == "TAG": return {tree[1]}
        if tree[0] == "NUMBER": return set()
        return set().union(*(walk(x) for x in tree[1]))
    return walk(parse(text))


def gate_parts(text):
    result = []
    for group in text.split(" OR "):
        items = []
        for condition in group.split(" AND "):
            m = CONDITION.fullmatch(condition.strip())
            if not m: raise ValueError(f"Unsupported mode condition: {condition}")
            key, op, raw = m.groups()
            value = {"true": True, "false": False}.get(raw, raw)
            if re.fullmatch(r"-?\d+(?:\.\d+)?", raw): value = float(raw)
            items.append((key, op, value))
        result.append(items)
    return result


def gate_dependencies(text):
    return {k for group in gate_parts(text) for k, _, _ in group}


def compare(value, op, limit):
    if op == ">=": return value >= limit
    if op == "<=": return value <= limit
    if op == ">": return value > limit
    if op == "<": return value < limit
    if op == "==": return value == limit
    raise ValueError("Unsupported comparator")


def evaluate_gate(text: str, modes: dict) -> bool | None:
    groups = []
    for group in gate_parts(text):
        vals = []
        for key, op, rhs in group:
            lhs = modes.get(key)
            if lhs is None: vals.append(None)
            else:
                try: vals.append(compare(lhs, op, rhs))
                except TypeError: vals.append(None)
        groups.append(False if False in vals else None if None in vals else True)
    return True if True in groups else None if None in groups else False


class Evaluator:
    def __init__(self, history: list[dict], specs: dict):
        self.history, self.specs = history, specs

    def read(self, tag, frame):
        data = frame["signals"].get(tag)
        if data is None: raise Unknown("MISSING:" + tag)
        if data.get("quality") != "GOOD": raise Unknown("QUALITY:" + tag)
        value = data.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value): raise Unknown("INVALID:" + tag)
        expected = self.specs.get(tag, {})
        if expected and data.get("unit") != expected["단위"]: raise Unknown("UNIT:" + tag)
        age = frame["time_s"] - data.get("time_s", float("-inf"))
        if age < -1e-9 or age >= expected.get("최대데이터나이_s", 1.0): raise Unknown("STALE:" + tag)
        return value

    def value(self, tree, frame):
        op, args = tree
        if op == "TAG": return self.read(args, frame)
        if op == "NUMBER": return args
        if op == "AGE":
            data = frame["signals"].get(args[0][1])
            if data is None or not math.isfinite(data.get("time_s", float("nan"))): raise Unknown("NO_TIMESTAMP")
            age = frame["time_s"] - data["time_s"]
            if age < 0: raise Unknown("FUTURE_TIMESTAMP")
            return age  # Timestamp age remains evaluable when measurement quality is BAD.
        if op == "P_ISOTHERM": raise Unknown("MODEL_UNAVAILABLE:validated isothermal EOS conversion")
        if op == "SUM": return sum(self.value(x, frame) for x in args)
        if op in ("DIFF", "ABS_DIFF"):
            delta = self.value(args[0], frame) - self.value(args[1], frame)
            return abs(delta) if op == "ABS_DIFF" else delta
        window = args[-1][1]
        end, start = frame["time_s"], frame["time_s"] - window
        if not self.history or self.history[0]["time_s"] > start + 1e-9: raise Unknown("HISTORY_REQUIRED")
        frames = [x for x in self.history if start - 2.01 <= x["time_s"] <= end + 1e-9]
        def at(expr, time):
            before = [x for x in frames if x["time_s"] <= time + 1e-9]
            after = [x for x in frames if x["time_s"] >= time - 1e-9]
            if not before or not after: raise Unknown("HISTORY_REQUIRED")
            a, b = before[-1], after[0]
            va, vb = self.value(expr, a), self.value(expr, b)
            if b["time_s"] == a["time_s"]: return va
            return va + (vb - va) * (time - a["time_s"]) / (b["time_s"] - a["time_s"])
        times = [start] + [x["time_s"] for x in frames if start < x["time_s"] < end] + [end]
        tags = set()
        def collect(node):
            if node[0] == "TAG": tags.add(node[1])
            elif node[0] != "NUMBER":
                for child in node[1]: collect(child)
        for arg in args[:-1]: collect(arg)
        gap = min((self.specs[tag]["최대데이터나이_s"] for tag in tags if tag in self.specs), default=1)
        actual_times = [x["time_s"] for x in frames if x["time_s"] >= start - gap - 1e-9]
        if any(b-a>gap+1e-9 for a,b in zip(actual_times,actual_times[1:])): raise Unknown("HISTORY_GAP")
        if op == "RATE":
            vals = [at(args[0], t) for t in times]  # Inspect all interior quality, not just endpoints.
            return (vals[-1] - vals[0]) / window
        if op == "BALANCE":
            ins, outs = [at(args[0], t) for t in times], [at(args[1], t) for t in times]
            mass = [at(args[2], t) for t in times]
            integral = sum(((ins[i]-outs[i]) + (ins[i+1]-outs[i+1])) * .5 * (times[i+1]-times[i]) for i in range(len(times)-1))
            return integral / window - 1000 * (mass[-1] - mass[0]) / window
        raise Unknown("UNSUPPORTED_EXPRESSION")

    def evaluate(self, expression, frame):
        value = self.value(parse(expression), frame)
        if not math.isfinite(value): raise Unknown("NONFINITE_DERIVED")
        return value
