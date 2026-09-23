# Rulesets

These files are the source of truth for how the repository is protected. The rulesets active on
GitHub are imported from them, never edited by hand on the website.

| File | Protects |
|---|---|
| `main.json` | The default branch: no deletion or force-push; pull requests need `ci-pass` and the code owner's approval, merged with squash. The administrator bypasses it and pushes directly. |
| `releases.json` | Tags `v*`: only the administrator can create them, and nobody can move or delete one. |

## Changing a ruleset

1. Edit the JSON file in a commit, like any other change.
2. Apply it on GitHub, either from the website (*Settings → Rules → Rulesets*, open the ruleset,
   *Import a ruleset* with the file), or from the command line:

   ```bash
   # Update an existing ruleset from its file
   id=$(gh api repos/AIAYN-creator/Lab-Harness/rulesets --jq '.[] | select(.name=="Proteger main") | .id')
   gh api -X PUT repos/AIAYN-creator/Lab-Harness/rulesets/$id --input .github/rulesets/main.json

   # Create one that does not exist yet
   gh api -X POST repos/AIAYN-creator/Lab-Harness/rulesets --input .github/rulesets/releases.json
   ```

3. Check that GitHub matches the files:

   ```bash
   python tools/check_rulesets.py
   ```

It needs administrator rights, so it runs by hand, at every release, rather than in CI.
