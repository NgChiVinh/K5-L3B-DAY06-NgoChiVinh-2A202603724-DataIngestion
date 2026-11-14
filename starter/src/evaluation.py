"""Evaluate retrieved evidence and preserve per-query traces."""
from __future__ import annotations

import re
from typing import Any


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _extract_key_clauses(quote: str) -> list[str]:
    """Split an evidence quote into substantial clauses/sentences for evidence verification."""
    norm_q = _norm(quote)
    parts = [p.strip() for p in re.split(r"[.;]", norm_q) if len(p.strip()) >= 25]
    return parts if parts else [norm_q]


def _chunk_contains_evidence(chunk_text: str, evidence_quote: str) -> tuple[bool, bool, float]:
    """Return (is_full_evidence_hit, is_partial_fragment, clause_coverage_ratio)."""
    norm_chunk = _norm(chunk_text)
    norm_quote = _norm(evidence_quote)

    if norm_quote in norm_chunk:
        return True, False, 1.0

    clauses = _extract_key_clauses(evidence_quote)
    matched = sum(1 for c in clauses if c in norm_chunk)
    ratio = matched / len(clauses) if clauses else 0.0

    # Also check 60-char sliding windows of the quote if a single sentence was long
    if ratio < 1.0 and len(norm_quote) >= 60:
        anchor_start = norm_quote[:65]
        anchor_end = norm_quote[-65:]
        has_start = anchor_start in norm_chunk
        has_end = anchor_end in norm_chunk
        if has_start and has_end:
            return True, False, 1.0
        if has_start or has_end:
            return False, True, max(ratio, 0.5)

    if ratio >= 0.75:
        return True, False, ratio
    if ratio > 0.0:
        return False, True, ratio
    return False, False, 0.0


def evaluate_query(
    question: dict[str, Any],
    hits: list[dict[str, Any]],
    strategy: str = "",
    applied_filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check source/page and enough gold evidence; keep hit@1 and hit@3 trace."""
    valid_pairs: list[tuple[str, int, str]] = [
        (question["gold_source_id"], int(question["gold_page"]), question["evidence_quote"])
    ]
    for alt_page, alt_quote in zip(
        question.get("alternative_gold_pages", []),
        question.get("alternative_evidence_quotes", []),
    ):
        valid_pairs.append((question["gold_source_id"], int(alt_page), alt_quote))

    evaluated_hits: list[dict[str, Any]] = []
    for hit in hits:
        meta = hit.get("metadata", {})
        hit_doc = meta.get("document_id")
        hit_page = int(meta.get("page", -1))
        hit_text = hit.get("text", "")

        is_gold_page = False
        is_evidence_hit = False
        is_partial_split = False
        best_coverage = 0.0
        matched_gold_page: int | None = None

        for g_doc, g_page, g_quote in valid_pairs:
            if hit_doc == g_doc and hit_page == g_page:
                is_gold_page = True
                full_ok, partial_ok, cov = _chunk_contains_evidence(hit_text, g_quote)
                if full_ok:
                    is_evidence_hit = True
                    best_coverage = 1.0
                    matched_gold_page = g_page
                    break
                if partial_ok and cov > best_coverage:
                    is_partial_split = True
                    best_coverage = cov
                    matched_gold_page = g_page

        required_fields = ("document_id", "source", "page", "section")
        metadata_complete = all(meta.get(k) not in (None, "") for k in required_fields)

        q_filter = question.get("filter")
        if q_filter:
            filter_compliant = all(meta.get(fk) == fv for fk, fv in q_filter.items())
        else:
            filter_compliant = None

        evaluated_hits.append(
            {
                "rank": hit["rank"],
                "chunk_id": hit["chunk_id"],
                "score": hit["score"],
                "document_id": hit_doc,
                "source": meta.get("source"),
                "page": hit_page,
                "section": meta.get("section"),
                "sub_section": meta.get("sub_section"),
                "char_length": len(hit_text),
                "is_gold_source_and_page": is_gold_page,
                "is_evidence_hit": is_evidence_hit,
                "is_partial_split_evidence": is_partial_split and not is_evidence_hit,
                "evidence_coverage": round(best_coverage, 3),
                "matched_gold_page": matched_gold_page,
                "metadata_complete_and_valid": metadata_complete,
                "filter_compliant": filter_compliant,
                "text": hit_text,
                "metadata": meta,
            }
        )

    hit_at_1 = bool(evaluated_hits and evaluated_hits[0]["is_evidence_hit"])
    hit_at_3 = any(h["is_evidence_hit"] for h in evaluated_hits[:3])
    page_hit_at_3 = any(h["is_gold_source_and_page"] for h in evaluated_hits[:3])
    split_evidence_error = page_hit_at_3 and not hit_at_3

    q_filter = question.get("filter")
    if q_filter:
        all_top3_filter_compliant = bool(
            evaluated_hits and all(h["filter_compliant"] is True for h in evaluated_hits[:3])
        )
    else:
        all_top3_filter_compliant = None

    return {
        "strategy": strategy,
        "question_id": question["id"],
        "split": question["split"],
        "question_type": question.get("type", "unknown"),
        "question": question["question"],
        "expected_answer": question["expected_answer"],
        "gold_source_id": question["gold_source_id"],
        "gold_page": question["gold_page"],
        "alternative_gold_pages": question.get("alternative_gold_pages", []),
        "evidence_quote": question["evidence_quote"],
        "question_filter": q_filter,
        "applied_filter": applied_filter,
        "hit_at_1": hit_at_1,
        "evidence_hit_at_3": hit_at_3,
        "page_hit_at_3": page_hit_at_3,
        "split_evidence_across_chunks": split_evidence_error,
        "all_top3_filter_compliant": all_top3_filter_compliant,
        "top_k_hits": evaluated_hits,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    summary: dict[str, dict[str, Any]] = {}
    strategies = sorted({t["strategy"] for t in traces})

    for strat in strategies:
        summary[strat] = {}
        for split_name in ("dev", "test", "all"):
            if split_name == "all":
                sub = [t for t in traces if t["strategy"] == strat]
            else:
                sub = [t for t in traces if t["strategy"] == strat and t["split"] == split_name]
            total = len(sub)
            if total == 0:
                continue

            h1 = sum(1 for t in sub if t["hit_at_1"])
            h3 = sum(1 for t in sub if t["evidence_hit_at_3"])
            page_h3 = sum(1 for t in sub if t["page_hit_at_3"])
            split_errs = sum(1 for t in sub if t["split_evidence_across_chunks"])

            filter_qs = [t for t in sub if t["question_filter"] is not None]
            filter_total = len(filter_qs)
            filter_ok = sum(1 for t in filter_qs if t["all_top3_filter_compliant"] is True)

            all_hits = [h for t in sub for h in t["top_k_hits"]]
            meta_ok = sum(1 for h in all_hits if h["metadata_complete_and_valid"])
            meta_total = len(all_hits)

            summary[strat][split_name] = {
                "total_questions": total,
                "hit_at_1_count": h1,
                "hit_at_1_fraction": f"{h1}/{total}",
                "hit_at_1_pct": round(100.0 * h1 / total, 2),
                "evidence_hit_at_3_count": h3,
                "evidence_hit_at_3_fraction": f"{h3}/{total}",
                "evidence_hit_at_3_pct": round(100.0 * h3 / total, 2),
                "page_hit_at_3_count": page_h3,
                "page_hit_at_3_fraction": f"{page_h3}/{total}",
                "split_evidence_cases": split_errs,
                "metadata_valid_count": meta_ok,
                "metadata_valid_total": meta_total,
                "metadata_valid_fraction": f"{meta_ok}/{meta_total}",
                "metadata_valid_pct": round(100.0 * meta_ok / meta_total, 2) if meta_total else 0.0,
                "filter_questions_count": filter_total,
                "filter_compliant_count": filter_ok,
                "filter_compliant_fraction": f"{filter_ok}/{filter_total}" if filter_total > 0 else "N/A",
                "filter_compliant_pct": round(100.0 * filter_ok / filter_total, 2) if filter_total > 0 else None,
            }

    return summary
