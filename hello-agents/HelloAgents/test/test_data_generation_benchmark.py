import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.benchmarks.data_generation import AIDataset, LLMJudgeEvaluator, WinRateEvaluator


def quiet_call(func, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.messages = []

    def invoke(self, messages):
        self.messages.append(messages)
        if not self.responses:
            return "{}"
        return self.responses.pop(0)


class AIDatasetTest(unittest.TestCase):
    def test_load_generated_data_normalizes_supported_field_names(self):
        rows = [
            {
                "id": "gen-1",
                "question": "Find x.",
                "answer": 42,
                "reasoning": "Solve for x.",
                "difficulty": 7,
                "category": "Algebra",
            },
            {
                "problem": "Count paths.",
                "answer": "12",
                "solution": "Use cases.",
                "topic": "Combinatorics",
            },
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            data_path = Path(tempdir) / "generated.json"
            write_json(data_path, rows)
            dataset = AIDataset(dataset_type="generated", data_path=str(data_path))
            problems = quiet_call(dataset.load)

        self.assertEqual(len(problems), 2)
        self.assertEqual(problems[0], {
            "problem_id": "gen-1",
            "problem": "Find x.",
            "answer": 42,
            "solution": "Solve for x.",
            "difficulty": 7,
            "topic": "Algebra",
        })
        self.assertEqual(problems[1]["problem_id"], "gen_1")
        self.assertEqual(problems[1]["topic"], "Combinatorics")
        self.assertEqual(dataset.get_problem("gen-1")["answer"], 42)
        self.assertEqual([p["problem_id"] for p in dataset.get_problems_by_topic("Algebra")], ["gen-1"])
        self.assertEqual([p["problem_id"] for p in dataset.get_problems_by_difficulty(6, 8)], ["gen-1"])
        self.assertEqual(len(dataset), 2)
        self.assertEqual(dataset[0]["problem_id"], "gen-1")

    def test_generated_dataset_validates_required_path(self):
        with self.assertRaises(ValueError):
            AIDataset(dataset_type="generated").load()

        with self.assertRaises(FileNotFoundError):
            AIDataset(dataset_type="generated", data_path="/tmp/not-a-real-aime-file.json").load()

    def test_load_real_data_uses_snapshot_download_and_normalizes_jsonl(self):
        with tempfile.TemporaryDirectory() as tempdir:
            local_dir = Path(tempdir) / "hf_snapshot"
            write_jsonl(local_dir / "aime25.jsonl", [
                {"id": "aime_2025_i_1", "problem": "Real problem", "answer": "314"},
                {"problem": "No id problem", "answer": "271", "difficulty": 8, "topic": "Number Theory"},
            ])

            with patch(
                    "evaluation.benchmarks.data_generation.dataset.snapshot_download",
                    return_value=str(local_dir),
            ) as snapshot:
                dataset = AIDataset(dataset_type="real", year=2025, cache_dir=str(Path(tempdir) / "cache"))
                problems = quiet_call(dataset.load)

        snapshot.assert_called_once_with(
            repo_id="math-ai/aime25",
            repo_type="dataset",
            cache_dir=str(Path(tempdir) / "cache"),
        )
        self.assertEqual(len(problems), 2)
        self.assertEqual(problems[0]["problem_id"], "aime_2025_i_1")
        self.assertEqual(problems[0]["solution"], "")
        self.assertEqual(problems[1]["problem_id"], "aime_2025_1")
        self.assertEqual(problems[1]["topic"], "Number Theory")

    def test_real_dataset_requires_year_and_unknown_type_is_rejected(self):
        with self.assertRaises(ValueError):
            AIDataset(dataset_type="real").load()

        with self.assertRaises(ValueError):
            AIDataset(dataset_type="other").load()


class LLMJudgeEvaluatorTest(unittest.TestCase):
    def test_prompt_contains_problem_reference_and_scoring_dimensions(self):
        evaluator = LLMJudgeEvaluator(llm=FakeLLM([]), judge_model="unit-judge")
        prompt = evaluator._build_evaluation_prompt(
            {"problem": "Generated?", "answer": 1, "solution": "Generated solution"},
            {"problem": "Reference?", "answer": 2, "solution": "Reference solution"},
        )

        self.assertIn("待评估题目", prompt)
        self.assertIn("参考题目", prompt)
        self.assertIn("正确性", prompt)
        self.assertIn("difficulty_match", prompt)

    def test_parse_evaluation_response_supports_code_fences_and_defaults(self):
        evaluator = LLMJudgeEvaluator(llm=FakeLLM([]))
        scores = evaluator._parse_evaluation_response(
            '```json\n{"correctness": 5, "clarity": 4, "difficulty_match": 3.5, "completeness": 4}\n```'
        )
        fallback = quiet_call(evaluator._parse_evaluation_response, "not json")

        self.assertEqual(scores, {
            "correctness": 5.0,
            "clarity": 4.0,
            "difficulty_match": 3.5,
            "completeness": 4.0,
        })
        self.assertEqual(fallback, {dim: 3.0 for dim in evaluator.EVALUATION_DIMENSIONS})

    def test_evaluate_single_and_batch_compute_documented_metrics(self):
        llm = FakeLLM([
            '{"correctness": 5, "clarity": 4, "difficulty_match": 4, "completeness": 5, "comments": "good"}',
            '{"correctness": 3, "clarity": 3, "difficulty_match": 3, "completeness": 3, "comments": "ok"}',
        ])
        evaluator = LLMJudgeEvaluator(llm=llm, judge_model="fake-judge")
        problems = [
            {"problem_id": "p1", "problem": "Problem 1", "answer": 1, "solution": "Solution 1"},
            {"problem_id": "p2", "problem": "Problem 2", "answer": 2, "solution": "Solution 2"},
        ]

        results = quiet_call(evaluator.evaluate_batch, problems)

        self.assertEqual(results["judge_model"], "fake-judge")
        self.assertEqual(results["num_problems"], 2)
        self.assertEqual(len(results["results"]), 2)
        self.assertEqual(results["results"][0]["total_score"], 4.5)
        self.assertEqual(results["metrics"]["average_total_score"], 3.75)
        self.assertEqual(results["metrics"]["pass_rate"], 0.5)
        self.assertEqual(results["metrics"]["excellent_rate"], 0.5)
        self.assertEqual(results["metrics"]["dimension_averages"]["correctness"], 4.0)
        self.assertEqual(len(llm.messages), 2)

    def test_export_results_writes_json_file(self):
        evaluator = LLMJudgeEvaluator(llm=FakeLLM([]))
        results = {"metrics": {"average_total_score": 4.2}, "results": []}

        with tempfile.TemporaryDirectory() as tempdir:
            output_path = Path(tempdir) / "judge.json"
            quiet_call(evaluator.export_results, results, str(output_path))
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(saved, results)


class WinRateEvaluatorTest(unittest.TestCase):
    def test_comparison_prompt_changes_when_solutions_are_missing(self):
        evaluator = WinRateEvaluator(llm=FakeLLM([]), judge_model="unit-judge")
        with_solution = evaluator._build_comparison_prompt(
            {"problem": "A", "answer": 1, "solution": "SA"},
            {"problem": "B", "answer": 2, "solution": "SB"},
            "Problem A",
            "Problem B",
        )
        without_solution = evaluator._build_comparison_prompt(
            {"problem": "A", "answer": 1},
            {"problem": "B", "answer": 2},
            "Problem A",
            "Problem B",
        )

        self.assertIn("Solution Completeness", with_solution)
        self.assertIn("Problem Quality", without_solution)
        self.assertIn('"winner": "Problem A"', with_solution)

    def test_parse_comparison_response_supports_fences_latex_and_invalid_winners(self):
        evaluator = WinRateEvaluator(llm=FakeLLM([]))
        winner, reason = evaluator._parse_comparison_response(
            '```json\n{"winner": "Problem A", "reason": "Uses \\frac{1}{2}."}\n```',
            "Problem A",
            "Problem B",
        )
        invalid_winner, invalid_reason = evaluator._parse_comparison_response(
            '{"winner": "Neither", "reason": "bad label"}',
            "Problem A",
            "Problem B",
        )
        fallback_winner, fallback_reason = quiet_call(
            evaluator._parse_comparison_response,
            "not json",
            "Problem A",
            "Problem B",
        )

        self.assertEqual((winner, reason), ("Problem A", "Uses \\frac{1}{2}."))
        self.assertEqual((invalid_winner, invalid_reason), ("Tie", "bad label"))
        self.assertEqual((fallback_winner, fallback_reason), ("Tie", "Failed to parse response"))

    def test_compare_pair_calls_llm_and_returns_structured_result(self):
        llm = FakeLLM(['{"winner": "Problem B", "reason": "Clearer."}'])
        evaluator = WinRateEvaluator(llm=llm, judge_model="fake-judge")

        result = evaluator.compare_pair(
            {"problem_id": "a", "problem": "A", "answer": 1},
            {"problem_id": "b", "problem": "B", "answer": 2},
            label_a="Problem A",
            label_b="Problem B",
        )

        self.assertEqual(result["problem_a_id"], "a")
        self.assertEqual(result["problem_b_id"], "b")
        self.assertEqual(result["winner"], "Problem B")
        self.assertEqual(result["reason"], "Clearer.")
        self.assertEqual(len(llm.messages), 1)

    def test_evaluate_win_rate_computes_win_loss_tie_rates_with_fixed_randomness(self):
        generated = [
            {"problem_id": "gen1", "problem": "G1", "answer": 1},
            {"problem_id": "gen2", "problem": "G2", "answer": 2},
            {"problem_id": "gen3", "problem": "G3", "answer": 3},
        ]
        reference = [
            {"problem_id": "ref1", "problem": "R1", "answer": 4},
            {"problem_id": "ref2", "problem": "R2", "answer": 5},
        ]
        llm = FakeLLM([
            '{"winner": "Problem A", "reason": "generated wins"}',
            '{"winner": "Problem A", "reason": "reference wins"}',
            '{"winner": "Tie", "reason": "same quality"}',
        ])
        evaluator = WinRateEvaluator(llm=llm, judge_model="fake-judge")

        with patch("random.sample", return_value=[0, 1, 2]), \
                patch("random.randint", side_effect=[0, 1, 0]), \
                patch("random.random", side_effect=[0.1, 0.9, 0.1]):
            results = quiet_call(evaluator.evaluate_win_rate, generated, reference, num_comparisons=3)

        self.assertEqual(results["metrics"], {
            "win_rate": 1 / 3,
            "loss_rate": 1 / 3,
            "tie_rate": 1 / 3,
            "wins": 1,
            "losses": 1,
            "ties": 1,
            "total_comparisons": 3,
        })
        self.assertEqual([c["actual_winner"] for c in results["comparisons"]], [
            "Generated",
            "Reference",
            "Tie",
        ])
        self.assertEqual(results["comparisons"][1]["actual_order"], {"A": "Reference", "B": "Generated"})

    def test_evaluate_win_rate_handles_zero_comparisons_and_export(self):
        evaluator = WinRateEvaluator(llm=FakeLLM([]), judge_model="fake-judge")
        results = quiet_call(
            evaluator.evaluate_win_rate,
            [{"problem_id": "g", "problem": "G"}],
            [{"problem_id": "r", "problem": "R"}],
            num_comparisons=0,
        )

        self.assertEqual(results["metrics"]["total_comparisons"], 0)
        self.assertEqual(results["metrics"]["win_rate"], 0)

        with tempfile.TemporaryDirectory() as tempdir:
            output_path = Path(tempdir) / "win_rate.json"
            quiet_call(evaluator.export_results, results, str(output_path))
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(saved["metrics"], results["metrics"])


if __name__ == "__main__":
    unittest.main()
