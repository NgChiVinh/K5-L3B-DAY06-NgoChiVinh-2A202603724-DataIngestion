"""Main pipeline entry point for Day 06 Data Ingestion Engineering Lab."""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .models import Chunk, DocumentPage
from .store import QdrantVectorStore

sys.stdout.reconfigure(encoding="utf-8")


def _compute_chunk_stats(
    strategy: str,
    description: str,
    chunks: list[Chunk],
    ingest_seconds: float,
    count_before_reingest: int,
    count_after_reingest: int,
) -> dict[str, Any]:
    lengths = [len(c.text) for c in chunks]
    total_chars = sum(lengths)
    approx_tokens = sum(len(c.text.split()) for c in chunks)
    return {
        "strategy": strategy,
        "description": description,
        "chunk_count": len(chunks),
        "total_chars": total_chars,
        "approx_word_tokens": approx_tokens,
        "min_chars": min(lengths) if lengths else 0,
        "median_chars": round(float(statistics.median(lengths)), 1) if lengths else 0.0,
        "mean_chars": round(float(statistics.mean(lengths)), 1) if lengths else 0.0,
        "max_chars": max(lengths) if lengths else 0,
        "ingest_time_seconds": round(ingest_seconds, 3),
        "cost_usd": 0.0,
        "stored_count_first_ingest": count_before_reingest,
        "stored_count_after_reingest": count_after_reingest,
        "idempotent_reingest_verified": count_before_reingest == count_after_reingest == len(chunks),
    }


def _export_coherence_samples(
    pages: list[DocumentPage],
    chunks_by_strategy: dict[str, list[Chunk]],
    out_path: Path,
) -> None:
    """Select the first 10 valid content pages (sorted by page number) and export chunks covering them."""
    selected_pages = sorted(pages, key=lambda p: p.page)[:10]
    samples: list[dict[str, Any]] = []

    for page in selected_pages:
        anchor_snippet = " ".join(page.text.split()[:35])
        strat_chunks: dict[str, list[dict[str, Any]]] = {}
        for strat, ch_list in chunks_by_strategy.items():
            page_chunks = [c for c in ch_list if c.page == page.page]
            strat_chunks[strat] = [
                {
                    "chunk_id": c.chunk_id,
                    "char_length": len(c.text),
                    "text": c.text,
                }
                for c in page_chunks
            ]
        samples.append(
            {
                "sample_id": f"pos_{page.page:02d}",
                "document_id": page.document_id,
                "page": page.page,
                "section": page.metadata.get("section"),
                "anchor_snippet": anchor_snippet,
                "strategies": strat_chunks,
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    starter_dir = Path(__file__).resolve().parents[1]
    repo_root = starter_dir.parent
    load_dotenv(starter_dir / ".env")

    pdf_path = starter_dir / "data" / "wb_diem_lai_2024_08.pdf"
    benchmark_path = repo_root / "benchmark" / "questions.json"
    results_dir = repo_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=== STEP 1: Load & Normalize Corpus ===")
    pages = load_pdf(
        path=pdf_path,
        document_id="wb-diem-lai-2024-08",
        source="starter/data/wb_diem_lai_2024_08.pdf",
        log_path=results_dir / "ingestion_log.json",
    )
    if len(pages) < 30:
        raise RuntimeError(f"Corpus has only {len(pages)} valid content pages; minimum required is 30.")
    print(f"Loaded {len(pages)} valid content pages (>= 30 required).")

    benchmark_data = json.loads(benchmark_path.read_text(encoding="utf-8"))
    questions: list[dict[str, Any]] = benchmark_data["questions"]
    print(f"Loaded {len(questions)} benchmark questions (15 dev / 5 test).")

    print("\n=== STEP 2: Build Chunks for Strategies A, B, C ===")
    chunks_A: list[Chunk] = []
    chunks_B: list[Chunk] = []
    chunks_C: list[Chunk] = []

    for page in pages:
        chunks_A.extend(fixed_size(page, size=500, overlap=50, strategy_tag="A"))
        chunks_B.extend(by_paragraph(page, max_size=1000, strategy_tag="B"))
        chunks_C.extend(by_paragraph(page, max_size=1000, strategy_tag="C"))

    print(f"Strategy A (fixed_size 500/50) chunks: {len(chunks_A)}")
    print(f"Strategy B (by_paragraph max 1000, no filter) chunks: {len(chunks_B)}")
    print(f"Strategy C (by_paragraph max 1000, + metadata filter) chunks: {len(chunks_C)}")

    print("\n=== STEP 3: Initialize Real Embedder & Vector Store ===")
    embedder = MyEmbedder()
    print(
        f"Embedder ready -> provider={embedder.provider}, model={embedder.model_name}, dimensions={embedder.dimensions}"
    )

    qdrant_path = starter_dir / "qdrant_storage"
    store = QdrantVectorStore(storage_path=qdrant_path, dimensions=embedder.dimensions)

    try:
        strategy_stats: dict[str, Any] = {}

        # Embed Strategy A chunks
        t0 = time.perf_counter()
        vecs_A = embedder.embed_documents([c.text for c in chunks_A])
        store.upsert("A", chunks_A, vecs_A)
        t_A = time.perf_counter() - t0
        cnt_A_1 = store.count("A")
        # Re-ingest same version to verify idempotency (no duplicate records)
        store.upsert("A", chunks_A, vecs_A)
        cnt_A_2 = store.count("A")
        strategy_stats["A"] = _compute_chunk_stats(
            "A",
            "Fixed-size chunking (size=500 chars, overlap=50 chars), no metadata filter at retrieval",
            chunks_A,
            t_A,
            cnt_A_1,
            cnt_A_2,
        )

        # Embed Strategy B chunks (since B and C have identical chunk texts, we still measure & store both collections cleanly)
        t0 = time.perf_counter()
        vecs_B = embedder.embed_documents([c.text for c in chunks_B])
        store.upsert("B", chunks_B, vecs_B)
        t_B = time.perf_counter() - t0
        cnt_B_1 = store.count("B")
        store.upsert("B", chunks_B, vecs_B)
        cnt_B_2 = store.count("B")
        strategy_stats["B"] = _compute_chunk_stats(
            "B",
            "Structure/Paragraph-aware chunking (max_size=1000 chars), no metadata filter at retrieval",
            chunks_B,
            t_B,
            cnt_B_1,
            cnt_B_2,
        )

        # Upsert Strategy C collection using the same paragraph chunks & vectors
        t0 = time.perf_counter()
        store.upsert("C", chunks_C, vecs_B)
        t_C = time.perf_counter() - t0 + t_B
        cnt_C_1 = store.count("C")
        store.upsert("C", chunks_C, vecs_B)
        cnt_C_2 = store.count("C")
        strategy_stats["C"] = _compute_chunk_stats(
            "C",
            "Structure/Paragraph-aware chunking (max_size=1000 chars) + Metadata filter (section) when query specifies filter",
            chunks_C,
            t_C,
            cnt_C_1,
            cnt_C_2,
        )

        print("\n=== STEP 4: Run Benchmark Queries (Top-3) Across A, B, C ===")
        q_vecs_list = embedder.embed_queries([q["question"] for q in questions])
        query_vectors: dict[str, list[float]] = {
            q["id"]: vec for q, vec in zip(questions, q_vecs_list)
        }

        all_traces: list[dict[str, Any]] = []
        for strat in ("A", "B", "C"):
            for q in questions:
                q_vec = query_vectors[q["id"]]
                applied_filter = q.get("filter") if strat == "C" else None
                hits = store.search(
                    strategy=strat,
                    query_vector=q_vec,
                    top_k=3,
                    filters=applied_filter,
                )
                trace = evaluate_query(
                    question=q,
                    hits=hits,
                    strategy=strat,
                    applied_filter=applied_filter,
                )
                all_traces.append(trace)

        metrics_summary = summarize(all_traces)

        run_metadata = {
            "executed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "embedding_provider": embedder.provider,
            "embedding_model": embedder.model_name,
            "embedding_dimensions": embedder.dimensions,
            "total_api_calls": embedder.api_calls,
            "total_embedded_texts": embedder.total_embedded_texts,
            "total_embedded_chars": embedder.total_embedded_chars,
            "rate_limit_events": embedder.rate_limit_events,
            "vector_store": "Qdrant Local Persistent Store (qdrant-client 1.20.0)",
            "storage_path": str(qdrant_path.relative_to(repo_root)),
            "distance_metric": "Cosine (Exact search)",
            "strategy_stats": strategy_stats,
            "metrics_summary": metrics_summary,
        }

        (results_dir / "strategy_stats.json").write_text(
            json.dumps(strategy_stats, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (results_dir / "traces_all.json").write_text(
            json.dumps(all_traces, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (results_dir / "metrics_summary.json").write_text(
            json.dumps(run_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _export_coherence_samples(
            pages=pages,
            chunks_by_strategy={"A": chunks_A, "B": chunks_B, "C": chunks_C},
            out_path=results_dir / "coherence_samples_raw.json",
        )

        # Also copy results summary into starter/results/ for convenience
        starter_results = starter_dir / "results"
        starter_results.mkdir(parents=True, exist_ok=True)
        (starter_results / "metrics_summary.json").write_text(
            json.dumps(run_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        print("\n=== STEP 5: Summary of Retrieval Results ===")
        for strat in ("A", "B", "C"):
            dev_m = metrics_summary[strat]["dev"]
            test_m = metrics_summary[strat]["test"]
            print(
                f"Strategy {strat} ({strategy_stats[strat]['chunk_count']} chunks): "
                f"DEV Hit@1={dev_m['hit_at_1_fraction']} ({dev_m['hit_at_1_pct']}%), "
                f"DEV Hit@3={dev_m['evidence_hit_at_3_fraction']} ({dev_m['evidence_hit_at_3_pct']}%) | "
                f"TEST Hit@1={test_m['hit_at_1_fraction']} ({test_m['hit_at_1_pct']}%), "
                f"TEST Hit@3={test_m['evidence_hit_at_3_fraction']} ({test_m['evidence_hit_at_3_pct']}%)"
            )
    finally:
        store.close()


if __name__ == "__main__":
    main()
