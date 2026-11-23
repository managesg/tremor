"""Build and inspect the exact SmolLM3 smoke container without starting it."""

from pathlib import Path
import re

from lab import spark_calibration_guard as spark


CONTAINER_MEMORY_BYTES = 60 * 2**30
PID_LIMIT = 64
CONTAINER_USER = "1000:1000"
EXPECTED_MOUNTS = ("/snapshot", "/runner")
TMPFS_OPTIONS = "rw,nosuid,nodev,size=128m,mode=1777"
WORKER_ENV = {
    "HOME": "/tmp", "PYTHONPATH": "/runner", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
    "OMP_NUM_THREADS": "1", "HF_HUB_DISABLE_PROGRESS_BARS": "1", "TOKENIZERS_PARALLELISM": "false",
    "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": "0", "NVIDIA_VISIBLE_DEVICES": "0",
}
INSPECT_FIELDS = (
    ("id", ".Id"), ("image", ".Image"), ("name", ".Name"),
    ("entrypoint", ".Config.Entrypoint"), ("args", ".Config.Cmd"), ("user", ".Config.User"),
    ("attempt", '(index .Config.Labels "ai.seabridge.tremor.attempt")'),
    ("network", ".HostConfig.NetworkMode"), ("runtime", ".HostConfig.Runtime"),
    ("readonly", ".HostConfig.ReadonlyRootfs"), ("privileged", ".HostConfig.Privileged"),
    ("memory", ".HostConfig.Memory"), ("swap", ".HostConfig.MemorySwap"),
    ("pids", ".HostConfig.PidsLimit"), ("requests", ".HostConfig.DeviceRequests"),
    ("devices", ".HostConfig.Devices"), ("mounts", ".Mounts"),
    ("log_driver", ".HostConfig.LogConfig.Type"), ("state", ".State.Status"),
    ("tmpfs", ".HostConfig.Tmpfs"),
)


def _bind(directory):
    path = Path(directory).absolute()
    if path.resolve(strict=True) != path or not path.is_dir() or any(c in str(path) for c in ",\r\n"):
        raise ValueError("mount must be a real, unambiguous local directory")
    return str(path)


def _worker_args(plan_sha256):
    if not re.fullmatch(r"[0-9a-f]{64}", plan_sha256):
        raise ValueError("native plan needs a canonical SHA-256")
    return [
        "--kill-after=5s", "285s", "python", "-B", "-m", "lab.smollm3_smoke_worker",
        "/snapshot", "/runner/candidate-cuda-plan.json", "--plan-sha256", plan_sha256,
    ]


def create_command(attempt, snapshot, worker, plan_sha256):
    """Return the create argv. The guarded caller owns registration and execution."""
    if not re.fullmatch(r"tremor-r2-[0-9a-f]{32}", attempt):
        raise ValueError("attempt must use the shared Spark journal namespace")
    paths = (_bind(snapshot), _bind(worker))
    if paths[0] == paths[1] or Path(paths[0]).is_relative_to(paths[1]) or Path(paths[1]).is_relative_to(paths[0]):
        raise ValueError("model and worker mounts must be disjoint")
    mounts = [
        argument
        for source, target in zip(paths, EXPECTED_MOUNTS, strict=True)
        for argument in ("--mount", f"type=bind,source={source},target={target},readonly")
    ]
    environment = [argument for key, value in WORKER_ENV.items() for argument in ("-e", f"{key}={value}")]
    return [
        *spark.DOCKER, "create", "--name", attempt, "--label", f"{spark.ATTEMPT_LABEL}={attempt}",
        "--pull=never", "--runtime=runc", "--log-driver=none", "--gpus", "device=0",
        "--network", "none", "--read-only", "--memory", "60g", "--memory-swap", "60g",
        "--pids-limit", str(PID_LIMIT), "--user", CONTAINER_USER,
        "--tmpfs", f"/tmp:{TMPFS_OPTIONS}", *mounts, *environment,
        "--entrypoint", "timeout", spark.IMAGE, *_worker_args(plan_sha256),
    ]


def inspect_command(identity):
    if not spark.CONTAINER_ID.fullmatch(identity):
        raise ValueError("expected the exact full Docker ID returned at create")
    fields = [f'"{key}":{{{{json {field}}}}}' for key, field in INSPECT_FIELDS]
    selected = " ".join(f'(eq $key "{key}")' for key in WORKER_ENV)
    # Emit matches for only the expected nonsecret keys. The sentinel keeps valid JSON.
    fields.append(
        '"env_matches":[{{range .Config.Env}}{{ $key := index (split . "=") 0 }}'
        + "{{if or " + selected + "}}{{json .}},{{end}}{{end}}null]"
    )
    view = "{" + ",".join(fields) + "}"
    return [*spark.DOCKER, "inspect", "--type", "container", "--format", view, identity]


def verify_created(view, *, identity, attempt, snapshot, worker, plan_sha256):
    """Reject a different container, mount, GPU, or worker before attachment."""
    fields = {key for key, _ in INSPECT_FIELDS} | {"env_matches"}
    if not spark.CONTAINER_ID.fullmatch(identity) or type(view) is not dict or view.keys() != fields:
        raise ValueError("malformed exact-container inspection")
    expected = {
        "id": identity, "image": spark.IMAGE, "name": f"/{attempt}", "attempt": attempt,
        "entrypoint": ["timeout"], "args": _worker_args(plan_sha256), "user": CONTAINER_USER,
        "network": "none", "runtime": "runc", "readonly": True, "privileged": False,
        "memory": CONTAINER_MEMORY_BYTES, "swap": CONTAINER_MEMORY_BYTES, "pids": PID_LIMIT,
        "devices": [], "log_driver": "none", "state": "created", "tmpfs": {"/tmp": TMPFS_OPTIONS},
    }
    if any(type(view[key]) is not type(value) or view[key] != value for key, value in expected.items()):
        raise ValueError("created container does not match the pinned smoke settings")
    env = view["env_matches"]
    if (type(env) is not list or env[-1:] != [None] or any(type(entry) is not str for entry in env[:-1])
            or sorted(env[:-1]) != sorted(f"{key}={value}" for key, value in WORKER_ENV.items())):
        raise ValueError("created worker environment differs from the pinned smoke settings")
    requests = view["requests"]
    expected_request = {"Driver": "", "Count": 0, "DeviceIDs": ["0"], "Capabilities": [["gpu"]], "Options": {}}
    if (type(requests) is not list or len(requests) != 1 or type(requests[0]) is not dict
            or requests[0] != expected_request or type(requests[0]["Count"]) is not int):
        raise ValueError("created container must request exactly CUDA device 0")
    mounts = view["mounts"]
    if not isinstance(mounts, list) or any(not isinstance(item, dict) for item in mounts):
        raise ValueError("invalid container mount inventory")
    observed = {item.get("Destination"): (item.get("Type"), item.get("Source"), item.get("RW")) for item in mounts}
    if len(mounts) != 2 or observed != {
        "/snapshot": ("bind", _bind(snapshot), False), "/runner": ("bind", _bind(worker), False),
    } or any(item.get("RW") is not False for item in mounts):
        raise ValueError("created model and worker mounts must match the reviewed read-only inputs")
