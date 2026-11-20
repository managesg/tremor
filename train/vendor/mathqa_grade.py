# Excerpt (lines 56-64, 223-281, 311-350, unchanged except the module shim below) of github.com/RikiyaT/lm_understand-logs
# exp8_math/code/mathqa.py, clone HEAD 4d09ba6d6a7e891dd8063974dfe81b3d78e3494f. Licence: MIT; notice reproduced as required:
# MIT License
#
# Copyright (c) 2026 the authors of "LLMs can understand and write neural network weights"
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import functools
import re
import sys
import threading

MATHVERIFY_PKGS = ""  # shim: math_verify is installed in the image


# ---------------------------------------------------------------- prompt
INSTRUCTION = "Please reason step by step, and put your final answer within \\boxed{}."
TEMPLATE = "math_qwen_boxed_v1"


def build_prompt(problem):
    """The user turn: the problem, a newline, Qwen's math instruction."""
    return problem + "\n" + INSTRUCTION



def answer_text(text):
    """The text the extraction reads: a stray reasoning block cut off (up to the last '</think>')."""
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    return text


_BOX_FORMS = re.compile(r"\\boxed|\\fbox")


def _box_at(text, idx):
    """the content of the box that starts at text[idx] ('\\boxed' or '\\fbox'), or None."""
    key = "\\boxed" if text.startswith("\\boxed", idx) else "\\fbox"
    rest = text[idx + len(key):]
    r = rest.lstrip()
    if r.startswith("{"):   # brace matched, as last_boxed_only_string
        depth = 0
        for k, ch in enumerate(r):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    out = r[1:k].strip()
                    return out or None
        return None          # not closed (e.g. a response cut inside the box)
    if key == "\\boxed" and rest.startswith(" "):   # '\\boxed 5': up to the next '$' or line end (Qwen's reading)
        out = rest.strip().split("$")[0].split("\n")[0].strip()
        return out or None
    return None


def last_boxed(text):
    """The content of the last box of a text, or None: hendrycks last_boxed_only_string + remove_boxed (the last
    '\\boxed', else the last '\\fbox'; brace matched; an unclosed last box = None), extended to '\\fbox{..}',
    '\\boxed {..}' and '\\boxed 5' (no braces: read up to the next '$' or line end, as Qwen's evaluation reads it).
    An empty box = None."""
    idx = text.rfind("\\boxed")
    if idx < 0:
        idx = text.rfind("\\fbox")
        if idx < 0:
            return None
    return _box_at(text, idx)


def boxed_values(text):
    """the distinct contents of every box in a text."""
    return {b for b in (_box_at(text, m.start()) for m in _BOX_FORMS.finditer(text)) if b is not None}


def extract(text):
    """(answer or None, number of boxes in the text)."""
    t = answer_text(text)
    return last_boxed(t), len(_BOX_FORMS.findall(t))


def gold_of_solution(solution):
    """The gold answer of a reference solution (the last box)."""
    return last_boxed(solution)


# ---------------------------------------------------------------- the checker (math-verify)
_MV = []


def mv():
    """the math_verify module (from MATHVERIFY_PKGS when the venv does not have it)."""
    if not _MV:
        try:
            import math_verify  # noqa: PLC0415
        except ImportError:
            if MATHVERIFY_PKGS not in sys.path:
                sys.path.append(MATHVERIFY_PKGS)
            import math_verify  # noqa: PLC0415
        _MV.append(math_verify)
    return _MV[0]


def _timeouts():
    """math-verify's timeouts use signal.alarm, which works only in the main thread; elsewhere they raise and the
    library would silently return 'not equal'. Off the main thread the checks run without its timeouts."""
    return 5 if threading.current_thread() is threading.main_thread() else None


@functools.lru_cache(maxsize=1 << 16)
def _parsed(s, to):
    return mv().parse("\\boxed{" + s + "}", parsing_timeout=to)


def is_correct(pred, gold):
    """math-verify equivalence of a boxed answer and the gold answer (False for no answer / unparseable gold)."""
    if pred is None or gold is None:
        return False
    to = _timeouts()
    g, p = _parsed(gold, to), _parsed(pred, to)
    if not g or not p:
        return False
    try:
        return bool(mv().verify(g, p, timeout_seconds=to))
    except Exception:  # noqa: BLE001
        return False
