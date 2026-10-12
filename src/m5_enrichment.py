from __future__ import annotations

"""
Module 5: Enrichment Pipeline
==============================
Làm giàu chunks TRƯỚC khi embed: Summarize, HyQA, Contextual Prepend, Auto Metadata.

Test: pytest tests/test_m5.py
"""

import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENROUTER_API_KEY, GENERATION_MODEL, create_llm_client

M5_USE_OPENAI = os.getenv("M5_USE_OPENAI", "").strip().lower() in {"1", "true", "yes"}


def _request_openai(system_prompt: str, user_prompt: str, max_tokens: int) -> str | None:
    """Make an explicitly enabled OpenRouter request; otherwise use local enrichment."""
    if not OPENROUTER_API_KEY or not M5_USE_OPENAI:
        return None

    from openai import OpenAIError

    try:
        response = create_llm_client().chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except OpenAIError as exc:
        print(f"  M5 OpenAI request failed; using local fallback: {exc}", flush=True)
        return None


def _local_summary(text: str) -> str:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
        if sentence.strip()
    ]
    return " ".join(sentences[:2]) if sentences else text.strip()


def _local_metadata(text: str) -> dict:
    lowered = text.casefold()
    category_keywords = {
        "hr": ("nhân viên", "nghỉ phép", "thử việc", "lương", "bảo hiểm"),
        "it": ("mật khẩu", "vpn", "máy tính", "phần mềm", "bảo mật"),
        "finance": ("chi phí", "tạm ứng", "tài chính", "ngân sách", "thanh toán"),
        "safety": ("an toàn", "pccc", "sơ cứu", "phòng cháy"),
    }
    category = next(
        (name for name, keywords in category_keywords.items()
         if any(keyword in lowered for keyword in keywords)),
        "general",
    )

    topic_keywords = (
        "nghỉ phép", "mật khẩu", "thử việc", "lương", "bảo hiểm",
        "tạm ứng", "chi phí", "đào tạo", "làm việc từ xa", "an toàn",
        "vpn", "đánh giá hiệu suất",
    )
    topic = next((keyword for keyword in topic_keywords if keyword in lowered), "nội dung chung")
    entities = list(dict.fromkeys(re.findall(r"\b[A-ZĐ][\wÀ-ỹ-]*(?:\s+[A-ZĐ][\wÀ-ỹ-]*)*", text)))
    return {
        "topic": topic,
        "entities": entities,
        "category": category,
        "language": "vi",
    }


def _parse_json_response(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise TypeError("Expected a JSON object from the enrichment model")
    return parsed


@dataclass
class EnrichedChunk:
    """Chunk đã được làm giàu."""
    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str  # "contextual", "summary", "hyqa", "full"


# ─── Technique 1: Chunk Summarization ────────────────────


def summarize_chunk(text: str) -> str:
    """
    Tạo summary ngắn cho chunk.
    Embed summary thay vì (hoặc cùng với) raw chunk → giảm noise.
    """
    content = _request_openai(
        "Tóm tắt đoạn văn sau trong 2-3 câu ngắn gọn bằng tiếng Việt.",
        text,
        max_tokens=150,
    )
    return content or _local_summary(text)


# ─── Technique 2: Hypothesis Question-Answer (HyQA) ─────


def generate_hypothesis_questions(text: str, n_questions: int = 3) -> list[str]:
    """
    Generate câu hỏi mà chunk có thể trả lời.
    Index cả questions lẫn chunk → query match tốt hơn (bridge vocabulary gap).
    """
    if n_questions <= 0 or not text.strip():
        return []

    content = _request_openai(
        f"Dựa trên đoạn văn, tạo {n_questions} câu hỏi mà đoạn văn có thể trả lời. "
        "Trả về mỗi câu hỏi trên một dòng.",
        text,
        max_tokens=200,
    )
    if content:
        questions = [
            re.sub(r"^\s*[\d.)\-]+\s*", "", line).strip()
            for line in content.splitlines()
            if line.strip()
        ]
        if questions:
            return questions[:n_questions]

    metadata = _local_metadata(text)
    question_by_topic = {
        "nghỉ phép": "Nhân viên được nghỉ phép bao nhiêu ngày?",
        "mật khẩu": "Mật khẩu cần thay đổi sau bao lâu?",
        "thử việc": "Thời gian thử việc là bao lâu?",
        "lương": "Thông tin nào được nêu về tiền lương?",
        "bảo hiểm": "Quy định về bảo hiểm là gì?",
        "chi phí": "Quy trình hoặc quy định về chi phí là gì?",
        "tạm ứng": "Quy định về tạm ứng là gì?",
        "đào tạo": "Thông tin nào được nêu về đào tạo?",
        "an toàn": "Quy định an toàn nào được nêu?",
        "vpn": "VPN được sử dụng như thế nào?",
    }
    primary = question_by_topic.get(metadata["topic"], "Thông tin chính trong đoạn này là gì?")
    questions = [primary]
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
        if len(sentence.strip()) > 10
    ]
    for sentence in sentences:
        candidate = f"Đoạn văn nêu thông tin gì về: {sentence.rstrip('.!?')}?"
        if candidate not in questions:
            questions.append(candidate)
        if len(questions) >= n_questions:
            break
    return questions[:n_questions]


# ─── Technique 3: Contextual Prepend (Anthropic style) ──


def contextual_prepend(text: str, document_title: str = "") -> str:
    """
    Prepend context giải thích chunk nằm ở đâu trong document.
    Anthropic benchmark: giảm 49% retrieval failure (alone).
    """
    if not text:
        return text

    content = _request_openai(
        "Viết một câu ngắn mô tả đoạn văn nằm ở đâu trong tài liệu và nói về chủ đề gì.",
        f"Tài liệu: {document_title}\n\nĐoạn văn:\n{text}",
        max_tokens=80,
    )
    if content:
        return f"{content}\n\n{text}"

    topic = _local_metadata(text)["topic"]
    location = f" trong tài liệu {document_title}" if document_title else " trong tài liệu"
    return f"Đoạn này nói về {topic}{location}.\n\n{text}"


# ─── Technique 4: Auto Metadata Extraction ──────────────


def extract_metadata(text: str) -> dict:
    """
    LLM extract metadata tự động: topic, entities, date_range, category.
    """
    content = _request_openai(
        'Trích xuất metadata từ đoạn văn, trả về JSON có dạng: '
        '{"topic":"...","entities":["..."],"category":"policy|hr|it|finance|safety|general","language":"vi|en"}.',
        text,
        max_tokens=150,
    )
    if content:
        try:
            metadata = _parse_json_response(content)
            if isinstance(metadata.get("entities"), list):
                return metadata
            raise ValueError("The metadata field 'entities' must be a list")
        except (json.JSONDecodeError, TypeError) as exc:
            print(f"  M5 metadata response was invalid; using local fallback: {exc}", flush=True)
    return _local_metadata(text)


# ─── Combined Single-Call Mode ───────────────────────────


def _enrich_single_call(text: str, source: str) -> dict:
    """Single LLM call to get summary + questions + context + metadata.

    ⚠️ Cost optimization: 1 API call thay vì 4 calls riêng lẻ.
    """
    system_prompt = """Phân tích đoạn văn và trả về JSON hợp lệ:
{
  "summary": "tóm tắt ngắn",
  "questions": ["câu hỏi có thể được trả lời từ đoạn văn"],
  "context": "một câu mô tả đoạn văn nằm ở đâu trong tài liệu và nói về chủ đề gì",
  "metadata": {"topic": "...", "entities": [], "category": "policy|hr|it|finance|safety|general", "language": "vi|en"}
}"""
    content = _request_openai(
        system_prompt,
        f"Tài liệu: {source}\n\nĐoạn văn:\n{text}",
        max_tokens=400,
    )
    if content:
        try:
            result = _parse_json_response(content)
            questions = result.get("questions")
            metadata = result.get("metadata")
            if not isinstance(questions, list) or not isinstance(metadata, dict):
                raise TypeError("Expected 'questions' list and 'metadata' object")
            result["questions"] = [str(question) for question in questions if str(question).strip()]
            return result
        except (json.JSONDecodeError, TypeError) as exc:
            print(f"  M5 combined response was invalid; using local fallback: {exc}", flush=True)

    return {
        "summary": _local_summary(text),
        "questions": generate_hypothesis_questions(text),
        "context": contextual_prepend(text, source).split("\n\n", 1)[0],
        "metadata": _local_metadata(text),
    }


# ─── Full Enrichment Pipeline ────────────────────────────


def enrich_chunks(
    chunks: list[dict],
    methods: list[str] | None = None,
) -> list[EnrichedChunk]:
    """
    Chạy enrichment pipeline trên danh sách chunks.

    Có 2 chế độ:
    - methods cụ thể (["summary"], ["contextual"]...): gọi từng function riêng (tốt cho học/debug)
    - methods=["combined"] hoặc None: combined path; makes 1 API call/chunk when M5_USE_OPENAI is enabled

    Args:
        chunks: List of {"text": str, "metadata": dict}
        methods: Default None → combined mode (1 API call/chunk only when explicitly enabled).
                 Options: "summary", "hyqa", "contextual", "metadata", "combined"
    """
    if methods is None:
        methods = ["combined"]

    use_combined = "combined" in methods

    enriched = []
    for i, chunk in enumerate(chunks):
        text = chunk["text"]
        source = chunk.get("metadata", {}).get("source", "")

        if use_combined:
            result = _enrich_single_call(text, source)
            summary = result.get("summary", "")
            questions = result.get("questions", [])
            context_line = result.get("context", "")
            enriched_text = f"{context_line}\n\n{text}" if context_line else text
            auto_meta = result.get("metadata", {})
        else:
            summary = summarize_chunk(text) if "summary" in methods else ""
            questions = generate_hypothesis_questions(text) if "hyqa" in methods else []
            enriched_text = contextual_prepend(text, source) if "contextual" in methods else text
            auto_meta = extract_metadata(text) if "metadata" in methods else {}

        enriched.append(EnrichedChunk(
            original_text=text,
            enriched_text=enriched_text,
            summary=summary,
            hypothesis_questions=questions,
            auto_metadata={**chunk.get("metadata", {}), **auto_meta},
            method="+".join(methods),
        ))

        if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
            print(f"  Enriched {i + 1}/{len(chunks)} chunks...", flush=True)

    return enriched


# ─── Main ────────────────────────────────────────────────

if __name__ == "__main__":
    sample = "Nhân viên chính thức được nghỉ phép năm 12 ngày làm việc mỗi năm. Số ngày nghỉ phép tăng thêm 1 ngày cho mỗi 5 năm thâm niên công tác."

    print("=== Enrichment Pipeline Demo ===\n")
    print(f"Original: {sample}\n")

    s = summarize_chunk(sample)
    print(f"Summary: {s}\n")

    qs = generate_hypothesis_questions(sample)
    print(f"HyQA questions: {qs}\n")

    ctx = contextual_prepend(sample, "Sổ tay nhân viên VinUni 2024")
    print(f"Contextual: {ctx}\n")

    meta = extract_metadata(sample)
    print(f"Auto metadata: {meta}")
