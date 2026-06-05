from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src import (  # noqa: E402
    ArticleSectionChunker,
    EmbeddingStore,
    VietnameseTextEmbedder,
    build_academic_policy_documents,
)


def load_group_queries() -> list[dict]:
    """Load shared group query/gold data from my own benchmark fixture."""
    query_path = Path(__file__).with_name("group_benchmark_queries.json")
    return json.loads(query_path.read_text(encoding="utf-8"))


def main() -> int:
    chunker = ArticleSectionChunker(max_chars=1400)
    embedder = VietnameseTextEmbedder()
    store = EmbeddingStore(collection_name="duc_academic_policy", embedding_fn=embedder)
    docs = build_academic_policy_documents(chunker=chunker)
    store.add_documents(docs)

    queries = load_group_queries()
    hits = 0

    print(f"Strategy: {chunker.__class__.__name__}(max_chars=1400) + {embedder._backend_name}")
    print(f"Indexed chunks: {len(docs)}")
    print("=" * 72)

    for index, item in enumerate(queries, start=1):
        query = item["q"]
        expected = item["expected_file"]
        metadata_filter = item.get("filter")
        if metadata_filter:
            results = store.search_with_filter(query, top_k=3, metadata_filter=metadata_filter)
        else:
            results = store.search(query, top_k=3)

        top_files = [result["metadata"].get("file_id") for result in results]
        relevant = expected in top_files
        hits += int(relevant)
        rank = top_files.index(expected) + 1 if relevant else "miss"
        top_score = results[0]["score"] if results else 0.0

        print(f"Q{index}: expected={expected} rank={rank} top3={top_files} top_score={top_score:.3f}")

    print("=" * 72)
    print(f"Precision@3: {hits}/{len(queries)} = {hits / len(queries):.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
