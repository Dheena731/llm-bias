import unittest

from experiment8_common import build_exp8_tasks, load_exp8_config


class Exp8V2TaskTests(unittest.TestCase):
    def setUp(self):
        self.config = load_exp8_config("configs/exp8_v2_presentation_priors.json")

    def test_hosted_and_local_matrices(self):
        hosted = build_exp8_tasks(self.config)
        local = build_exp8_tasks(self.config, local=True)
        self.assertEqual(len(hosted), 6 * 60 * 8 * 3)
        self.assertEqual(len(local), 4 * 60 * 7 * 1)  # system_plain excluded for local checkpoints
        self.assertEqual(len({t["artifact_id"] for t in hosted + local}), len(hosted) + len(local))
        self.assertNotIn("system_plain", {t["condition"] for t in local})

    def test_system_condition_moves_instruction_out_of_user_prompt(self):
        tasks = [t for t in build_exp8_tasks(self.config) if t["prompt_id"] == "recipe_tip_p1" and t["run"] == 1]
        by_condition = {t["condition"]: t for t in tasks if t["model"] == tasks[0]["model"]}
        self.assertEqual(by_condition["system_plain"]["prompt"], by_condition["neutral"]["prompt"])
        self.assertEqual(by_condition["system_plain"]["system_prompt"], self.config["conditions"]["plain_no_markdown"]["suffix"])
        self.assertEqual(by_condition["neutral"]["system_prompt"], "")


if __name__ == "__main__":
    unittest.main()


class SweepOrphanBlobsTest(unittest.TestCase):
    def test_removes_only_blobs_without_a_remaining_repo(self):
        import tempfile
        from pathlib import Path

        from experiment8_collect_local import sweep_orphan_blobs

        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            (hub / "models--kept").mkdir()
            (hub / "blobs" / "aa").mkdir(parents=True)
            for name, repo in (("aa1", "models--gone"), ("aa2", "models--kept")):
                (hub / "blobs" / "aa" / name).write_text("w")
                (hub / "blobs" / "aa" / f"{name}.lock").write_text("")
                (hub / "blobs" / "aa" / f"{name}.refs").write_text(f"{repo}/blobs/x\n")
            sweep_orphan_blobs(hub)
            self.assertEqual(sorted(p.name for p in (hub / "blobs" / "aa").iterdir()), ["aa2", "aa2.lock", "aa2.refs"])
