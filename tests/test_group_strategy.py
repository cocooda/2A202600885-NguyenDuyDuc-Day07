from src import ArticleSectionChunker, Document, EmbeddingStore, VietnameseTextEmbedder


def test_article_section_chunker_keeps_article_context():
    text = """
# Quy Che Dao Tao

## Dieu 26. Xu Ly Vi Pham

### Thi Ho

Sinh vien thi ho hoac nho nguoi thi ho deu bi ky luat.
- Vi pham lan thu nhat: dinh chi hoc tap 01 nam
- Vi pham lan thu hai: buoc thoi hoc
"""

    chunks = ArticleSectionChunker(max_chars=500).chunk(text)

    thi_ho_chunk = next(chunk for chunk in chunks if "Thi Ho" in chunk)
    assert "Dieu 26. Xu Ly Vi Pham" in thi_ho_chunk
    assert "Sinh vien thi ho" in thi_ho_chunk


def test_vietnamese_text_embedder_ranks_matching_policy_topic_first():
    store = EmbeddingStore(collection_name="policy_strategy_test", embedding_fn=VietnameseTextEmbedder())
    store.add_documents(
        [
            Document(
                id="discipline",
                content=(
                    "Dieu 26. Thi Ho. Sinh vien thi ho hoac nho nguoi thi ho "
                    "bi dinh chi hoc tap 01 nam neu vi pham lan thu nhat."
                ),
                metadata={"category": "discipline"},
            ),
            Document(
                id="graduation",
                content=(
                    "Dieu 20. Tot nghiep. Sinh vien duoc xet tot nghiep khi "
                    "tich luy du tin chi va diem trung binh tich luy dat tu 2.0."
                ),
                metadata={"category": "graduation"},
            ),
        ]
    )

    results = store.search("Sinh vien thi ho bi xu ly ky luat nhu the nao?", top_k=2)

    assert results[0]["metadata"]["doc_id"] == "discipline"
