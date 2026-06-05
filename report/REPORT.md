# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Duy Đức
**Nhóm:** B2
**Ngày:** 2026-06-05

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> High cosine similarity nghĩa là hai vector gần cùng hướng, nên hai đoạn văn có nội dung hoặc ý định gần nhau về mặt ngữ nghĩa.

**Ví dụ HIGH similarity:**
- Sentence A: Sinh viên được xét tốt nghiệp khi tích lũy đủ tín chỉ.
- Sentence B: Điều kiện tốt nghiệp gồm hoàn thành đủ học phần và tín chỉ.
- Tại sao tương đồng: Cả hai câu đều nói về điều kiện tốt nghiệp.

**Ví dụ LOW similarity:**
- Sentence A: Sinh viên thi hộ bị xử lý kỷ luật.
- Sentence B: Python là ngôn ngữ lập trình phổ biến.
- Tại sao khác: Hai câu thuộc hai domain khác nhau.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> Cosine similarity tập trung vào hướng vector thay vì độ lớn tuyệt đối. Với text embeddings, hướng vector thường phản ánh ý nghĩa tốt hơn khoảng cách thô.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Phép tính: `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = 23`
> Đáp án: 23 chunks.

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = 25`, nên số chunk tăng từ 23 lên 25. Overlap nhiều hơn giúp giữ ngữ cảnh ở ranh giới chunk, nhưng tốn thêm lưu trữ và thời gian search.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Quy chế đào tạo đại học, đăng ký học phần, đánh giá kết quả học tập, tốt nghiệp, nghỉ học/chuyển ngành và kỷ luật sinh viên.

**Tại sao nhóm chọn domain này?**
> Bộ tài liệu có cấu trúc điều khoản rõ ràng, phù hợp để thử retrieval theo heading, section và metadata. Các benchmark queries có gold answers cụ thể, có thể verify trực tiếp từ nội dung trong `data/`.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | quy_che_dao_tao.md | `data/quy_che_dao_tao.md` | 3709 | `category=academics`, `chapter=I`, `language=vi` |
| 2 | dang_ky_hoc_phan.md | `data/dang_ky_hoc_phan.md` | 3832 | `category=registration`, `chapter=II`, `language=vi` |
| 3 | danh_gia_ket_qua_hoc_tap.md | `data/danh_gia_ket_qua_hoc_tap.md` | 4634 | `category=assessment`, `chapter=III`, `language=vi` |
| 4 | tot_nghiep_va_bang_cap.md | `data/tot_nghiep_va_bang_cap.md` | 3670 | `category=graduation`, `chapter=III`, `language=vi` |
| 5 | nghi_hoc_chuyen_nganh.md | `data/nghi_hoc_chuyen_nganh.md` | 4603 | `category=transfer`, `chapter=IV`, `language=vi` |
| 6 | ky_luat_sinh_vien.md | `data/ky_luat_sinh_vien.md` | 3174 | `category=discipline`, `chapter=IV`, `language=vi` |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `category` | string | `graduation`, `discipline` | Lọc đúng nhóm quy định khi query có phạm vi rõ. |
| `chapter` | string | `III`, `IV` | Phân biệt nhóm điều khoản trong quy chế. |
| `source` | string | `data/tot_nghiep_va_bang_cap.md` | Trace evidence về file gốc. |
| `file_id` | string | `tot_nghiep_va_bang_cap` | Chấm benchmark theo expected file. |
| `language` | string | `vi` | Tránh trộn dữ liệu khác ngôn ngữ nếu dataset mở rộng. |
| `chunk_index` | int | `7` | Debug chunk nào được retrieve. |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| danh_gia_ket_qua_hoc_tap.md | FixedSizeChunker (`fixed_size`) | 10 | 463.4 | Trung bình; có thể cắt giữa điều kiện cảnh báo học vụ. |
| danh_gia_ket_qua_hoc_tap.md | SentenceChunker (`by_sentences`) | 4 | 1156.8 | Giữ câu tốt nhưng chunk dài, trộn nhiều mục. |
| danh_gia_ket_qua_hoc_tap.md | RecursiveChunker (`recursive`) | 12 | 384.2 | Tốt hơn fixed-size, nhưng heading không luôn đi cùng nội dung. |
| tot_nghiep_va_bang_cap.md | FixedSizeChunker (`fixed_size`) | 8 | 458.8 | Trung bình; có thể cắt bảng/hạng khỏi lý do giảm hạng. |
| tot_nghiep_va_bang_cap.md | SentenceChunker (`by_sentences`) | 5 | 731.6 | Giữ câu tốt nhưng mỗi chunk chứa nhiều subsection. |
| tot_nghiep_va_bang_cap.md | RecursiveChunker (`recursive`) | 9 | 405.9 | Tốt; giữ paragraph ổn nhưng chưa gắn metadata article/section. |
| dang_ky_hoc_phan.md | FixedSizeChunker (`fixed_size`) | 8 | 479.0 | Trung bình; có thể cắt giữa mức tín chỉ cử nhân/kỹ sư. |
| dang_ky_hoc_phan.md | SentenceChunker (`by_sentences`) | 6 | 636.3 | Giữ câu tốt nhưng chưa tận dụng cấu trúc `Điều 10`. |
| dang_ky_hoc_phan.md | RecursiveChunker (`recursive`) | 9 | 423.9 | Tốt nhất trong 3 baseline built-in. |

### Strategy Của Tôi

**Loại:** custom strategy: `ArticleSectionChunker(max_chars=1400)` + `VietnameseTextEmbedder(dim=512)`

**Mô tả cách hoạt động:**
> Strategy chunk theo cấu trúc markdown của tài liệu quy chế: tiêu đề tài liệu, chương, `Điều ...`, subsection `###`, rồi nội dung body/bullet/table. Mỗi chunk được gắn lại heading context để khi retrieve một đoạn về "thi hộ" vẫn thấy nó thuộc `Điều 26. Xử lý vi phạm`. Nếu một section dài hơn `max_chars`, chunker chia nhỏ body nhưng vẫn lặp lại heading ở từng chunk con. Embedder chuẩn hóa tiếng Việt không dấu, bỏ stopwords, rồi hash unigram/bigram/trigram vào vector 512 chiều để bắt các cụm như `thi ho`, `xet tot nghiep`, `canh bao hoc tap`.

**Tại sao tôi chọn strategy này cho domain nhóm?**
> Tài liệu nhóm là quy chế dạng điều khoản, không phải văn xuôi tự do. Gold answers thường nằm trong một block điều khoản và các bullet điều kiện, nên strategy cần giữ nguyên heading + rule block để evidence đủ rõ khi demo. So với fixed-size và recursive thông thường, chunk theo article/section giúp giảm nguy cơ mất tiêu đề hoặc tách rời điều kiện liên quan.

**Code snippet (nếu custom):**
```python
from src import ArticleSectionChunker, VietnameseTextEmbedder

chunker = ArticleSectionChunker(max_chars=1400)
embedder = VietnameseTextEmbedder(dim=512)
```

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| all group docs | best baseline: RecursiveChunker(500) | 60 | 391.8 | Precision@3 = 5/5; context tốt nhưng heading không luôn lặp lại. |
| all group docs | **của tôi: ArticleSectionChunker(1400)** | 60 | 478.2 | Precision@3 = 5/5; top chunks có article/subsection/rule block rõ hơn. |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi | ArticleSectionChunker(1400) + VietnameseTextEmbedder | 10 / 10 | Giữ article context, top-1 expected file 5/5, không cần dependency ngoài. | Lexical embedder chưa hiểu paraphrase xa như semantic embedding thật. |
| Thu Linh | RecursiveChunker(300) | 10 / 10 | Score cao nhất, chunk khớp cấu trúc Điều/Khoản. | Nhiều chunk nhỏ (107), tốc độ index chậm hơn. |
| Bút | Semantic Chunking | 10 / 10 | Lọc cực kỳ thông minh, chunk ngữ nghĩa trọn vẹn. | Thời gian chạy cực kỳ chậm (embed từng câu). |
| Hải An | FixedSize(500, overlap=50) | 10 / 10 | Kiểm soát kích thước tốt. | Score thấp nhất, overlap tạo chunk dư thừa. |
| Quang | MetadataAwareChunker(900) + metadata schema/filter | 10 / 10 | Gán metadata `category`, `article_number`, `section_title`; filter trước khi rank; dễ trace nguồn. | Filter hiện mới dùng category-level nên Q5 còn score thấp. |

**Strategy nào tốt nhất cho domain này? Tại sao?**
> Nhóm thống nhất strategy của Thu Linh (`RecursiveChunker(300)`) là tốt nhất cho domain này. Strategy này vẫn đạt 10/10 như các strategy khác, nhưng có score cao nhất và chunk khớp tốt với cấu trúc Điều/Khoản của tài liệu quy chế. Điểm yếu là tạo nhiều chunk nhỏ (107 chunks) nên tốc độ index chậm hơn, nhưng đổi lại retrieval evidence chi tiết và dễ bám sát từng điều khoản hơn.

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> Tôi xử lý input rỗng trước, sau đó dùng regex `(?<=[.!?])\s+` để tách theo dấu kết thúc câu. Các câu được strip whitespace và nhóm theo `max_sentences_per_chunk`. Constructor dùng `max(1, max_sentences_per_chunk)` để tránh tham số 0 làm lỗi vòng lặp.

**`RecursiveChunker.chunk` / `_split`** — approach:
> `chunk()` gọi `_split()` với separator priority `["\n\n", "\n", ". ", " ", ""]`. Base case là đoạn hiện tại không vượt quá `chunk_size`. Nếu đoạn quá dài, `_split()` thử separator hiện tại; phần nào vẫn quá dài thì recurse với separator nhỏ hơn, và fallback cuối cùng là cắt fixed-size.

### EmbeddingStore

**`add_documents` + `search`** — approach:
> `add_documents()` chuẩn hóa mỗi `Document` thành record gồm `id`, `content`, `metadata`, `embedding`, rồi lưu vào `_store` in-memory. Nếu ChromaDB optional có sẵn thì mirror sang collection, nhưng in-memory vẫn là source of truth để tests ổn định. `search()` embed query, tính cosine similarity bằng `compute_similarity()`, sort giảm dần theo score và lấy `top_k`.

**`search_with_filter` + `delete_document`** — approach:
> `search_with_filter()` lọc metadata trước rồi mới search, vì filter sau search có thể làm mất candidate đúng. Filter dùng exact match theo các field như `category` hoặc `language`. `delete_document()` xóa tất cả record có `metadata["doc_id"] == doc_id`, trả `True` nếu có xóa và `False` nếu không tìm thấy.

### KnowledgeBaseAgent

**`answer`** — approach:
> `answer()` strip câu hỏi, trả message rõ nếu input rỗng, retrieve top-k chunks từ store, rồi build prompt gồm instruction, context đánh số và question. Context được inject trực tiếp vào prompt để LLM chỉ trả lời dựa trên evidence đã retrieve. Nếu không có result hoặc `llm_fn` lỗi, agent trả fallback message thay vì crash.

### Test Results

```text
pytest tests/ -v
44 passed
```

**Số tests pass:** 44 / 44

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Sinh viên bị cảnh báo học vụ khi nợ nhiều tín chỉ. | Cảnh báo học tập áp dụng khi tín chỉ không đạt vượt quá 50 phần trăm. | high | 0.396 | Đúng |
| 2 | Điều kiện tốt nghiệp là tích lũy đủ tín chỉ và GPA từ 2.0. | Sinh viên được công nhận tốt nghiệp khi đủ tín chỉ và điểm trung bình tích lũy từ 2.0. | high | 0.557 | Đúng |
| 3 | Sinh viên thi hộ bị đình chỉ học tập một năm. | Người nhờ thi hộ lần đầu bị kỷ luật đình chỉ một năm. | high | 0.360 | Đúng |
| 4 | Học kỳ hè tối đa 8 tín chỉ. | Bằng tốt nghiệp được cấp trong 30 ngày. | low | 0.117 | Đúng một phần |
| 5 | Python là ngôn ngữ lập trình phổ biến. | Sinh viên chuyển ngành cần được hiệu trưởng đồng ý. | low | 0.248 | Không |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> Pair 5 bất ngờ nhất: hai câu khác domain nhưng vẫn có score 0.248. Nguyên nhân là `VietnameseTextEmbedder` là lexical hashing embedder, nên một số token/cụm phổ biến hoặc hash collision có thể tạo similarity dương dù nghĩa không gần. Điều này cho thấy lexical embedding phù hợp cho benchmark có thuật ngữ trùng rõ, nhưng chưa biểu diễn nghĩa tốt như semantic embedding thật.

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân của bạn trong package `src`. **5 queries phải trùng với các thành viên cùng nhóm.**

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | Sinh viên bị cảnh báo học vụ khi nào? | Khi tín chỉ không đạt > 50% đăng ký, hoặc nợ > 24 tín chỉ; điểm TB học kỳ < 0.8 (kỳ 1) / < 1.0; điểm TB tích lũy dưới ngưỡng theo năm. Tối đa 4 lần, không quá 2 lần liên tiếp. |
| 2 | Điều kiện để được xét tốt nghiệp là gì? | Tích lũy đủ tín chỉ; điểm TB tích lũy >= 2.0; không bị truy cứu hình sự hoặc đình chỉ; có đơn xin xét tốt nghiệp nếu tốt nghiệp sớm/muộn. |
| 3 | Số tín chỉ tối đa có thể đăng ký trong một học kỳ chính là bao nhiêu? | Cử nhân: tối đa 26 tín chỉ. Kỹ sư: tối đa 30 tín chỉ (kỹ sư tài năng: 33). Học kỳ hè: tối đa 8 tín chỉ. |
| 4 | Sinh viên thi hộ bị xử lý kỷ luật như thế nào? | Lần 1: đình chỉ học 1 năm. Lần 2: buộc thôi học. Áp dụng cả người thi hộ và người nhờ thi hộ. |
| 5 | Hạng tốt nghiệp bị giảm một mức trong trường hợp nào? | Khi khối lượng học lại > 5% tổng tín chỉ chương trình, hoặc đã bị kỷ luật từ mức cảnh cáo trở lên trong thời gian học. |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Sinh viên bị cảnh báo học vụ khi nào? | `danh_gia_ket_qua_hoc_tap`: Điều 16, điều kiện cảnh báo học tập | 0.347 | Có | Chunk nêu 3 nhóm điều kiện: tín chỉ không đạt > 50% hoặc nợ > 24; điểm TB học kỳ dưới 0.8/1.0; điểm TB tích lũy dưới ngưỡng theo năm. Cũng có giới hạn tối đa 4 lần, không quá 2 lần liên tiếp. |
| 2 | Điều kiện để được xét tốt nghiệp là gì? | `tot_nghiep_va_bang_cap`: Điều 20, điều kiện xét tốt nghiệp | 0.406 | Có | Chunk nêu điều kiện tốt nghiệp: tích lũy đủ học phần/tín chỉ và chuẩn đầu ra; điểm TB tích lũy >= 2.0; không bị truy cứu hình sự hoặc đình chỉ; có đơn nếu tốt nghiệp sớm/muộn. |
| 3 | Số tín chỉ tối đa có thể đăng ký trong một học kỳ chính là bao nhiêu? | `dang_ky_hoc_phan`: Điều 10, số lượng tín chỉ đăng ký | 0.484 | Có | Chunk nêu học kỳ chính: kỹ sư tối đa 30 tín chỉ, kỹ sư tài năng 33; cử nhân tối đa 26 tín chỉ. Chunk cũng ghi học kỳ hè tối đa 8 tín chỉ. |
| 4 | Sinh viên thi hộ bị xử lý kỷ luật như thế nào? | `ky_luat_sinh_vien`: Điều 26, thi hộ | 0.314 | Có | Chunk nêu cả người thi hộ và người nhờ thi hộ đều bị kỷ luật: lần thứ nhất đình chỉ học tập 01 năm; lần thứ hai buộc thôi học. |
| 5 | Hạng tốt nghiệp bị giảm một mức trong trường hợp nào? | `tot_nghiep_va_bang_cap`: Điều 20, hạng tốt nghiệp bị giảm một mức | 0.356 | Có | Chunk nêu hạng tốt nghiệp bị giảm một mức nếu học phần phải học lại vượt quá 5% tổng tín chỉ chương trình, hoặc sinh viên bị kỷ luật từ mức cảnh cáo trở lên trong thời gian học. |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 5 / 5

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> Từ nhóm mình, tôi học được rằng strategy phức tạp hơn không phải lúc nào cũng tốt hơn tuyệt đối; quan trọng là strategy có khớp cấu trúc tài liệu hay không. Strategy của Thu Linh với `RecursiveChunker(300)` cho kết quả tốt nhất vì chunk nhỏ hơn và bám sát cấu trúc Điều/Khoản, dù đánh đổi bằng số chunk nhiều hơn và index chậm hơn. Strategy metadata/filter của Quang cũng cho thấy metadata schema giúp trace nguồn và giảm nhiễu khi query có phạm vi rõ.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> Từ nhóm khác, tôi học được rằng agentic chunking không quá tốt trong bài này dù nghe có vẻ thông minh hơn, vì nó có thể tốn thời gian và chưa chắc giữ được cấu trúc tài liệu ổn định. Structure chunking cho kết quả tốt hơn agentic chunking dù đơn giản hơn, vì nó tận dụng trực tiếp heading/section có sẵn trong tài liệu. Bài học chính là nên khai thác cấu trúc dữ liệu rõ ràng trước khi dùng strategy phức tạp.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> Tôi sẽ thêm metadata `article` và `section_title` vào từng chunk để filter trực tiếp theo điều khoản, ví dụ `article=26` cho câu hỏi thi hộ. Tôi cũng sẽ so sánh thêm với semantic embedding thật để kiểm tra các câu hỏi paraphrase xa hơn.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 10 / 10 |
| Chunking strategy | Nhóm | 15 / 15 |
| My approach | Cá nhân | 9 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 10 / 10 |
| Retrieval quality | Nhóm | 10 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 5 / 5 |
| **Tổng** | | **99 / 100** |
