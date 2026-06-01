import csv
import json
import tempfile
import unittest
from pathlib import Path

from analyze_post_training_priors import (
    annotate_polish_defaults,
    benjamini_hochberg,
    cluster_paired_condition_contrasts,
    dedupe_rows,
    length_exclusion_sensitivity,
    paired_condition_delta_summary,
    parse_features,
    planned_contrasts_fdr,
    prompt_family_holdout_summary,
    run_analysis,
    wilson_ci,
)
from experiment8_common import build_exp8_tasks


def row(
    artifact_id,
    condition,
    prompt_family,
    run,
    features,
    route_stage_label="base_candidate",
    model_family="llama",
    model="meta-llama/llama-3.1-8b",
    error="",
):
    return {
        "artifact_id": artifact_id,
        "track": "text",
        "model": model,
        "model_family": model_family,
        "route_stage_label": route_stage_label,
        "stage_provenance": "unit_test",
        "prompt_family": prompt_family,
        "domain": prompt_family,
        "condition": condition,
        "run": str(run),
        "error": error,
        "feature_json": json.dumps(features),
        "features": parse_features(json.dumps(features)),
        "source_file": "",
    }


class Exp8AnalysisTests(unittest.TestCase):
    def test_parse_features_derives_format_default(self):
        features = parse_features(json.dumps({"has_emoji": False, "has_markdown": True, "word_count": 12}))

        self.assertTrue(features["has_format_default"])

    def test_annotate_polish_defaults_uses_neutral_prompt_family_median(self):
        rows = [
            row("a", "neutral", "launch", 1, {"word_count": 10, "has_stock_phrase": False, "exclamation_count": 0}),
            row("b", "neutral", "launch", 2, {"word_count": 12, "has_stock_phrase": False, "exclamation_count": 0}),
            row("c", "polished_but_plain", "launch", 1, {"word_count": 20, "has_stock_phrase": False, "exclamation_count": 0}),
            row("d", "plain_no_markdown", "launch", 1, {"word_count": 5, "has_stock_phrase": False, "exclamation_count": 0}),
        ]

        annotated = annotate_polish_defaults(rows)

        self.assertTrue(annotated[2]["features"]["has_polish_default"])
        self.assertFalse(annotated[3]["features"]["has_polish_default"])

    def test_wilson_ci_handles_empty_and_extreme_inputs(self):
        self.assertEqual(wilson_ci(0, 0), (0.0, 0.0))
        low, high = wilson_ci(0, 5)
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.0)
        low, high = wilson_ci(5, 5)
        self.assertLess(low, 1.0)
        self.assertEqual(high, 1.0)

    def test_benjamini_hochberg_returns_monotone_adjusted_values_in_original_order(self):
        adjusted = benjamini_hochberg([0.01, 0.04, 0.03])

        self.assertEqual(adjusted, [0.03, 0.04, 0.04])

    def test_dedupe_prefers_clean_row_over_error(self):
        errored = row("same", "neutral", "launch", 1, {}, error="RuntimeError: fail")
        errored["run_id"] = "run-a"
        clean = row("same", "neutral", "launch", 1, {"has_emoji": False, "word_count": 10})
        clean["run_id"] = "run-a"

        deduped = dedupe_rows([errored, clean])

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["error"], "")

    def test_dedupe_keeps_independent_run_ids_for_same_artifact(self):
        first = row("same", "neutral", "launch", 1, {"has_markdown": False, "word_count": 10})
        first["run_id"] = "run-a"
        second = row("same", "neutral", "launch", 1, {"has_markdown": True, "word_count": 10})
        second["run_id"] = "run-b"

        deduped = dedupe_rows([first, second])

        self.assertEqual(len(deduped), 2)
        self.assertEqual({item["run_id"] for item in deduped}, {"run-a", "run-b"})

    def test_paired_condition_delta_summary_compares_same_prompt_family_and_run(self):
        rows = annotate_polish_defaults(
            [
                row("n1", "neutral", "launch", 1, {"has_markdown": True, "word_count": 10}),
                row("p1", "plain_no_markdown", "launch", 1, {"has_markdown": False, "word_count": 9}),
            ]
        )

        summary = paired_condition_delta_summary(rows)
        markdown = [item for item in summary if item["metric"] == "has_markdown"][0]

        self.assertEqual(markdown["paired_n"], 1)
        self.assertEqual(markdown["mean_paired_delta"], -1.0)

    def test_prompt_family_holdout_summarizes_each_family_without_leakage(self):
        rows = annotate_polish_defaults(
            [
                row("a", "neutral", "launch", 1, {"has_markdown": True, "word_count": 10}),
                row("b", "neutral", "legal", 1, {"has_markdown": False, "word_count": 8}),
            ]
        )

        summary = prompt_family_holdout_summary(rows, features=["has_markdown"])
        held_out = {item["held_out_prompt_family"] for item in summary}

        self.assertEqual(held_out, {"launch", "legal"})
        self.assertTrue(all(item["train_prompt_family_count"] == 1 for item in summary))

    def test_length_sensitivity_separates_length_component(self):
        rows = annotate_polish_defaults(
            [
                row("n1", "neutral", "launch", 1, {"word_count": 10, "has_stock_phrase": False, "exclamation_count": 0}),
                row("p1", "polished_but_plain", "launch", 1, {"word_count": 20, "has_stock_phrase": False, "exclamation_count": 0}),
            ]
        )

        summary = length_exclusion_sensitivity(rows)

        self.assertEqual(summary[0]["polish_default_rate"], 0.5)
        self.assertEqual(summary[0]["polish_without_length_rate"], 0.0)

    def test_planned_contrasts_apply_fdr_to_condition_comparisons(self):
        rows = annotate_polish_defaults(
            [
                row("n1", "neutral", "launch", 1, {"has_markdown": True, "word_count": 10}),
                row("n2", "neutral", "legal", 1, {"has_markdown": True, "word_count": 10}),
                row("p1", "plain_no_markdown", "launch", 1, {"has_markdown": False, "word_count": 10}),
                row("p2", "plain_no_markdown", "legal", 1, {"has_markdown": False, "word_count": 10}),
            ]
        )

        contrasts = planned_contrasts_fdr(rows, features=["has_markdown"])

        self.assertTrue(contrasts)
        self.assertIn("p_value_fdr", contrasts[0])

    def test_cluster_paired_condition_contrasts_use_prompt_family_clusters(self):
        rows = annotate_polish_defaults(
            [
                row("n1", "neutral", "launch", 1, {"has_markdown": True, "word_count": 10}),
                row("p1", "plain_no_markdown", "launch", 1, {"has_markdown": False, "word_count": 9}),
                row("n2", "neutral", "legal", 1, {"has_markdown": True, "word_count": 10}),
                row("p2", "plain_no_markdown", "legal", 1, {"has_markdown": False, "word_count": 9}),
            ]
        )

        contrasts = cluster_paired_condition_contrasts(rows, features=["has_markdown"])

        self.assertEqual(len(contrasts), 1)
        self.assertEqual(contrasts[0]["cluster_level"], "prompt_family")
        self.assertEqual(contrasts[0]["cluster_count"], 2)
        self.assertEqual(contrasts[0]["paired_unit_count"], 2)
        self.assertEqual(contrasts[0]["mean_paired_delta"], -1.0)
        self.assertEqual(contrasts[0]["inference_scope"], "prompt_family_clustered_condition_effect")
        self.assertEqual(contrasts[0]["route_count"], 1)
        self.assertTrue(contrasts[0]["routes_same_direction"])
        self.assertIn("p_value_fdr", contrasts[0])

    def test_cluster_paired_condition_contrasts_do_not_cross_route_labels(self):
        rows = annotate_polish_defaults(
            [
                row("n1", "neutral", "launch", 1, {"has_markdown": True, "word_count": 10}),
                row(
                    "p1",
                    "plain_no_markdown",
                    "launch",
                    1,
                    {"has_markdown": False, "word_count": 9},
                    route_stage_label="instruct_candidate",
                ),
            ]
        )

        contrasts = cluster_paired_condition_contrasts(rows, features=["has_markdown"])

        self.assertEqual(contrasts, [])

    def test_cluster_paired_condition_contrasts_report_route_diagnostics(self):
        rows = annotate_polish_defaults(
            [
                row("n1", "neutral", "launch", 1, {"has_markdown": True, "word_count": 10}, model="route/a"),
                row("p1", "plain_no_markdown", "launch", 1, {"has_markdown": False, "word_count": 9}, model="route/a"),
                row("n2", "neutral", "legal", 1, {"has_markdown": True, "word_count": 10}, model="route/b"),
                row("p2", "plain_no_markdown", "legal", 1, {"has_markdown": True, "word_count": 9}, model="route/b"),
            ]
        )

        contrast = cluster_paired_condition_contrasts(rows, features=["has_markdown"])[0]

        self.assertEqual(contrast["route_count"], 2)
        self.assertEqual(contrast["route_delta_min"], -1.0)
        self.assertEqual(contrast["route_delta_max"], 0.0)
        self.assertTrue(contrast["routes_same_direction"])
        self.assertEqual(contrast["prompt_family_delta_min"], -1.0)
        self.assertEqual(contrast["prompt_family_delta_max"], 0.0)
        self.assertTrue(contrast["prompt_families_same_direction"])

    def test_run_analysis_writes_required_outputs(self):
        fixture_rows = [
            row("n1", "neutral", "launch", 1, {"has_markdown": True, "word_count": 10}),
            row("p1", "plain_no_markdown", "launch", 1, {"has_markdown": False, "word_count": 8}),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_csv = tmp_path / "exp8.csv"
            fieldnames = [
                "artifact_id",
                "track",
                "model",
                "model_family",
                "route_stage_label",
                "stage_provenance",
                "prompt_family",
                "domain",
                "condition",
                "run",
                "error",
                "feature_json",
            ]
            with input_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for item in fixture_rows:
                    writer.writerow({key: item.get(key, "") for key in fieldnames})

            output_dir = tmp_path / "out"
            run_analysis([str(input_csv)], output_dir)

            expected = {
                "stage_condition_summary.csv",
                "confidence_intervals.csv",
                "planned_contrasts_fdr.csv",
                "paired_condition_delta_summary.csv",
                "cluster_paired_condition_contrasts.csv",
                "prompt_family_holdout.csv",
                "length_sensitivity.csv",
                "missingness_summary.csv",
                "matrix_completeness.csv",
                "analysis_manifest.json",
                "post_training_priors_report.md",
            }
            self.assertTrue(expected.issubset({path.name for path in output_dir.iterdir()}))

    def test_run_analysis_reports_incomplete_expected_matrix(self):
        config = {
            "routes": [
                {
                    "model": "unit/model-a",
                    "model_family": "unit",
                    "route_stage_label": "instruct_candidate",
                    "stage_provenance": "unit_test_verified",
                }
            ],
            "prompt_families": [
                {"id": "launch", "domain": "marketing", "prompt": "Write a launch note."},
                {"id": "legal", "domain": "legal", "prompt": "Write a legal notice."},
            ],
            "conditions": {
                "neutral": {"suffix": ""},
                "plain_no_markdown": {"suffix": "Use plain text."},
            },
            "tracks": {
                "text": {
                    "smoke_repeats": 1,
                    "full_repeats": 2,
                    "api_parameters": {"max_tokens": 64},
                }
            },
        }
        expected_tasks = build_exp8_tasks(config, mode="full")
        first_task = expected_tasks[0]
        fixture = row(
            first_task["artifact_id"],
            first_task["condition"],
            first_task["prompt_family"],
            first_task["run"],
            {"has_markdown": True, "word_count": 10},
            route_stage_label=first_task["route_stage_label"],
            model_family=first_task["model_family"],
            model=first_task["model"],
        )
        fixture["config_hash"] = first_task["config_hash"]
        fixture["run_id"] = "unit_firstpass"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "exp8_config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            input_csv = tmp_path / "exp8.csv"
            fieldnames = [
                "artifact_id",
                "run_id",
                "config_hash",
                "track",
                "model",
                "model_family",
                "route_stage_label",
                "stage_provenance",
                "prompt_family",
                "domain",
                "condition",
                "run",
                "error",
                "feature_json",
            ]
            with input_csv.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow({key: fixture.get(key, "") for key in fieldnames})

            output_dir = tmp_path / "out"
            outputs = run_analysis(
                [str(input_csv)],
                output_dir,
                config_path=config_path,
                expected_runs_per_cell=2,
            )

            manifest = json.loads(outputs["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["expected_matrix_rows"], len(expected_tasks))
            self.assertEqual(manifest["missing_expected_rows"], len(expected_tasks) - 1)
            self.assertEqual(manifest["completeness_status"], "incomplete")

            with outputs["missingness_summary"].open(newline="", encoding="utf-8") as handle:
                missingness = list(csv.DictReader(handle))
            self.assertTrue(any(int(row["missing_expected_rows"]) > 0 for row in missingness))
            self.assertIn("Matrix completeness status: incomplete", outputs["report"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
