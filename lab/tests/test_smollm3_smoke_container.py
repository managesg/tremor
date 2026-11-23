import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import smollm3_smoke_container as smoke
from lab import spark_calibration_guard as spark


class SmokeContainerTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.snapshot = root / "snapshot"
        self.worker = root / "worker"
        self.snapshot.mkdir()
        self.worker.mkdir()
        self.args = {"identity": "a" * 64, "attempt": "tremor-r2-" + "b" * 32,
                     "snapshot": self.snapshot, "worker": self.worker, "plan_sha256": "d" * 64}
        self.view = {
            "id": self.args["identity"], "image": spark.IMAGE, "name": "/" + self.args["attempt"],
            "attempt": self.args["attempt"], "entrypoint": ["timeout"],
            "args": ["--kill-after=5s", "285s", "python", "-B", "-m", "lab.smollm3_smoke_worker",
                     "/snapshot", "/runner/candidate-cuda-plan.json", "--plan-sha256", "d" * 64],
            "user": "1000:1000", "network": "none", "runtime": "runc", "readonly": True,
            "privileged": False, "memory": 60 * 2**30, "swap": 60 * 2**30, "pids": 64,
            "requests": [{"Driver": "", "Count": 0, "DeviceIDs": ["0"], "Capabilities": [["gpu"]], "Options": {}}],
            "devices": [], "log_driver": "none", "state": "created", "tmpfs": {"/tmp": smoke.TMPFS_OPTIONS},
            "env_matches": [f"{key}={value}" for key, value in smoke.WORKER_ENV.items()] + [None],
            "mounts": [{"Type": "bind", "Source": str(path), "Destination": destination, "RW": False}
                       for path, destination in ((self.snapshot, "/snapshot"), (self.worker, "/runner"))],
        }

    def test_recipe_and_matching_inspection_are_pinned(self):
        create = smoke.create_command(**{key: value for key, value in self.args.items() if key != "identity"})
        self.assertEqual(create[:5], [*spark.DOCKER, "create", "--name"])
        self.assertEqual(create[create.index("--gpus") + 1], "device=0")
        self.assertEqual(create[create.index(spark.IMAGE) + 1:], self.view["args"])
        self.assertEqual(smoke.inspect_command(self.args["identity"])[-1], self.args["identity"])
        smoke.verify_created(self.view, **self.args)

    def test_foreign_and_weakened_docker_settings_are_refused(self):
        for field, value in (("id", "b" * 64), ("image", "sha256:" + "a" * 64), ("network", "host"),
                             ("readonly", False), ("privileged", True), ("state", "running"),
                             ("env_matches", ["CUDA_VISIBLE_DEVICES=1", None]), ("tmpfs", {}),
                             ("requests", [{"DeviceIDs": ["1"], "Capabilities": [["gpu"]]}])):
            with self.subTest(field=field), self.assertRaises(ValueError):
                smoke.verify_created({**self.view, field: value}, **self.args)
        view = copy.deepcopy(self.view)
        view["mounts"][1]["RW"] = True
        with self.assertRaises(ValueError):
            smoke.verify_created(view, **self.args)
        view = copy.deepcopy(self.view)
        view["requests"][0]["Count"] = -1
        with self.assertRaises(ValueError):
            smoke.verify_created(view, **self.args)

    def test_linked_and_nested_mounts_are_refused(self):
        link = self.snapshot.parent / "link"
        link.symlink_to(self.worker)
        for path in (link, self.snapshot, self.snapshot / "nested"):
            if path.name == "nested":
                path.mkdir()
            with self.subTest(path=path.name), self.assertRaises(ValueError):
                smoke.create_command(self.args["attempt"], self.snapshot, path, "d" * 64)
