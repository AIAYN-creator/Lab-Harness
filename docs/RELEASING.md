# Releasing

A list to follow in order. The once-only setup (PyPI, TestPyPI and the two GitHub environments) is
in [*Publishing a release*](onboarding.md#publishing-a-release); this is what to do every time.

The workflow is `.github/workflows/release.yml`. It publishes with trusted publishing: no token
exists anywhere.

## 1. Before

- `main` is green on Linux, Windows and macOS.
- `uv run pytest` passes on your machine with LaTeX installed.
- `uv run labharness doctor` has nothing to fix.

## 2. The version

1. Change `version` in `pyproject.toml`, then `uv lock`. The version lives only there:
   `labharness.__version__` reads it from the installed package.
2. In `docs/CHANGELOG.md`, move what is under *Unreleased* to the new version, with its date, and
   add the comparison link at the bottom.
3. Update *Status* and *Progress* in the README so they say what this version is.

## 3. The commit and the tag

One commit, `release: vX.Y.Z`, and the tag `vX.Y.Z` on it. Pushing the tag starts the workflow,
and the workflow refuses a tag that does not match `pyproject.toml`.

```bash
git tag vX.Y.Z
git push origin main vX.Y.Z
```

## 4. The rehearsal

The workflow publishes to TestPyPI first. Before letting the real one through, in a clean
environment:

```bash
uv venv /tmp/release-check
uv pip install --python /tmp/release-check --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ labharness==X.Y.Z
/tmp/release-check/bin/labharness doctor
```

## 5. PyPI

The `pypi` environment waits for the maintainer's approval: approving it is the publication.

## 6. The GitHub release

Create it from the tag, with the notes from the changelog. The workflow attaches the wheel and the
sdist if the release exists when it finishes; if not, attach them by hand from the workflow's
artifacts.

## 7. After

In a clean environment, `pip install labharness`, then `labharness --version` and
`labharness doctor`. Run the demo in the README once.

## If it goes wrong

**PyPI never accepts the same version twice**, not even after deleting it. So a bad release is
not fixed by re-uploading:

1. **Yank** the version on PyPI (*Manage → Options → Yank*). It stays installable for whoever
   pinned it, and stops being chosen by everyone else.
2. Fix it on `main`, and release `X.Y.Z+1` with the steps above.
3. Say what happened in the changelog, under the new version.

If the workflow failed before PyPI, nothing was published: fix it, delete the tag
(`git push --delete origin vX.Y.Z`, `git tag -d vX.Y.Z`) and tag again.
