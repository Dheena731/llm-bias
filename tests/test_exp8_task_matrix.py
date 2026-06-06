import copy
import unittest

from experiment8_common import (
    build_exp8_tasks,
    config_hash,
    load_exp8_config,
    unverified_routes,
    validate_exp8_config,
)


class TestExp8TaskMatrix(unittest.TestCase):
    def test_full_task_count_and_ids(self):
        config = load_exp8_config()
        tasks = build_exp8_tasks(config, mode="full")
        expected = (
            len(config["routes"])
            * len(config["prompt_families"])
            * len(config["conditions"])
            * config["tracks"]["text"]["full_repeats"]
        )
        self.assertEqual(len(tasks), expected)
        artifact_ids = [task["artifact_id"] for task in tasks]
        self.assertEqual(len(artifact_ids), len(set(artifact_ids)))
        self.assertIn("model_family", tasks[0])
        self.assertIn("route_stage_label", tasks[0])

    def test_smoke_task_count(self):
        config = load_exp8_config()
        tasks = build_exp8_tasks(config, mode="smoke")
        expected = len(config["conditions"]) * config["tracks"]["text"]["smoke_repeats"]
        self.assertEqual(len(tasks), expected)

    def test_task_metadata_includes_config_hash(self):
        config = load_exp8_config()
        tasks = build_exp8_tasks(config, mode="smoke")

        self.assertEqual(tasks[0]["config_hash"], config_hash(config))
        self.assertIn("stage_provenance", tasks[0])

    def test_config_validation_rejects_duplicate_routes(self):
        config = load_exp8_config()
        broken = copy.deepcopy(config)
        broken["routes"].append(copy.deepcopy(broken["routes"][0]))

        with self.assertRaises(ValueError):
            validate_exp8_config(broken)

    def test_current_config_has_verified_openrouter_routes(self):
        config = load_exp8_config()

        self.assertEqual(unverified_routes(config), [])
        self.assertEqual({task["route_stage_label"] for task in build_exp8_tasks(config, mode="full")}, {"instruct_candidate", "chat_or_instruct"})

    def test_unverified_routes_helper_detects_provenance_gate(self):
        config = load_exp8_config()
        broken = copy.deepcopy(config)
        broken["routes"][0]["stage_provenance"] = "verify_before_full_run"

        self.assertEqual([route["model"] for route in unverified_routes(broken)], [broken["routes"][0]["model"]])


if __name__ == "__main__":
    unittest.main()
