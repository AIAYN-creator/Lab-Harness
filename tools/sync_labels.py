"""Make the repository's issue labels match .github/labels.json.

Creates the labels that are missing and updates the colour and description of the others,
with the GitHub CLI. It never deletes a label: one that is not in the file is only reported,
because removing it would strip it from every issue that has it.

    python tools/sync_labels.py            # show what would change
    python tools/sync_labels.py --apply    # change it
"""

import json
import subprocess
import sys
from pathlib import Path

REPOSITORY = "AIAYN-creator/Lab-Harness"
LABELS = Path(__file__).resolve().parents[1] / ".github" / "labels.json"


def main(apply: bool) -> int:
    wanted = {label["name"]: label for label in json.loads(LABELS.read_text(encoding="utf-8"))}
    listing = subprocess.run(
        [
            "gh",
            "label",
            "list",
            "-R",
            REPOSITORY,
            "--limit",
            "200",
            "--json",
            "name,color,description",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    live = {label["name"]: label for label in json.loads(listing.stdout)}

    for name, label in wanted.items():
        current = live.get(name)
        if current is None:
            action = "create"
        elif (current["color"].lower(), current["description"]) != (
            label["color"].lower(),
            label["description"],
        ):
            action = "update"
        else:
            continue
        print(f"{action:7} {name}")
        if apply:
            subprocess.run(
                [
                    "gh",
                    "label",
                    "create",
                    name,
                    "-R",
                    REPOSITORY,
                    "--force",
                    "--color",
                    label["color"],
                    "--description",
                    label["description"],
                ],
                check=True,
            )

    for name in sorted(set(live) - set(wanted)):
        print(f"extra   {name}  (not in labels.json; left alone)")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv[1:]))
