"""Compare the rulesets versioned in .github/rulesets/ with the ones active on GitHub.

The files are the source of truth: what a pull request reviews must be what protects the
repository. Reading live rulesets needs administrator rights, so this runs by hand (and at
every release, see RELEASING.md) with an authenticated GitHub CLI, not in CI:

    python tools/check_rulesets.py

It exits 1 and prints every difference if a ruleset is missing or has drifted.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPOSITORY = "AIAYN-creator/Lab-Harness"
FOLDER = Path(__file__).resolve().parents[1] / ".github" / "rulesets"
# Fields GitHub adds or fills in that a versioned file does not carry.
SERVER_ONLY = {
    "integration_id",
    "required_reviewers",
    "require_extra_approval_for_unattributed_changes",
}


def gh(path: str) -> Any:
    result = subprocess.run(
        ["gh", "api", f"repos/{REPOSITORY}/{path}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def normalise(value: Any) -> Any:
    """Drop server-only fields and sort rules by type, so order does not count as drift."""
    if isinstance(value, dict):
        return {key: normalise(item) for key, item in value.items() if key not in SERVER_ONLY}
    if isinstance(value, list):
        items = [normalise(item) for item in value]
        if all(isinstance(item, dict) and "type" in item for item in items):
            return sorted(items, key=lambda item: item["type"])
        return items
    return value


def differences(expected: Any, actual: Any, where: str = "") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        found = []
        for key in sorted(set(expected) | set(actual)):
            found += differences(expected.get(key), actual.get(key), f"{where}.{key}")
        return found
    if isinstance(expected, list) and isinstance(actual, list) and len(expected) == len(actual):
        found = []
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            found += differences(left, right, f"{where}[{index}]")
        return found
    return [] if expected == actual else [f"{where or '.'}: file {expected!r}, live {actual!r}"]


def main() -> int:
    live = {ruleset["name"]: ruleset["id"] for ruleset in gh("rulesets")}
    problems = []
    for path in sorted(FOLDER.glob("*.json")):
        wanted = json.loads(path.read_text(encoding="utf-8"))
        name = wanted["name"]
        if name not in live:
            problems.append(f"{path.name}: no active ruleset called '{name}'")
            continue
        active = gh(f"rulesets/{live[name]}")
        fields = {key: active.get(key) for key in wanted}
        for difference in differences(normalise(wanted), normalise(fields)):
            problems.append(f"{path.name}: {difference}")

    for problem in problems:
        print(problem)
    if not problems:
        print(f"{len(live)} rulesets match the files in {FOLDER.name}/")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
