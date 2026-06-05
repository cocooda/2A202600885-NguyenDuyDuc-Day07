from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from pathlib import Path
from typing import Iterable

from .chunking import RecursiveChunker
from .models import Document


ACADEMIC_POLICY_FILES = [
    ("data/quy_che_dao_tao.md", {"category": "academics", "chapter": "I"}),
    ("data/dang_ky_hoc_phan.md", {"category": "registration", "chapter": "II"}),
    ("data/danh_gia_ket_qua_hoc_tap.md", {"category": "assessment", "chapter": "III"}),
    ("data/tot_nghiep_va_bang_cap.md", {"category": "graduation", "chapter": "III"}),
    ("data/nghi_hoc_chuyen_nganh.md", {"category": "transfer", "chapter": "IV"}),
    ("data/ky_luat_sinh_vien.md", {"category": "discipline", "chapter": "IV"}),
]


class ArticleSectionChunker:
    """Chunk Vietnamese academic policy docs by markdown article and subsection."""

    def __init__(self, max_chars: int = 1400) -> None:
        self.max_chars = max(300, max_chars)

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []

        chunks: list[str] = []
        body_lines: list[str] = []
        doc_title = ""
        chapter_title = ""
        article_title = ""
        section_title = ""

        def flush_body() -> None:
            nonlocal body_lines
            body = "\n".join(body_lines).strip()
            body_lines = []
            if not body:
                return
            headings = _dedupe([doc_title, chapter_title, article_title, section_title])
            prefix = "\n".join(headings)
            chunks.extend(self._pack_with_prefix(prefix, body))

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                flush_body()
                level = len(stripped) - len(stripped.lstrip("#"))
                title = stripped[level:].strip()
                normalized = _normalize(title)

                if level == 1:
                    doc_title = title
                    chapter_title = ""
                    article_title = ""
                    section_title = ""
                elif level == 2 and normalized.startswith("dieu "):
                    article_title = title
                    section_title = ""
                elif level == 2:
                    chapter_title = title
                    article_title = ""
                    section_title = ""
                else:
                    section_title = title
                continue

            body_lines.append(line.rstrip())

        flush_body()
        if chunks:
            return chunks
        return RecursiveChunker(chunk_size=self.max_chars).chunk(text)

    def _pack_with_prefix(self, prefix: str, body: str) -> list[str]:
        header = f"{prefix}\n\n" if prefix else ""
        if len(header) + len(body) <= self.max_chars:
            return [f"{header}{body}".strip()]

        budget = max(200, self.max_chars - len(header))
        parts = _split_paragraphs(body)
        packed: list[str] = []
        current = ""

        for part in parts:
            candidate = f"{current}\n\n{part}".strip() if current else part
            if len(candidate) <= budget:
                current = candidate
                continue

            if current:
                packed.append(current)
                current = ""

            if len(part) <= budget:
                current = part
            else:
                packed.extend(RecursiveChunker(chunk_size=budget).chunk(part))

        if current:
            packed.append(current)

        # Critical for retrieval: repeat article context on every split section.
        return [f"{header}{part}".strip() for part in packed if part.strip()]


class VietnameseTextEmbedder:
    """Dependency-free lexical embedder tuned for Vietnamese policy retrieval."""

    STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "ai",
        "bi",
        "boi",
        "cac",
        "cho",
        "co",
        "con",
        "cua",
        "duoc",
        "de",
        "den",
        "hoac",
        "khi",
        "khong",
        "la",
        "mot",
        "nao",
        "neu",
        "nhu",
        "nhung",
        "phai",
        "the",
        "theo",
        "thi",
        "trong",
        "tu",
        "va",
        "ve",
    }

    def __init__(self, dim: int = 512) -> None:
        self.dim = max(64, dim)
        self._backend_name = "vietnamese lexical hashing"

    def __call__(self, text: str) -> list[float]:
        tokens = [token for token in _tokens(text) if token not in self.STOPWORDS]
        if not tokens:
            return [0.0] * self.dim

        vector = [0.0] * self.dim
        for term, weight in self._weighted_terms(tokens):
            digest = hashlib.md5(term.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            vector[index] += weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

    def _weighted_terms(self, tokens: list[str]) -> Iterable[tuple[str, float]]:
        for token in tokens:
            yield token, 1.0
        for size, weight in ((2, 1.7), (3, 2.2)):
            for index in range(0, len(tokens) - size + 1):
                yield "_".join(tokens[index : index + size]), weight


def build_academic_policy_documents(
    base_dir: str | Path = ".",
    chunker: ArticleSectionChunker | None = None,
) -> list[Document]:
    chunker = chunker or ArticleSectionChunker()
    root = Path(base_dir)
    docs: list[Document] = []

    for raw_path, base_metadata in ACADEMIC_POLICY_FILES:
        path = root / raw_path
        text = path.read_text(encoding="utf-8")
        file_id = path.stem
        for index, chunk in enumerate(chunker.chunk(text)):
            metadata = dict(base_metadata)
            metadata.update(
                {
                    "source": raw_path,
                    "file_id": file_id,
                    "chunk_index": index,
                    "language": "vi",
                }
            )
            docs.append(Document(id=f"{file_id}_chunk{index}", content=chunk, metadata=metadata))
    return docs


def _normalize(text: str) -> str:
    text = text.lower().replace("đ", "d")
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _normalize(text))


def _split_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
