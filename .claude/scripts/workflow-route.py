#!/usr/bin/env python3
"""Resolve requested workflow resources; never spawn agents or change a session model."""

import argparse
import json
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / "shared/workflow-resources/policy.json"


def resolve(role, runtime, risks=(), policy=None):
    policy = policy or json.loads(POLICY.read_text())
    if runtime not in ("claude", "codex"):
        raise ValueError("runtime must be claude or codex")
    names = {**policy["roles"], **policy["lenses"]}
    # Unknown roles must be explicitly classified, never silently downgraded.
    if role not in names and role not in (
        "implementation",
        "specification",
        "research",
        "extraction",
    ):
        raise ValueError("unknown role; classify it in the shared policy first")
    invalid = set(risks) - set(policy["critical_risks"])
    if invalid:
        raise ValueError("unknown risk category")
    tier = names.get(
        role, "extraction" if role == "extraction" else policy["default_tier"]
    )
    if risks:
        if tier == "extraction":
            raise ValueError("extraction cannot approve or execute high-risk work")
        tier = "critical"
    settings = policy["tiers"][tier][runtime]
    custom = role if role in policy["roles"] else None
    if tier == "critical" and names.get(role) != "critical":
        custom = "workflow-escalation"
    elif tier == "extraction":
        custom = "workflow-extractor"
    return {
        "policy_version": policy["version"],
        "role": role,
        "runtime": runtime,
        "tier": tier,
        "agent_type": custom,
        "requested": settings,
        "risks": sorted(set(risks)),
        "actual": None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("role")
    ap.add_argument("--runtime", choices=("claude", "codex"), required=True)
    ap.add_argument("--risk", action="append", default=[])
    args = ap.parse_args()
    try:
        print(
            json.dumps(
                resolve(args.role, args.runtime, args.risk),
                ensure_ascii=False,
                indent=2,
            )
        )
    except ValueError as error:
        ap.error(str(error))


if __name__ == "__main__":
    main()
