from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        question = question.strip()
        if not question:
            return "Please provide a question."

        results = self.store.search(question, top_k=top_k)
        if not results:
            return "I could not find relevant context in the knowledge base."

        context = "\n\n".join(
            f"[{index}] {result['content']}" for index, result in enumerate(results, start=1)
        )
        prompt = (
            "Answer the question using only the context below.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        try:
            answer = self.llm_fn(prompt)
        except Exception as exc:
            return f"Unable to generate answer: {exc}"
        return str(answer).strip() or "No answer generated."
