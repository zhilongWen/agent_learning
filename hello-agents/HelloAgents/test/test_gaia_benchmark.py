import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.benchmarks.gaia import GAIADataset, GAIAEvaluator, GAIAMetrics


def log(message):
    print(f"\n[GAIA_TEST] {message}")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def empty_local_dataset():
    data_dir = Path(tempfile.mkdtemp(prefix="gaia_empty_"))
    return GAIADataset(local_data_dir=data_dir)


class ScriptedGAIAAgent:
    def __init__(self, responses):
        self.name = "ScriptedGAIAAgent"
        self.responses = list(responses)
        self.prompts = []

    def run(self, prompt):
        self.prompts.append(prompt)
        if not self.responses:
            return "FINAL ANSWER: unknown"
        return self.responses.pop(0)


class GAIADatasetTest(unittest.TestCase):
    def make_local_dir(self):
        tempdir = tempfile.TemporaryDirectory()
        data_dir = Path(tempdir.name)
        rows = [
            {
                "task_id": "task-level-1",
                "Question": "What is 2 + 2?",
                "Level": 1,
                "Final answer": "4",
                "file_name": "",
                "Annotator Metadata": {"Number of steps": 1, "Tools": ["calculator"]},
                "Steps": 1,
                "Tools": ["calculator"],
            },
            {
                "task_id": "task-level-2",
                "question": "Name the capital of France.",
                "level": 2,
                "final_answer": "Paris",
                "file_name": "attachment.csv",
                "file_path": "attachment.csv",
                "steps": 3,
                "tools": ["search"],
            },
            {
                "task_id": "task-level-3",
                "Question": "List three cities.",
                "Level": 3,
                "Final answer": "Berlin, London, Paris",
                "steps": 6,
            },
        ]
        write_json(data_dir / "gaia_fixture.json", rows)
        return tempdir, data_dir, rows

    def test_local_load_standardizes_items_filters_level_and_reports_statistics(self):
        log("dataset: local JSON load, standardization, level filtering, statistics")
        tempdir, data_dir, _ = self.make_local_dir()
        self.addCleanup(tempdir.cleanup)

        dataset = GAIADataset(level=2, split="validation", local_data_dir=data_dir)
        items = dataset.load()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["task_id"], "task-level-2")
        self.assertEqual(items[0]["question"], "Name the capital of France.")
        self.assertEqual(items[0]["level"], 2)
        self.assertEqual(items[0]["final_answer"], "Paris")
        self.assertEqual(items[0]["tools"], ["search"])
        self.assertIn("raw_item", items[0])
        self.assertEqual(dataset.get_sample(0)["task_id"], "task-level-2")
        self.assertEqual(dataset.get_by_level(2)[0]["task_id"], "task-level-2")
        self.assertEqual(dataset.get_level_distribution(), {1: 0, 2: 1, 3: 0})
        stats = dataset.get_statistics()
        self.assertEqual(stats["total_samples"], 1)
        self.assertEqual(stats["samples_with_files"], 1)
        self.assertEqual(stats["average_steps"], 3.0)
        self.assertEqual(len(dataset), 1)

    def test_local_loader_handles_single_json_object_and_ignores_non_gaia_files(self):
        log("dataset: single object JSON and gaia filename filtering")
        with tempfile.TemporaryDirectory() as tempdir:
            data_dir = Path(tempdir)
            write_json(data_dir / "not_related.json", {"task_id": "ignored"})
            write_json(data_dir / "gaia_single.json", {
                "task_id": "single",
                "Question": "Single question?",
                "Level": 1,
                "Final answer": "yes",
            })

            dataset = GAIADataset(local_data_dir=data_dir)
            items = dataset.load()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["task_id"], "single")

    def test_huggingface_loader_uses_token_skips_placeholder_and_rewrites_file_path(self):
        log("dataset: mocked HuggingFace snapshot_download path")
        with tempfile.TemporaryDirectory() as tempdir:
            local_dir = Path(tempdir) / "gaia_snapshot"
            metadata_file = local_dir / "2023" / "validation" / "metadata.jsonl"
            write_jsonl(metadata_file, [
                {"task_id": "0-0-0-0-0", "Question": "placeholder"},
                {
                    "task_id": "hf-task",
                    "Question": "Read the file.",
                    "Level": 1,
                    "Final answer": "done",
                    "file_name": "table.csv",
                },
            ])

            with patch.dict("os.environ", {"HF_TOKEN": "hf_test"}, clear=False), \
                 patch(
                     "huggingface_hub.snapshot_download",
                     return_value=str(local_dir),
                 ) as snapshot:
                dataset = GAIADataset(dataset_name="gaia-benchmark/GAIA", split="validation")
                items = dataset.load()

        snapshot.assert_called_once()
        self.assertNotIn("local_dir_use_symlinks", snapshot.call_args.kwargs)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["task_id"], "hf-task")
        self.assertTrue(items[0]["file_name"].endswith("2023/validation/table.csv"))

    def test_huggingface_loader_handles_gated_repo_403_as_empty_dataset(self):
        log("dataset: gated GAIA repo 403 returns empty list")
        with patch.dict("os.environ", {"HF_TOKEN": "hf_without_access"}, clear=False), \
             patch(
                 "huggingface_hub.snapshot_download",
                 side_effect=Exception("403 Client Error: Cannot access gated repo; restricted"),
             ):
            dataset = GAIADataset()
            self.assertEqual(dataset.load(), [])

    def test_huggingface_loader_without_token_returns_empty_list(self):
        log("dataset: missing HF_TOKEN returns empty list")
        with patch.dict("os.environ", {}, clear=True):
            dataset = GAIADataset()
            self.assertEqual(dataset.load(), [])


class GAIAEvaluatorTest(unittest.TestCase):
    def make_dataset(self):
        tempdir = tempfile.TemporaryDirectory()
        data_dir = Path(tempdir.name)
        rows = [
            {"task_id": "l1", "Question": "What is 2 + 2?", "Level": 1, "Final answer": "4"},
            {"task_id": "l2", "Question": "Capital of France?", "Level": 2, "Final answer": "Paris"},
            {"task_id": "l3", "Question": "List cities", "Level": 3, "Final answer": "Berlin, London, Paris"},
        ]
        write_json(data_dir / "gaia_eval.json", rows)
        dataset = GAIADataset(local_data_dir=data_dir)
        return tempdir, dataset

    def test_extract_answer_supports_gaia_format_fallback_markers_and_last_line(self):
        log("evaluator: FINAL ANSWER extraction and fallback markers")
        evaluator = GAIAEvaluator(dataset=empty_local_dataset())

        self.assertEqual(evaluator._extract_answer("Reasoning\nFINAL ANSWER: [42]"), "42")
        self.assertEqual(evaluator._extract_answer("最终答案：巴黎"), "巴黎")
        self.assertEqual(evaluator._extract_answer("Answer: London"), "London")
        self.assertEqual(evaluator._extract_answer("# scratch\nlast non-empty line"), "last non-empty line")

    def test_normalization_matches_gaia_rules_for_numbers_strings_and_lists(self):
        log("evaluator: quasi exact normalization for number/string/list answers")
        evaluator = GAIAEvaluator(dataset=empty_local_dataset())

        self.assertEqual(evaluator._normalize_answer("$1,234.56%"), "1234.56")
        self.assertEqual(evaluator._normalize_answer("The United States."), "united states")
        self.assertEqual(evaluator._normalize_answer("Paris, London, Berlin"), "berlin,london,paris")
        self.assertTrue(evaluator._check_exact_match("The Apple.", "apple"))
        self.assertTrue(evaluator._check_partial_match("capital city paris france", "Paris France"))
        self.assertFalse(evaluator._check_partial_match("Berlin", "Paris France"))

    def test_build_prompt_mentions_attachments(self):
        log("evaluator: prompt includes attachment hint")
        evaluator = GAIAEvaluator(dataset=empty_local_dataset())
        prompt = evaluator._build_prompt("Question?", {"file_name": "/tmp/table.csv"})

        self.assertIn("Question?", prompt)
        self.assertIn("/tmp/table.csv", prompt)

    def test_evaluate_sample_scores_exact_partial_and_wrong_answers(self):
        log("evaluator: evaluate_sample scoring exact/partial/wrong")
        evaluator = GAIAEvaluator(dataset=empty_local_dataset())

        exact = evaluator.evaluate_sample(
            ScriptedGAIAAgent(["Thinking...\nFINAL ANSWER: [4]"]),
            {"task_id": "exact", "question": "2+2", "final_answer": "4", "level": 1},
        )
        partial = evaluator.evaluate_sample(
            ScriptedGAIAAgent(["FINAL ANSWER: capital city paris france"]),
            {"task_id": "partial", "question": "capital", "final_answer": "Paris France", "level": 2},
        )
        wrong = evaluator.evaluate_sample(
            ScriptedGAIAAgent(["FINAL ANSWER: Berlin"]),
            {"task_id": "wrong", "question": "capital", "final_answer": "Paris", "level": 3},
        )

        self.assertTrue(exact["exact_match"])
        self.assertTrue(exact["partial_match"])
        self.assertEqual(exact["score"], 1.0)
        self.assertFalse(partial["exact_match"])
        self.assertTrue(partial["partial_match"])
        self.assertEqual(partial["score"], 0.5)
        self.assertFalse(wrong["partial_match"])
        self.assertEqual(wrong["score"], 0.0)

    def test_evaluate_computes_overall_and_level_metrics(self):
        log("evaluator: end-to-end evaluate over local fixture")
        tempdir, dataset = self.make_dataset()
        self.addCleanup(tempdir.cleanup)
        evaluator = GAIAEvaluator(dataset=dataset)
        agent = ScriptedGAIAAgent([
            "FINAL ANSWER: 4",
            "FINAL ANSWER: capital city paris france",
            "FINAL ANSWER: Madrid",
        ])

        results = evaluator.evaluate(agent, max_samples=3)

        self.assertEqual(results["benchmark"], "GAIA")
        self.assertEqual(results["agent_name"], "ScriptedGAIAAgent")
        self.assertEqual(results["total_samples"], 3)
        self.assertEqual(results["exact_matches"], 1)
        self.assertEqual(results["partial_matches"], 2)
        self.assertEqual(results["exact_match_rate"], 1 / 3)
        self.assertEqual(results["partial_match_rate"], 2 / 3)
        self.assertEqual(results["level_metrics"]["Level_1"]["exact_matches"], 1)
        self.assertEqual(results["level_metrics"]["Level_2"]["partial_matches"], 1)
        self.assertEqual(results["level_metrics"]["Level_3"]["exact_matches"], 0)
        self.assertEqual(len(agent.prompts), 3)

    def test_empty_dataset_returns_empty_results(self):
        log("evaluator: empty dataset result shape")
        with tempfile.TemporaryDirectory() as tempdir:
            dataset = GAIADataset(local_data_dir=Path(tempdir))
            evaluator = GAIAEvaluator(dataset=dataset, level=1)
            results = evaluator.evaluate(ScriptedGAIAAgent([]))

        self.assertEqual(results["total_samples"], 0)
        self.assertEqual(results["level_metrics"], {})
        self.assertEqual(results["level_filter"], 1)

    def test_export_to_gaia_format_writes_jsonl_with_optional_reasoning(self):
        log("evaluator: GAIA official JSONL export")
        evaluator = GAIAEvaluator(dataset=empty_local_dataset())
        results = {
            "detailed_results": [
                {"task_id": "t1", "predicted": "4", "response": "FINAL ANSWER: 4"},
                {"task_id": "t2", "predicted": "Paris", "response": "FINAL ANSWER: Paris"},
            ]
        }

        with tempfile.TemporaryDirectory() as tempdir:
            with_reasoning = Path(tempdir) / "gaia_with_reasoning.jsonl"
            without_reasoning = Path(tempdir) / "gaia_without_reasoning.jsonl"
            evaluator.export_to_gaia_format(results, with_reasoning, include_reasoning=True)
            evaluator.export_to_gaia_format(results, without_reasoning, include_reasoning=False)
            rows_with = [json.loads(line) for line in with_reasoning.read_text(encoding="utf-8").splitlines()]
            rows_without = [json.loads(line) for line in without_reasoning.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(rows_with[0], {
            "task_id": "t1",
            "model_answer": "4",
            "reasoning_trace": "FINAL ANSWER: 4",
        })
        self.assertNotIn("reasoning_trace", rows_without[0])


class GAIAMetricsTest(unittest.TestCase):
    def sample_results(self):
        return [
            {"level": 1, "exact_match": True, "partial_match": True, "score": 1.0, "execution_time": 0.1},
            {"level": 2, "exact_match": False, "partial_match": True, "score": 0.5, "execution_time": 0.3},
            {"level": 3, "exact_match": False, "partial_match": False, "score": 0.0, "execution_time": 0.5},
        ]

    def test_basic_rate_helpers_and_level_metrics(self):
        log("metrics: exact/partial rates and level metrics")
        results = self.sample_results()

        self.assertEqual(GAIAMetrics.calculate_exact_match_rate(results), 1 / 3)
        self.assertEqual(GAIAMetrics.calculate_partial_match_rate(results), 2 / 3)
        self.assertEqual(GAIAMetrics.calculate_average_execution_time(results), 0.3)
        self.assertEqual(GAIAMetrics.calculate_level_metrics(results, 2), {
            "total": 1,
            "exact_match_rate": 0.0,
            "partial_match_rate": 1.0,
            "average_score": 0.5,
        })
        self.assertEqual(GAIAMetrics.calculate_level_metrics(results, 99)["total"], 0)

    def test_compute_metrics_includes_difficulty_progression_and_errors(self):
        log("metrics: full compute_metrics output")
        metrics = GAIAMetrics().compute_metrics(self.sample_results())

        self.assertEqual(metrics["total_samples"], 3)
        self.assertEqual(metrics["exact_match_rate"], 1 / 3)
        self.assertEqual(metrics["partial_match_rate"], 2 / 3)
        self.assertEqual(metrics["level_metrics"]["Level_1"]["average_score"], 1.0)
        self.assertEqual(metrics["performance_analysis"]["level_performance"]["Level_1"]["success_rate"], 1.0)
        self.assertEqual(metrics["performance_analysis"]["difficulty_progression"]["Level_1_to_Level_2"]["drop_rate"], 1.0)
        self.assertEqual(metrics["performance_analysis"]["error_analysis"]["total_errors"], 2)
        self.assertEqual(metrics["performance_analysis"]["error_analysis"]["partial_correct"], 1)
        self.assertEqual(metrics["score_statistics"]["min"], 0.0)
        self.assertEqual(metrics["score_statistics"]["max"], 1.0)

    def test_empty_metrics_and_compare_results(self):
        log("metrics: empty metrics and comparison helper")
        empty = GAIAMetrics().compute_metrics([])
        comparison = GAIAMetrics.compare_results(
            {
                "exact_match_rate": 0.8,
                "partial_match_rate": 0.9,
                "average_execution_time": 1.2,
                "level_metrics": {"Level_1": {"exact_match_rate": 1.0, "average_score": 0.8}},
            },
            {
                "exact_match_rate": 0.5,
                "partial_match_rate": 0.6,
                "average_execution_time": 2.0,
                "level_metrics": {"Level_1": {"exact_match_rate": 0.5, "average_score": 0.4}},
            },
        )

        self.assertEqual(empty["total_samples"], 0)
        self.assertEqual(comparison["exact_match_rate_diff"], 0.30000000000000004)
        self.assertEqual(comparison["partial_match_rate_diff"], 0.30000000000000004)
        self.assertEqual(comparison["execution_time_diff"], -0.8)
        self.assertEqual(comparison["level_comparison"]["Level_1"]["score_diff"], 0.4)


if __name__ == "__main__":
    unittest.main()
