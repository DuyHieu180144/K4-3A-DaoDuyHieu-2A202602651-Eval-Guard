from __future__ import annotations

"""Phase A: RAGAS Production Evaluation — 50q, 3 distributions, cluster analysis."""

import json
import math
import os
import sys
from dataclasses import asdict, dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH, ANSWERS_PATH, ARTIFACTS_DIR
from src.experiment_support import write_json

Distribution = str  # "factual" | "multi_hop" | "adversarial"

DIAGNOSTIC_TREE = {
    "faithfulness":      ("LLM hallucinating", "Tighten system prompt, lower temperature"),
    "context_recall":    ("Missing relevant chunks", "Improve chunking or add BM25"),
    "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
    "answer_relevancy":  ("Answer doesn't match question", "Improve prompt template"),
}


@dataclass
class RagasResult:
    question_id: int
    distribution: Distribution
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float

    @property
    def avg_score(self) -> float:
        return (self.faithfulness + self.answer_relevancy +
                self.context_precision + self.context_recall) / 4

    @property
    def worst_metric(self) -> str:
        scores = {
            "faithfulness":      self.faithfulness,
            "answer_relevancy":  self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall":    self.context_recall,
        }
        return min(scores, key=scores.get)


# ─── Đã implement sẵn ────────────────────────────────────────────────────────

@dataclass
class RagasEvaluation:
    """Task 2 output: measured rows plus model identifiers reported by m4."""
    results: list[RagasResult]
    evaluator_models: list[str]

def load_test_set_50q(path: str = TEST_SET_PATH) -> list[dict]:
    """Load 50q test set với 3 distributions."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_answers(path: str = ANSWERS_PATH) -> list[dict]:
    """Load pre-generated answers từ setup_answers.py."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"answers_50q.json không tìm thấy tại {path}\n"
            "→ Chạy trước: python scripts/setup_answers.py --live"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict]) -> dict:
    """Provided exporter: preserve the student-produced Task 3 rows verbatim."""
    per_dist: dict[str, dict] = {}
    for dist in ["factual", "multi_hop", "adversarial"]:
        subset = [r for r in results if r.distribution == dist]
        if subset:
            per_dist[dist] = {
                "count": len(subset),
                "faithfulness":      sum(r.faithfulness for r in subset) / len(subset),
                "answer_relevancy":  sum(r.answer_relevancy for r in subset) / len(subset),
                "context_precision": sum(r.context_precision for r in subset) / len(subset),
                "context_recall":    sum(r.context_recall for r in subset) / len(subset),
                "avg_score":         sum(r.avg_score for r in subset) / len(subset),
            }

    report = {
        "total_questions": len(results),
        "per_question": [asdict(r) for r in results],
        "per_distribution": per_dist,
        "failure_clusters": clusters,
        "bottom_10": bottom,
    }
    return report


def save_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict],
                        path: str = os.path.join(ARTIFACTS_DIR, "ragas_50q.json")) -> None:
    write_json(path, build_phase_a_report(results, clusters, bottom))



# ─── Tasks 1-4: Sinh viên implement ──────────────────────────────────────────

def group_by_distribution(test_set: list[dict]) -> dict[str, list[dict]]:
    """Task 1: Nhóm 50 câu hỏi theo 3 distributions.

    Returns:
        {"factual": [...], "multi_hop": [...], "adversarial": [...]}
    """
    groups = {"factual": [], "multi_hop": [], "adversarial": []}
    for item in test_set:
        distribution = item.get("distribution")
        if distribution not in groups:
            raise ValueError(f"Unsupported test-set distribution: {distribution!r}")
        groups[distribution].append(item)
    return groups


def run_ragas_50q(answers: list[dict]) -> RagasEvaluation:
    """Task 2: Chạy RAGAS 4 metrics trên toàn bộ 50 câu hỏi.

    Gợi ý — import từ Day 18 của bạn:
        from src.m4_eval import evaluate_ragas

    Steps:
        1. Extract questions, answers, contexts, ground_truths từ answers list
        2. Gọi evaluate_ragas() từ m4_eval.py
        3. Kết hợp kết quả với distribution info từ answers list
        4. Return RagasEvaluation(results, raw["metadata"]["evaluator_models"])
           m4 must report its actual LLM/embedding models; never guess JUDGE_MODEL.
    """
    if len(answers) != 50:
        raise ValueError(f"Phase A requires exactly 50 answers; received {len(answers)}")

    from src.m4_eval import evaluate_ragas

    raw = evaluate_ragas(
        [answer["question"] for answer in answers],
        [answer["answer"] for answer in answers],
        [answer["contexts"] for answer in answers],
        [answer["ground_truth"] for answer in answers],
    )
    if not isinstance(raw, dict) or raw.get("evaluation_status") != "evaluated":
        status = raw.get("evaluation_status") if isinstance(raw, dict) else None
        raise ValueError(f"RAGAS evaluation did not complete successfully (status={status!r})")

    metadata = raw.get("metadata")
    evaluator_models = metadata.get("evaluator_models") if isinstance(metadata, dict) else None
    if (not isinstance(evaluator_models, list) or not evaluator_models
            or any(not isinstance(model, str) or not model.strip() for model in evaluator_models)):
        raise ValueError("RAGAS must report non-empty evaluator model identifiers")

    per_question = raw.get("per_question")
    if not isinstance(per_question, list) or len(per_question) != len(answers):
        actual = len(per_question) if isinstance(per_question, list) else "non-list"
        raise ValueError(f"RAGAS returned {actual} rows for {len(answers)} answers")

    results = []
    for answer, measured in zip(answers, per_question):
        scores = {}
        for metric in DIAGNOSTIC_TREE:
            value = measured.get(metric) if isinstance(measured, dict) else getattr(measured, metric, None)
            try:
                score = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"RAGAS returned a non-numeric {metric} score") from exc
            if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                raise ValueError(f"RAGAS returned an invalid {metric} score: {score!r}")
            scores[metric] = score
        results.append(RagasResult(
            question_id=answer["id"],
            distribution=answer["distribution"],
            question=answer["question"],
            answer=answer["answer"],
            contexts=answer["contexts"],
            ground_truth=answer["ground_truth"],
            **scores,
        ))
    return RagasEvaluation(results, list(evaluator_models))


def bottom_10(results: list[RagasResult]) -> list[dict]:
    """Task 3: Lấy 10 câu hỏi có avg_score thấp nhất.

    Returns:
        [{"rank": 1, "question_id": ..., "distribution": ...,
          "question": ..., "avg_score": ..., "worst_metric": ...,
          "diagnosis": ..., "suggested_fix": ...}, ...]
    """
    ordered = sorted(results, key=lambda result: result.avg_score)[:10]
    output = []
    for rank, result in enumerate(ordered, start=1):
        diagnosis, suggested_fix = DIAGNOSTIC_TREE[result.worst_metric]
        output.append({
            "rank": rank,
            "question_id": result.question_id,
            "distribution": result.distribution,
            "question": result.question,
            "avg_score": round(result.avg_score, 4),
            "worst_metric": result.worst_metric,
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })
    return output


def cluster_analysis(results: list[RagasResult]) -> dict:
    """Task 4: Phân tích failure clusters theo (worst_metric × distribution).

    Matrix thống kê worst_metric của mọi câu, không coi mọi câu là một failure.
    Nhóm yếu nhất = distribution có avg_score trung bình thấp nhất (bỏ nhóm rỗng).
    Tổng matrix theo cột chỉ là kích thước nhóm 20/20/10, không đo chất lượng.

    Returns:
        {
          "matrix": {
            "faithfulness":      {"factual": 3, "multi_hop": 5, "adversarial": 2},
            "answer_relevancy":  {...},
            "context_precision": {...},
            "context_recall":    {...},
          },
          "dominant_failure_distribution": "multi_hop",
          "dominant_failure_metric": "context_recall",
          "insight": "..."
        }
    """
    if not results:
        raise ValueError("Cannot analyze empty Phase A results")

    distributions = ("factual", "multi_hop", "adversarial")
    matrix = {
        metric: {distribution: 0 for distribution in distributions}
        for metric in DIAGNOSTIC_TREE
    }
    grouped_scores = {distribution: [] for distribution in distributions}
    for result in results:
        if result.distribution not in grouped_scores:
            raise ValueError(f"Unsupported result distribution: {result.distribution!r}")
        if result.worst_metric not in matrix:
            raise ValueError(f"Unsupported worst metric: {result.worst_metric!r}")
        matrix[result.worst_metric][result.distribution] += 1
        grouped_scores[result.distribution].append(result.avg_score)

    distribution_avg_scores = {
        distribution: sum(scores) / len(scores)
        for distribution, scores in grouped_scores.items()
        if scores
    }
    dominant_distribution = min(distribution_avg_scores, key=distribution_avg_scores.get)
    metric_counts = {metric: sum(counts.values()) for metric, counts in matrix.items()}
    dominant_metric = max(metric_counts, key=metric_counts.get)
    insight = (
        f"{dominant_distribution} has the lowest mean average score "
        f"({distribution_avg_scores[dominant_distribution]:.3f}); "
        f"{dominant_metric} is the most frequent worst metric ({metric_counts[dominant_metric]} questions)."
    )
    return {
        "matrix": matrix,
        "distribution_avg_scores": distribution_avg_scores,
        "dominant_failure_distribution": dominant_distribution,
        "dominant_failure_metric": dominant_metric,
        "insight": insight,
    }
# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "a", *sys.argv[1:]]))
