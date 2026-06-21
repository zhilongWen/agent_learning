import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.benchmarks.bfcl import (
    BFCLDataset,
    BFCLEvaluator,
    BFCLIntegration,
    BFCLMetrics,
)


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def quiet_call(func, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


class ScriptedBFCLAgent:
    def __init__(self, responses):
        self.name = "ScriptedBFCLAgent"
        self.responses = list(responses)
        self.prompts = []

    def run(self, prompt):
        self.prompts.append(prompt)
        if not self.responses:
            return "[]"
        return self.responses.pop(0)


class BFCLDatasetTest(unittest.TestCase):
    def make_data_dir(self):
        tempdir = tempfile.TemporaryDirectory()
        data_dir = Path(tempdir.name)
        rows = [
            {
                "id": "simple_python_0",
                "question": "What is the weather in Beijing?",
                "function": [
                    {
                        "name": "get_weather",
                        "description": "Get current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {"location": {"type": "string"}},
                            "required": ["location"],
                        },
                    }
                ],
            },
            {
                "id": "simple_python_1",
                "question": "Add two numbers",
                "function": [{"name": "add", "description": "Add numbers", "parameters": {}}],
            },
        ]
        answers = [
            {"id": "simple_python_0", "ground_truth": [{"get_weather": {"location": ["Beijing"]}}]},
            {"id": "simple_python_1", "ground_truth": [{"add": {"a": [2], "b": [3]}}]},
        ]
        write_jsonl(data_dir / "BFCL_v4_simple_python.json", rows)
        write_jsonl(data_dir / "possible_answer" / "BFCL_v4_simple_python.json", answers)
        return tempdir, data_dir

    def test_load_merges_official_data_with_ground_truth(self):
        tempdir, data_dir = self.make_data_dir()
        self.addCleanup(tempdir.cleanup)

        dataset = quiet_call(BFCLDataset, bfcl_data_dir=data_dir, category="simple_python")
        data = quiet_call(dataset.load)

        self.assertEqual(len(data), 2)
        self.assertEqual(len(dataset.ground_truth), 2)
        self.assertEqual(data[0]["ground_truth"], [{"get_weather": {"location": ["Beijing"]}}])
        self.assertEqual(dataset.get_ground_truth("simple_python_1"), [{"add": {"a": [2], "b": [3]}}])
        self.assertEqual(data[0]["id"], "simple_python_0")
        self.assertIn("parallel", dataset.get_available_categories())
        self.assertEqual(len(data), 2)

    def test_unknown_category_and_missing_data_are_safe_empty_results(self):
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)

        unknown = quiet_call(BFCLDataset, bfcl_data_dir=tempdir.name, category="unknown_category")
        self.assertEqual(quiet_call(unknown.load), [])

        missing = quiet_call(BFCLDataset, bfcl_data_dir=Path(tempdir.name) / "missing", category="simple_python")
        self.assertEqual(quiet_call(missing.load), [])


class BFCLEvaluatorTest(unittest.TestCase):
    def make_dataset(self):
        tempdir = tempfile.TemporaryDirectory()
        data_dir = Path(tempdir.name)
        rows = [
            {
                "id": "simple_python_0",
                "question": "What is the weather in Beijing?",
                "function": [{"name": "get_weather", "description": "Get weather", "parameters": {}}],
            },
            {
                "id": "simple_python_1",
                "question": "Calculate 2 + 3",
                "function": [{"name": "add", "description": "Add numbers", "parameters": {}}],
            },
        ]
        answers = [
            {"id": "simple_python_0", "ground_truth": [{"get_weather": {"location": ["Beijing"]}}]},
            {"id": "simple_python_1", "ground_truth": [{"add": {"a": [2], "b": [3]}}]},
        ]
        write_jsonl(data_dir / "BFCL_v4_simple_python.json", rows)
        write_jsonl(data_dir / "possible_answer" / "BFCL_v4_simple_python.json", answers)
        dataset = quiet_call(BFCLDataset, bfcl_data_dir=data_dir, category="simple_python")
        return tempdir, dataset

    def test_constructor_accepts_documented_local_data_dir_alias(self):
        tempdir, dataset = self.make_dataset()
        self.addCleanup(tempdir.cleanup)

        evaluator = quiet_call(BFCLEvaluator, category="simple_python", local_data_dir=str(dataset.bfcl_data_dir))

        self.assertEqual(evaluator.dataset.bfcl_data_dir, dataset.bfcl_data_dir)
        self.assertEqual(evaluator.category, "simple_python")

    def test_build_prompt_and_extract_function_calls(self):
        evaluator = quiet_call(BFCLEvaluator, dataset=quiet_call(BFCLDataset, category="simple_python"), category="simple_python")
        prompt = evaluator._build_function_calling_prompt(
            "Get weather",
            [{"name": "get_weather", "description": "Get weather", "parameters": {"type": "object"}}],
        )

        self.assertIn("get_weather", prompt)
        self.assertIn("请以JSON格式返回函数调用", prompt)

        direct = evaluator._extract_function_calls('[{"name":"get_weather","arguments":{"location":"Beijing"}}]')
        embedded = evaluator._extract_function_calls(
            'Result: [{"name":"add","arguments":{"a":2,"b":3}}] done'
        )

        self.assertEqual(direct[0]["name"], "get_weather")
        self.assertEqual(embedded[0]["arguments"], {"a": 2, "b": 3})

    def test_ast_matching_supports_bfcl_v4_and_string_formats(self):
        evaluator = quiet_call(BFCLEvaluator, dataset=quiet_call(BFCLDataset, category="simple_python"), category="simple_python")

        ok, score = evaluator._evaluate_ast_matching(
            [{"name": "get_weather", "arguments": {"location": "Beijing"}}],
            [{"get_weather": {"location": ["Beijing", "北京市"]}}],
        )
        self.assertTrue(ok)
        self.assertEqual(score, 1.0)

        wrong, wrong_score = evaluator._evaluate_ast_matching(
            [{"name": "get_temperature", "arguments": {"location": "Beijing"}}],
            [{"get_weather": {"location": ["Beijing"]}}],
        )
        self.assertFalse(wrong)
        self.assertEqual(wrong_score, 0.0)

        string_ok, string_score = evaluator._evaluate_ast_matching(
            [{"name": "get_weather", "arguments": {"unit": "celsius", "city": "Beijing"}}],
            ['get_weather(city="Beijing", unit="celsius")'],
        )
        self.assertTrue(string_ok)
        self.assertEqual(string_score, 1.0)

    def test_evaluate_runs_agent_and_computes_category_metrics(self):
        tempdir, dataset = self.make_dataset()
        self.addCleanup(tempdir.cleanup)
        evaluator = quiet_call(BFCLEvaluator, dataset=dataset, category="simple_python")
        agent = ScriptedBFCLAgent([
            '[{"name":"get_weather","arguments":{"location":"Beijing"}}]',
            '[{"name":"subtract","arguments":{"a":2,"b":3}}]',
        ])

        results = quiet_call(evaluator.evaluate, agent, max_samples=2)

        self.assertEqual(results["benchmark"], "BFCL")
        self.assertEqual(results["agent_name"], "ScriptedBFCLAgent")
        self.assertEqual(results["total_samples"], 2)
        self.assertEqual(results["correct_samples"], 1)
        self.assertEqual(results["overall_accuracy"], 0.5)
        self.assertEqual(results["category_metrics"]["simple_python"], {
            "total": 2,
            "correct": 1,
            "accuracy": 0.5,
        })
        self.assertEqual(len(agent.prompts), 2)

    def test_export_to_bfcl_format_writes_jsonl_result_and_inference_log(self):
        evaluator = quiet_call(BFCLEvaluator, dataset=quiet_call(BFCLDataset, category="simple_python"), category="simple_python")
        results = {
            "detailed_results": [
                {
                    "sample_id": "simple_python_0",
                    "predicted": [{"name": "get_weather", "arguments": {"location": "Beijing"}}],
                    "question": "Weather?",
                    "response": '[{"name":"get_weather"}]',
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tempdir:
            output_path = Path(tempdir) / "result.json"
            quiet_call(evaluator.export_to_bfcl_format, results, output_path)
            rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(rows[0]["id"], "simple_python_0")
        self.assertEqual(rows[0]["result"], "get_weather(location='Beijing')")
        self.assertEqual(rows[0]["inference_log"][0]["content"], "Weather?")


class BFCLMetricsTest(unittest.TestCase):
    def test_basic_metric_helpers(self):
        self.assertEqual(BFCLMetrics.calculate_accuracy([1, 2, 3], [1, 0, 3]), 2 / 3)
        self.assertEqual(BFCLMetrics.calculate_parameter_accuracy({"city": " Beijing "}, {"city": "beijing"}), 1.0)
        self.assertEqual(BFCLMetrics.calculate_parameter_accuracy({"a": 1}, {"a": 1, "b": 2}), 0.5)
        self.assertEqual(BFCLMetrics.calculate_f1_score(0.5, 1.0), 2 * 0.5 * 1.0 / 1.5)

    def test_compute_metrics_includes_category_and_function_call_stats(self):
        metrics = BFCLMetrics().compute_metrics([
            {
                "success": True,
                "score": 1.0,
                "execution_time": 0.2,
                "category": "simple_python",
                "predicted": [{"name": "get_weather", "arguments": {}}],
            },
            {
                "success": False,
                "score": 0.0,
                "execution_time": 0.4,
                "category": "simple_python",
                "predicted": [{"name": "add", "arguments": {}}],
            },
        ])

        self.assertEqual(metrics["total_samples"], 2)
        self.assertEqual(metrics["success_count"], 1)
        self.assertEqual(metrics["accuracy"], 0.5)
        self.assertEqual(metrics["average_execution_time"], 0.30000000000000004)
        self.assertEqual(metrics["category_metrics"]["simple_python"]["accuracy"], 0.5)
        self.assertEqual(metrics["function_call_stats"]["total_function_calls"], 2)
        self.assertEqual(metrics["function_call_stats"]["function_names"], ["add", "get_weather"])

    def test_precision_recall_uses_function_names(self):
        precision, recall = BFCLMetrics.calculate_precision_recall(
            [{"name": "a"}, {"name": "b"}],
            [{"name": "a"}, {"name": "c"}],
        )

        self.assertEqual(precision, 0.5)
        self.assertEqual(recall, 0.5)


class BFCLIntegrationTest(unittest.TestCase):
    def test_prepare_result_file_and_parse_results_use_expected_paths(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = root / "source.json"
            source.write_text('{"id":"x","result":"f()"}\n', encoding="utf-8")

            integration = BFCLIntegration(project_root=root)
            target = quiet_call(integration.prepare_result_file, source, "HelloAgents", "simple_python")

            self.assertEqual(target, root / "result" / "HelloAgents" / "BFCL_v3_simple_python_result.json")
            self.assertEqual(target.read_text(encoding="utf-8"), source.read_text(encoding="utf-8"))

            score_file = root / "score" / "HelloAgents" / "BFCL_v3_simple_python_score.json"
            score_file.parent.mkdir(parents=True)
            score_file.write_text(json.dumps({"overall_acc": 100.0}), encoding="utf-8")

            self.assertEqual(quiet_call(integration.parse_results, "HelloAgents", "simple_python"), {"overall_acc": 100.0})
            self.assertIsNone(quiet_call(integration.get_summary_csv))


if __name__ == "__main__":
    unittest.main()
