import csv
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from experiment8_collect_text import (
    format_error,
    parse_args,
    raw_output_dir,
    resolve_collection_mode,
    run_single_text_task,
    run_text_tasks,
    validate_run_safety,
)
from experiment8_common import build_exp8_tasks, load_exp8_config


def fake_model(task):
    if task["condition"] == "neutral":
        return "## Launch update\n\nHere is a polished note with a short list:\n- First item\n- Second item"
    return "Plain prose response without decorative formatting."


def failing_model(task):
    raise RuntimeError("fake failure")


class TestExp8FakeCollectors(unittest.TestCase):
    def test_fake_collection_writes_rows(self):
        config = load_exp8_config()
        tasks = build_exp8_tasks(config, mode="smoke")[:2]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "exp8.csv"
            rows = run_text_tasks(tasks, csv_path, tmp_path / "raw", model_fn=fake_model, max_workers=1)
            self.assertEqual(len(rows), 2)
            self.assertTrue(csv_path.exists())
            with csv_path.open(newline="", encoding="utf-8") as handle:
                written = list(csv.DictReader(handle))
            self.assertEqual(len(written), 2)
            self.assertTrue(written[0]["feature_json"])

    def test_errors_are_written_as_rows(self):
        config = load_exp8_config()
        tasks = build_exp8_tasks(config, mode="smoke")[:1]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rows = run_text_tasks(tasks, tmp_path / "exp8.csv", tmp_path / "raw", model_fn=failing_model, max_workers=1)
            self.assertEqual(len(rows), 1)
            self.assertIn("fake failure", rows[0]["error"])

    def test_single_task_row_preserves_run_metadata(self):
        config = load_exp8_config()
        task = build_exp8_tasks(config, mode="smoke")[0]
        task["run_id"] = "run-test"
        with tempfile.TemporaryDirectory() as tmp:
            row = run_single_text_task(task, Path(tmp) / "raw", fake_model)

        self.assertEqual(row["config_hash"], task["config_hash"])
        self.assertEqual(row["run_id"], "run-test")
        self.assertTrue(row["raw_output_path"].endswith(f"{task['artifact_id']}.txt"))

    def test_collection_mode_requires_explicit_collection_flag(self):
        args = parse_args(["--dry-run"])
        self.assertEqual(resolve_collection_mode(args), "full")

        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parse_args([])

        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parse_args(["--smoke", "--full"])

    def test_full_run_requires_confirmation_and_provenance_override(self):
        config = load_exp8_config()

        with self.assertRaises(SystemExit):
            validate_run_safety(parse_args(["--full"]), config)

        args = parse_args(["--full", "--confirm-full"])
        validate_run_safety(args, config)

    def test_provider_error_formatting_removes_user_ids(self):
        api_key = "sk-or-v1-" + "redaction-fixture"
        env_key = "sk-or-v1-" + "env-fixture"
        bearer = "Bearer"
        token = "secret-token"
        error = RuntimeError(
            f"BadRequestError: {{'user_id': 'org_secret', 'api_key': '{api_key}'}} "
            f"Authorization: {bearer} {token} "
            f"OPENROUTER_API_KEY={env_key} "
            "X-API-Key: header-secret "
            "{'organization_id': 'org_private'}"
        )

        formatted = format_error(error)

        self.assertNotIn("org_secret", formatted)
        self.assertNotIn(api_key, formatted)
        self.assertNotIn(token, formatted)
        self.assertNotIn(env_key, formatted)
        self.assertNotIn("header-secret", formatted)
        self.assertNotIn("org_private", formatted)
        self.assertIn("[redacted]", formatted)

    def test_raw_output_dir_is_run_scoped(self):
        config = load_exp8_config()

        first = raw_output_dir(config, "run-a")
        second = raw_output_dir(config, "run-b")

        self.assertNotEqual(first, second)
        self.assertTrue(str(first).endswith("run-a"))


if __name__ == "__main__":
    unittest.main()
