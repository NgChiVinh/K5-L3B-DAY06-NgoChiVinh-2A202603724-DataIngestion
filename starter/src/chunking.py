"""Implement fixed-size and structure-aware (paragraph/heading) chunking."""
from __future__ import annotations

import re
from .models import Chunk, DocumentPage

HEADER_BOILERPLATE_RE = re.compile(
    r"^(\d+\s+)?BÁO CÁO ĐIỂM LẠI THÁNG 8/2024(\s+VƯƠN TỚI TẦM CAO MỚI TRÊN THỊ TRƯỜNG VỐN)?$",
    re.IGNORECASE,
)


def _collapse_inline_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fixed_size(
    page: DocumentPage,
    size: int = 500,
    overlap: int = 50,
    strategy_tag: str = "A",
) -> list[Chunk]:
    """Split page text into fixed-size overlapping character windows and retain page metadata."""
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")

    flat_text = _collapse_inline_whitespace(page.text)
    if not flat_text:
        return []

    chunks: list[Chunk] = []
    step = size - overlap
    start = 0
    chunk_idx = 1

    while start < len(flat_text):
        end = min(start + size, len(flat_text))
        window_text = flat_text[start:end].strip()
        if window_text:
            chunk_id = f"{page.document_id}__{strategy_tag}__p{page.page:02d}__c{chunk_idx:03d}"
            meta = dict(page.metadata)
            meta.update(
                {
                    "chunk_id": chunk_id,
                    "strategy": strategy_tag,
                    "chunking_method": "fixed_size",
                    "chunk_index": chunk_idx,
                    "char_start": start,
                    "char_end": end,
                    "char_length": len(window_text),
                }
            )
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=window_text,
                    metadata=meta,
                )
            )
            chunk_idx += 1
        if end >= len(flat_text):
            break
        start += step

    return chunks


def _extract_structural_blocks(page_text: str) -> list[str]:
    """Group lines into meaningful paragraphs/sections while removing running page headers."""
    lines = [line.strip() for line in page_text.split("\n") if line.strip()]
    filtered_lines: list[str] = []
    for idx, line in enumerate(lines):
        if idx <= 2 and (
            line.isdigit()
            or "BÁO CÁO ĐIỂM LẠI THÁNG 8/2024" in line
            or "VƯƠN TỚI TẦM CAO MỚI TRÊN THỊ TRƯỜNG VỐN" in line
        ):
            continue
        if HEADER_BOILERPLATE_RE.match(line):
            continue
        filtered_lines.append(line)

    blocks: list[str] = []
    current_lines: list[str] = []

    for line in filtered_lines:
        is_heading = bool(
            re.match(r"^(I{1,3}\.|[0-9]+\.[0-9]*|Bảng\s+\d+|Hình\s+\d+|Hộp\s+\d+)\b", line)
        )
        if is_heading and current_lines:
            blocks.append(" ".join(current_lines))
            current_lines = [line]
        else:
            current_lines.append(line)
            if line.endswith(".") and sum(len(x) for x in current_lines) >= 350:
                blocks.append(" ".join(current_lines))
                current_lines = []

    if current_lines:
        blocks.append(" ".join(current_lines))

    return [_collapse_inline_whitespace(b) for b in blocks if _collapse_inline_whitespace(b)]


def _split_oversized_block(block: str, max_size: int) -> list[str]:
    """Split an oversized paragraph along sentence boundaries when possible."""
    if len(block) <= max_size:
        return [block]

    sentences = re.split(r"(?<=[.!?])\s+", block)
    sub_blocks: list[str] = []
    current = ""

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        candidate = f"{current} {sent}".strip() if current else sent
        if len(candidate) <= max_size:
            current = candidate
        else:
            if current:
                sub_blocks.append(current)
            if len(sent) <= max_size:
                current = sent
            else:
                # Hard split only if a single sentence exceeds max_size
                for i in range(0, len(sent), max_size):
                    part = sent[i : i + max_size].strip()
                    if part:
                        sub_blocks.append(part)
                current = ""

    if current:
        sub_blocks.append(current)

    return sub_blocks


def by_paragraph(
    page: DocumentPage,
    max_size: int = 1000,
    strategy_tag: str = "B",
) -> list[Chunk]:
    """Group paragraphs/headings, split oversized blocks at sentence boundaries, and retain metadata."""
    if max_size <= 0:
        raise ValueError("max_size must be positive")

    blocks = _extract_structural_blocks(page.text)
    if not blocks:
        return []

    merged_Texts: list[str] = []
    current_chunk = ""

    for block in blocks:
        parts = _split_oversized_block(block, max_size=max_size)
        for part in parts:
            candidate = f"{current_chunk}\n\n{part}".strip() if current_chunk else part
            if len(candidate) <= max_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    merged_Texts.append(current_chunk)
                current_chunk = part

    if current_chunk:
        merged_Texts.append(current_chunk)

    chunks: list[Chunk] = []
    cursor = 0
    for idx, chunk_text in enumerate(merged_Texts, start=1):
        chunk_id = f"{page.document_id}__{strategy_tag}__p{page.page:02d}__c{idx:03d}"
        meta = dict(page.metadata)
        meta.update(
            {
                "chunk_id": chunk_id,
                "strategy": strategy_tag,
                "chunking_method": "by_paragraph",
                "chunk_index": idx,
                "char_start": cursor,
                "char_end": cursor + len(chunk_text),
                "char_length": len(chunk_text),
            }
        )
        cursor += len(chunk_text)
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=chunk_text,
                metadata=meta,
            )
        )

    return chunks
