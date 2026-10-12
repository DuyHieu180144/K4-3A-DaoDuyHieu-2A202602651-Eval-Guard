from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import json
import math
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (EMBEDDING_MODEL, GENERATION_MODEL, OPENROUTER_API_KEY,
                    OPENAI_API_BASE, TEST_SET_PATH)

METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)

DIAGNOSTIC_TREE = {
    "faithfulness": (
        "Answer có thể chứa nội dung không được hỗ trợ bởi context.",
        "Siết prompt chỉ trả lời theo context và giảm temperature.",
    ),
    "context_recall": (
        "Context truy xuất có thể thiếu thông tin cần thiết.",
        "Cải thiện chunking, query matching hoặc bổ sung BM25.",
    ),
    "context_precision": (
        "Context truy xuất có thể chứa quá nhiều chunk không liên quan.",
        "Cải thiện reranking hoặc lọc theo metadata.",
    ),
    "answer_relevancy": (
        "Answer có thể chưa trả lời trực tiếp câu hỏi.",
        "Cải thiện prompt sinh câu trả lời và yêu cầu bám sát câu hỏi.",
    ),
}


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    input_lengths = {len(questions), len(answers), len(contexts), len(ground_truths)}
    if len(input_lengths) != 1:
        raise ValueError("questions, answers, contexts, and ground_truths must have equal lengths")

    def empty_result(status: str, evaluator_models: list[str] | None = None) -> dict:
        per_question = [
            EvalResult(
                question=question,
                answer=answer,
                contexts=question_contexts,
                ground_truth=ground_truth,
                faithfulness=0.0,
                answer_relevancy=0.0,
                context_precision=0.0,
                context_recall=0.0,
            )
            for question, answer, question_contexts, ground_truth
            in zip(questions, answers, contexts, ground_truths)
        ]
        return {
            **dict.fromkeys(METRIC_NAMES, 0.0),
            "per_question": per_question,
            "evaluation_status": status,
            "metadata": {"evaluator_models": evaluator_models or []},
        }

    if not questions:
        print("  RAGAS evaluation skipped: no questions were provided.", flush=True)
        return empty_result("skipped_empty_input")
    if not OPENROUTER_API_KEY:
        print("  RAGAS evaluation unavailable: OPENROUTER_API_KEY is not configured.", flush=True)
        return empty_result("skipped_no_api_key")

    evaluator_models = []
    try:
        import pandas as pd
        from datasets import Dataset
        from ragas import evaluate
        from ragas.embeddings import HuggingfaceEmbeddings
        from ragas.llms import llm_factory
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })
        evaluator_llm = llm_factory(model=GENERATION_MODEL, base_url=OPENAI_API_BASE)
        wrapped_llm = getattr(evaluator_llm, "langchain_llm", evaluator_llm)
        llm_model_id = (
            getattr(wrapped_llm, "model_name", None)
            or getattr(wrapped_llm, "model", None)
            or GENERATION_MODEL
        )
        evaluator_embeddings = HuggingfaceEmbeddings(model_name=EMBEDDING_MODEL)
        embedding_model_id = getattr(evaluator_embeddings, "model_name", EMBEDDING_MODEL)
        evaluator_models = [llm_model_id, embedding_model_id]

        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )
        dataframe = result.to_pandas()
        if len(dataframe) != len(questions):
            raise ValueError(
                f"RAGAS returned {len(dataframe)} rows for {len(questions)} questions"
            )

        per_question = []
        for index, row in dataframe.iterrows():
            metric_scores = {}
            for metric in METRIC_NAMES:
                value = pd.to_numeric(row.get(metric), errors="coerce")
                if pd.isna(value):
                    raise ValueError(f"RAGAS returned a non-numeric {metric} score at row {index}")
                score = float(value)
                if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                    raise ValueError(f"RAGAS returned an invalid {metric} score at row {index}")
                metric_scores[metric] = score
            per_question.append(
                EvalResult(
                    question=questions[index],
                    answer=answers[index],
                    contexts=contexts[index],
                    ground_truth=ground_truths[index],
                    **metric_scores,
                )
            )

        aggregate = {
            metric: sum(getattr(row, metric) for row in per_question) / len(per_question)
            for metric in METRIC_NAMES
        }
        return {
            **aggregate,
            "per_question": per_question,
            "evaluation_status": "evaluated",
            "metadata": {"evaluator_models": evaluator_models},
        }
    except Exception as exc:  # noqa: BLE001 - RAGAS/provider failures vary by backend.
        print(f"  RAGAS evaluation failed; returning zero scores: {exc}", flush=True)
        return empty_result("failed", evaluator_models)


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    if bottom_n <= 0:
        return []

    failures = []
    for result in eval_results:
        metric_scores = {
            metric: float(getattr(result, metric))
            for metric in METRIC_NAMES
        }
        worst_metric = min(metric_scores, key=metric_scores.get)
        diagnosis, suggested_fix = DIAGNOSTIC_TREE[worst_metric]
        failures.append({
            "question": result.question,
            "answer": result.answer,
            "contexts": result.contexts,
            "ground_truth": result.ground_truth,
            "average_score": sum(metric_scores.values()) / len(METRIC_NAMES),
            "worst_metric": worst_metric,
            "worst_metric_score": metric_scores[worst_metric],
            "metrics": metric_scores,
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })

    failures.sort(key=lambda failure: failure["average_score"])
    return failures[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
