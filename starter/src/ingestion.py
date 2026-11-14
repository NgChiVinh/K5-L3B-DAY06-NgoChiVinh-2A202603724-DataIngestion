"""Read and normalize source data for Day 06 Data Ingestion Lab."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pypdf

from .models import DocumentPage


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC) and whitespace without discarding paragraph/heading structure."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in text.split("\n"):
        cleaned = re.sub(r"[ \t]+", " ", raw_line).strip()
        lines.append(cleaned)
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    return normalized


def classify_wb_page(page_num: int) -> dict[str, Any]:
    """Deterministically classify pages of the World Bank Aug 2024 report based on its Table of Contents."""
    if 13 <= page_num <= 16:
        return {
            "is_valid_content": True,
            "section": "tong_quan",
            "sub_section": "tong_quan_kinh_te_vi_mo",
            "exclude_reason": None,
        }
    if 17 <= page_num <= 18:
        return {
            "is_valid_content": True,
            "section": "tong_quan",
            "sub_section": "tong_quan_thi_truong_von",
            "exclude_reason": None,
        }
    if 20 <= page_num <= 32:
        return {
            "is_valid_content": True,
            "section": "chuong_1_kinh_te_vi_mo",
            "sub_section": "dien_bien_kinh_te_gan_day",
            "exclude_reason": None,
        }
    if 33 <= page_num <= 37:
        return {
            "is_valid_content": True,
            "section": "chuong_1_kinh_te_vi_mo",
            "sub_section": "trien_vong_rui_ro_chinh_sach",
            "exclude_reason": None,
        }
    if 39 <= page_num <= 42:
        return {
            "is_valid_content": True,
            "section": "chuong_2_thi_truong_von",
            "sub_section": "gioi_thieu_va_khung_thi_truong_von",
            "exclude_reason": None,
        }
    if 43 <= page_num <= 49:
        return {
            "is_valid_content": True,
            "section": "chuong_2_thi_truong_von",
            "sub_section": "cong_cu_thi_truong_von",
            "exclude_reason": None,
        }
    if 50 <= page_num <= 57:
        return {
            "is_valid_content": True,
            "section": "chuong_2_thi_truong_von",
            "sub_section": "nha_dau_tu_to_chuc_va_ha_tang",
            "exclude_reason": None,
        }
    if 58 <= page_num <= 61:
        return {
            "is_valid_content": True,
            "section": "chuong_2_thi_truong_von",
            "sub_section": "thach_thuc_va_dinh_huong_tuong_lai",
            "exclude_reason": None,
        }

    if page_num in (1, 3, 64):
        reason = "cover_or_title_page"
    elif page_num in (2, 62, 63):
        reason = "blank_page"
    elif page_num == 4:
        reason = "copyright_and_disclaimer"
    elif page_num in (5, 6, 7, 8):
        reason = "table_of_contents_and_lists"
    elif page_num in (9, 10):
        reason = "abbreviations"
    elif page_num == 11:
        reason = "acknowledgments"
    elif page_num in (12, 19, 38):
        reason = "section_divider_title_only"
    else:
        reason = "other_non_content"

    return {
        "is_valid_content": False,
        "section": "excluded",
        "sub_section": "excluded",
        "exclude_reason": reason,
    }


def load_pdf(
    path: Path,
    document_id: str,
    source: str,
    log_path: Path | None = None,
) -> list[DocumentPage]:
    """Extract each physical page, log empty/excluded pages, and return valid content pages."""
    if not path.exists():
        raise FileNotFoundError(f"Source PDF not found at: {path}")

    reader = pypdf.PdfReader(str(path))
    valid_pages: list[DocumentPage] = []
    skipped_or_empty_pages: list[dict[str, Any]] = []

    for page_idx, pdf_page in enumerate(reader.pages, start=1):
        raw_text = pdf_page.extract_text() or ""
        norm_text = normalize_text(raw_text)
        page_info = classify_wb_page(page_idx)

        if not page_info["is_valid_content"] or len(norm_text) == 0:
            skipped_or_empty_pages.append(
                {
                    "document_id": document_id,
                    "source": source,
                    "page": page_idx,
                    "raw_chars": len(raw_text),
                    "normalized_chars": len(norm_text),
                    "reason": page_info["exclude_reason"] or "empty_text",
                }
            )
            continue

        metadata = {
            "document_id": document_id,
            "source": source,
            "page": page_idx,
            "section": page_info["section"],
            "sub_section": page_info["sub_section"],
            "year": 2024,
            "language": "vi",
            "document_type": "world_bank_taking_stock_report",
            "char_count": len(norm_text),
        }
        valid_pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=page_idx,
                text=norm_text,
                metadata=metadata,
            )
        )

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_payload = {
            "document_id": document_id,
            "source": source,
            "total_physical_pages": len(reader.pages),
            "valid_content_pages_count": len(valid_pages),
            "excluded_or_empty_pages_count": len(skipped_or_empty_pages),
            "total_valid_normalized_chars": sum(len(p.text) for p in valid_pages),
            "excluded_or_empty_pages": skipped_or_empty_pages,
        }
        log_path.write_text(
            json.dumps(log_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return valid_pages
