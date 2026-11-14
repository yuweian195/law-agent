"""Contract text decoding and clause splitting."""

from __future__ import annotations

import io
import re
from pathlib import Path

from app.schemas import ContractClause, ParsedContract

_HEADING_RE = re.compile(
    r"^\s*(第[一二三四五六七八九十百零]+条|[一二三四五六七八九十]+、|\d+[.、]|（[一二三四五六七八九十]+）)\s*"
)
_PARTY_RE = re.compile(r"^(甲方|乙方|用人单位|劳动者)\s*[:：]\s*(.+)$")


def decode_text(filename: str, content: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        from docx import Document

        document = Document(io.BytesIO(content))
        parts = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append("  ".join(cell.text.strip() for cell in row.cells))
        return "\n".join(parts)
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u3000", " ")
    return "\n".join(line.rstrip() for line in text.splitlines())


def parse_contract(text: str) -> ParsedContract:
    text = _normalize(text)
    lines = [line.strip() for line in text.splitlines()]

    title = ""
    for line in lines:
        if line and not _HEADING_RE.match(line) and not _PARTY_RE.match(line):
            title = line
            break

    parties: list[str] = []
    for line in lines:
        match = _PARTY_RE.match(line)
        if match:
            parties.append(f"{match.group(1)}：{match.group(2).strip()}")

    heading_indexes = [
        index for index, line in enumerate(lines) if line and _HEADING_RE.match(line)
    ]
    clauses: list[ContractClause] = []
    if heading_indexes:
        for order, start in enumerate(heading_indexes, start=1):
            end = heading_indexes[order] if order < len(heading_indexes) else len(lines)
            heading = lines[start]
            body = "\n".join(
                line for line in lines[start + 1 : end] if line
            ).strip()
            clauses.append(
                ContractClause(
                    index=order,
                    title=heading[:80],
                    text=(heading + "\n" + body).strip(),
                )
            )
    else:
        paragraphs = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
        for order, paragraph in enumerate(paragraphs[:40], start=1):
            clauses.append(
                ContractClause(index=order, title=f"条款 {order}", text=paragraph)
            )

    return ParsedContract(title=title or "未命名合同", parties=parties, clauses=clauses)
