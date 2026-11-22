"""Rehearse a Grover inventory commitment and offline opening on synthetic inputs."""

import argparse
from collections import Counter
from datetime import datetime
from fractions import Fraction
from hashlib import sha256
from hmac import compare_digest
from itertools import product
import json
from pathlib import Path
import re

from lab import topology
from .topology_transfer import adapt
from .transfer import exact_trace
from .transfer_fixtures import Fixture, REGIMES, Stage, WORKERS


MANIFEST = "grover_custody_rehearsal_manifest_v1"
RECEIPT = "grover_custody_rehearsal_receipt_v1"
DEVELOPMENT = "grover_custody_rehearsal_development_v1"
EXPECTATIONS = "grover_custody_rehearsal_expectations_v1"
DOMAIN = b"tremor:grover:custody-rehearsal:manifest:v1\x00"
LIMIT = 512 * 1024
DIGEST = re.compile(r"[0-9a-f]{64}")
IDENTITY = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}")
ARMS = set(product(topology.MODES, topology.EVIDENCE_ACCESS))
BRANCHES = ("hit", "no_hit", "boundary")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _object(value, fields, label):
    _require(type(value) is dict and value.keys() == set(fields), f"unexpected {label} fields")


def _identifier(value):
    _require(type(value) is str and IDENTITY.fullmatch(value), "expected a canonical identifier")
    return value


def _pin(value):
    _require(type(value) is str and DIGEST.fullmatch(value), "expected a lowercase SHA-256 digest")
    return value


def _unique(pairs):
    value = dict(pairs)
    _require(len(value) == len(pairs), "duplicate custody member")
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _canonical_document(raw):
    value = json.loads(raw, object_pairs_hook=_unique)
    _require(canonical(value) == raw, "custody document must use canonical JSON bytes")
    return value


def _read(path, limit=LIMIT):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    _require(0 < len(raw) <= limit, "custody input is empty or exceeds its size bound")
    return raw


def commitment(manifest_bytes, nonce):
    """The private opening is exactly 32 bytes, supplied by the custodian."""
    _require(type(nonce) is bytes and len(nonce) == 32, "commitment opening must contain 32 bytes")
    _canonical_document(manifest_bytes)
    return sha256(DOMAIN + nonce + manifest_bytes).hexdigest()


def _stage(row, prior):
    _object(row, ("id", "qubits", "iteration_cap", "target", "marks", "solvers", "prerequisite", "branch"), "stage")
    name = _identifier(row["id"])
    _require(name not in prior, "duplicate stage")
    prerequisite = row["prerequisite"]
    _require(prerequisite is None or _identifier(prerequisite) in prior, "stage prerequisite must precede its use")
    _require(type(row["target"]) is str and len(row["target"]) <= 96, "expected a bounded rational target")
    target = Fraction(row["target"])
    _require(str(target) == row["target"], "target is not canonical rational")
    marks, solvers = row["marks"], row["solvers"]
    _require(type(marks) is dict and marks and marks.keys() <= set(WORKERS), "invalid shard sources")
    _require(type(solvers) is list and solvers == [worker for worker in WORKERS if worker in solvers] and solvers,
             "invalid solver roster")
    _require(0 <= target <= 1, "fallback threshold outside [0, 1]")
    for values in marks.values():
        _require(type(values) is list and all(type(index) is int for index in values)
                 and values == sorted(set(values)), "shard indices must be sorted and unique")
    return Stage(name, row["qubits"], row["iteration_cap"], target,
                 tuple((worker, tuple(marks[worker])) for worker in WORKERS if worker in marks),
                 tuple(solvers), prerequisite)


def projections(fixture):
    """Build worker questions and verifier-side static task eligibility."""
    instrument, _ = adapt(fixture)
    return {
        "workers": {worker: fixture.question_for(worker) for worker in WORKERS},
        "planner_eligibility": {worker: list(instrument.observations[worker]) for worker in WORKERS},
    }


def _requires_separate_sources(stage):
    sources = [set(marks) for _, marks in stage.marks]
    marked = set().union(*sources)
    return all(source != marked for source in sources)


def _check_regime(fixture):
    if fixture.regime == "complementary":
        valid = any(_requires_separate_sources(stage) for stage in fixture.stages)
    elif fixture.regime == "redundant":
        direct = [stage for stage in fixture.stages if stage.prerequisite is None and not stage.needs_shards()]
        common = [stage for stage in direct if len(stage.solvers) >= 2]
        separate = [stage for stage in direct if len(stage.solvers) == 1]
        valid = any(other.solvers[0] not in shared.solvers for shared in common for other in separate)
    else:
        valid = any(stage.prerequisite is not None for stage in fixture.stages)
    _require(valid, f"block structure does not implement {fixture.regime}")


def _block(record):
    _object(record, ("id", "family", "instance", "structure", "regime", "budget", "order", "worker_order",
                     "stages", "projections"), "block")
    identity = tuple(_identifier(record[field]) for field in ("id", "family", "instance", "structure"))
    _require(record["regime"] in REGIMES, "unknown block regime")
    order = record["order"]
    _require(type(order) is list and len(order) == len(ARMS)
             and all(type(arm) is list and len(arm) == 2 for arm in order)
             and {tuple(arm) for arm in order} == ARMS, "block does not bind the complete matched arm schedule")
    roster = record["worker_order"]
    _require(type(roster) is list and sorted(roster) == sorted(WORKERS), "invalid within-arm worker order")
    _require(type(record["budget"]) is int and record["budget"] >= 1, "invalid common arm budget")

    rows = record["stages"]
    _require(type(rows) is list and 0 < len(rows) <= 16, "empty or oversized block stage inventory")
    stages, prior, signatures, counts = [], {}, [], dict.fromkeys(BRANCHES, 0)
    slots = {}
    for row in rows:
        stage = _stage(row, prior)
        task = stage.task(prior)
        trace = exact_trace(task)
        first = next(((step, probability) for step, probability in enumerate(trace) if probability >= task.target), None)
        branch = "no_hit" if first is None else "boundary" if first[1] == task.target else "hit"
        _require(row["branch"] == branch, "declared branch differs from the exact scorer")
        counts[branch] += 1
        prior[stage.name] = first
        slots[stage.name] = len(stages)
        stages.append(stage)
        sources = {worker: set(indices) for worker, indices in stage.marks}
        incidence = Counter(tuple(worker for worker in sources if mark in sources[worker]) for mark in task.marked)
        signatures.append({
            "dependency": slots.get(stage.prerequisite),
            "qubits": stage.qubits,
            "source_slots": list(sources),
            "solver_slots": stage.solvers,
            "mark_incidence": sorted(incidence.items()),
            "fallback_or_initial_target": str(stage.target),
            "effective_target": str(task.target),
            "probability": [str(probability) for probability in trace],
        })
    fixture = Fixture(record["regime"], tuple(stages))
    _check_regime(fixture)
    expected = projections(fixture)
    _require(canonical(record["projections"]) == canonical(expected), "role projection differs from its exact scope")
    return identity, sha256(canonical(signatures)).hexdigest(), counts


def _inventory(rows):
    _require(type(rows) is list and 0 < len(rows) <= 64, "empty or oversized block inventory")
    groups = [set() for _ in range(4)]
    fingerprints = set()
    branches_by_regime = {regime: Counter(dict.fromkeys(BRANCHES, 0)) for regime in REGIMES}
    for row in rows:
        identifiers, fingerprint, counts = _block(row)
        _require(identifiers[0] not in groups[0] and identifiers[2] not in groups[2], "duplicate block or instance")
        _require(fingerprint not in fingerprints, "duplicate equivalent task within the rehearsal inventory")
        for group, item in zip(groups, identifiers, strict=True):
            group.add(item)
        fingerprints.add(fingerprint)
        branches_by_regime[row["regime"]].update(counts)
    return groups, fingerprints, branches_by_regime


def _check_expectations(path, digest, document, manifest_commitment, branches_by_regime):
    raw = _read(path, 16 * 1024)
    _require(compare_digest(sha256(raw).hexdigest(), _pin(digest)), "expectations digest does not match")
    expected = _canonical_document(raw)
    identity = ("inventory_id", "protocol_sha256", "split_rule_sha256", "generator_revision",
                "generator_config_sha256", "development_inventory_sha256")
    _object(expected, ("schema", *identity, "block_ids", "manifest_commitment", "branches_by_regime"),
            "expectations document")
    _require(expected["schema"] == EXPECTATIONS, "unknown rehearsal expectations schema")
    for field in identity:
        _require(expected[field] == document[field], f"{field} differs from expectations")
    _require(expected["block_ids"] == [block["id"] for block in document["blocks"]],
             "ordered block IDs differ from expectations")
    _require(expected["manifest_commitment"] == manifest_commitment, "manifest commitment differs from expectations")
    quotas = expected["branches_by_regime"]
    _object(quotas, REGIMES, "expected regime quota")
    for regime, counts in quotas.items():
        _object(counts, BRANCHES, f"expected {regime} branch quota")
        _require(all(type(value) is int and value >= 0 for value in counts.values()),
                 "expected branch quota must be a nonnegative integer")
    _require(quotas == branches_by_regime, "branch quotas differ from the exact scorer")


def verify(manifest, nonce, receipt, development, *, receipt_sha256, protocol_sha256, split_rule_sha256,
           custodian_id, expectations=None, expectations_sha256=None):
    """Check a synthetic opening and, optionally, a separately pinned comparison."""
    _require((expectations is None) == (expectations_sha256 is None),
             "expectations and their SHA-256 must be supplied together")
    trusted = _read(receipt, 16 * 1024)
    _require(compare_digest(sha256(trusted).hexdigest(), _pin(receipt_sha256)), "receipt digest does not match")
    receipt_row = _canonical_document(trusted)
    _object(receipt_row, ("schema", "inventory_id", "commitment", "protocol_sha256", "split_rule_sha256",
                          "custodian_id", "issuance_index", "issued_utc"), "receipt")
    _require(receipt_row["schema"] == RECEIPT, "unknown rehearsal receipt schema")
    _require(_identifier(receipt_row["custodian_id"]) == _identifier(custodian_id), "unexpected custodian")
    _require(type(receipt_row["issuance_index"]) is int and receipt_row["issuance_index"] >= 0,
             "invalid issuance index")
    issued = receipt_row["issued_utc"]
    _require(type(issued) is str and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", issued),
             "expected a UTC issuance timestamp")
    datetime.fromisoformat(issued)

    raw = _read(manifest)
    document = _canonical_document(raw)
    _object(document, ("schema", "inventory_id", "protocol_sha256", "generator_revision", "generator_config_sha256",
                       "split_rule_sha256", "development_inventory_sha256", "blocks"), "manifest")
    _require(document["schema"] == MANIFEST, "unknown rehearsal manifest schema")
    _require(_identifier(document["inventory_id"]) == receipt_row["inventory_id"], "receipt inventory differs")
    _identifier(document["generator_revision"])
    _pin(document["generator_config_sha256"])
    for field, wanted in (("protocol_sha256", protocol_sha256), ("split_rule_sha256", split_rule_sha256)):
        _require(document[field] == receipt_row[field] == _pin(wanted), f"{field} differs from expected freeze")
    opening = _read(nonce, 32)
    _require(compare_digest(commitment(raw, opening), _pin(receipt_row["commitment"])),
             "manifest opening differs from receipt")

    reference = _read(development)
    _require(compare_digest(sha256(reference).hexdigest(), _pin(document["development_inventory_sha256"])),
             "development inventory digest differs")
    dev = _canonical_document(reference)
    _object(dev, ("schema", "blocks"), "development inventory")
    _require(dev["schema"] == DEVELOPMENT, "unknown rehearsal development schema")
    dev_groups, dev_fingerprints, _ = _inventory(dev["blocks"])
    groups, fingerprints, branches_by_regime = _inventory(document["blocks"])
    for field, prior, held in zip(("block", "family", "instance", "structure"), dev_groups, groups, strict=True):
        _require(prior.isdisjoint(held), f"{field} overlaps the development inventory")
    _require(dev_fingerprints.isdisjoint(fingerprints), "equivalent task structure and probability overlap development")
    result = {
        "evidence": "synthetic_grover_custody_opening",
        "receipt_sha256": receipt_sha256,
        "commitment": receipt_row["commitment"],
        "blocks": len(document["blocks"]),
        "matched_arms": len(document["blocks"]) * len(ARMS),
        "branches": {branch: sum(counts[branch] for counts in branches_by_regime.values()) for branch in BRANCHES},
        "custodian_authenticated": False,
        "authorizes_execution": False,
        "scientific_result": False,
    }
    if expectations is not None:
        _check_expectations(expectations, expectations_sha256, document, receipt_row["commitment"], branches_by_regime)
        result.update(expectations_sha256=expectations_sha256, branches_by_regime=branches_by_regime)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("manifest", "nonce", "receipt", "development"):
        parser.add_argument(arg, type=Path)
    for arg in ("receipt-sha256", "protocol-sha256", "split-rule-sha256", "custodian-id"):
        parser.add_argument(f"--{arg}", required=True)
    parser.add_argument("--expectations", type=Path)
    parser.add_argument("--expectations-sha256")
    try:
        result = verify(**vars(parser.parse_args()))
    except (KeyError, OSError, RecursionError, TypeError, ValueError, ZeroDivisionError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
