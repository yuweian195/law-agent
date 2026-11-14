"""Chinese-friendly tokenizer for BM25 retrieval.

No external segmentation dependency: ASCII words are kept whole, Chinese text
is indexed as character bigrams.  This is robust for legal terms such as
"竞业限制", "经济补偿" and "试用期".
"""

from __future__ import annotations

import re

_ASCII_RE = re.compile(r"[a-zA-Z0-9]+")
_CHINESE_RE = re.compile(r"[\u4e00-\u9fa5]+")


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens: list[str] = _ASCII_RE.findall(text)
    for segment in _CHINESE_RE.findall(text):
        if len(segment) == 1:
            tokens.append(segment)
            continue
        tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return tokens
