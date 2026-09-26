# `labharness`

Turn raw lab data into publication-ready LaTeX figures, and keep the PDF in sync.

**Usage**:

```console
$ labharness [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--version`: Print the LabHarness version and exit.
* `--help`: Show this message and exit.

**Commands**:

* `init`: Create a workspace: manuscript, data,...
* `add`: Add a figure or a table: write its script...
* `build`: Rebuild the figures and compile the...
* `watch`: Watch the workspace and rebuild on every...
* `preview`: Render figures as PNG images, to look at...
* `eject`: Copy this workspace into a folder that...
* `accept`: Accept a change to a raw data file,...
* `resolve`: Turn a name into a SMILES file, offline:...
* `cite`: Add a work to the bibliography from its...
* `doctor`: Check that this machine has everything...
* `hook`: The git hook that stops unaccepted data...
* `library`: The lab&#x27;s compound inventory, named by...

## `labharness init`

Create a workspace: manuscript, data, scripts, figures and manifest.

**Usage**:

```console
$ labharness init [OPTIONS] [path]
```

**Arguments**:

* `path`: Where to create the workspace.  [default: .]

**Options**:

* `--journal <str>`: Template: acs, article, elsevier, report, rsc-draft.  [default: acs]
* `--font <str>`: Typeface: latin-modern, termes, pagella, stix, libertinus. Default: the journal&#x27;s.
* `--force / --no-force`: Write into a folder that is not empty.  [default: no-force]
* `--help`: Show this message and exit.

## `labharness add`

Add a figure or a table: write its script from a template and declare it.

**Usage**:

```console
$ labharness add [OPTIONS] {kind} {name}
```

**Arguments**:

* `kind`: What to add: structure, plot, mechanism, flow, network, table.  [required]
* `name`: Name of the script, and of figures/&lt;name&gt;.pdf or tables/&lt;name&gt;.tex.  [required]

**Options**:

* `--input <path>`: A file it depends on. Repeatable.
* `--insert / --no-insert`: Also add its block to paper.tex, before the references.  [default: no-insert]
* `--edit / --no-edit`: Open the new script in your editor.  [default: no-edit]
* `--force / --no-force`: Replace a script that already exists.  [default: no-force]
* `--help`: Show this message and exit.

## `labharness build`

Rebuild the figures and compile the document once.

**Usage**:

```console
$ labharness build [OPTIONS]
```

**Options**:

* `--only <str>`: Rebuild a single figure, by name.
* `--no-latex / --no-no-latex`: Rebuild figures without compiling.  [default: no-no-latex]
* `--help`: Show this message and exit.

## `labharness watch`

Watch the workspace and rebuild on every save.

**Usage**:

```console
$ labharness watch [OPTIONS]
```

**Options**:

* `--no-open`: Do not open the PDF viewer.
* `--debounce <int>`: Milliseconds used to group rapid saves.  [default: 100]
* `--json`: Write what happens as JSON events, one per line.
* `--help`: Show this message and exit.

## `labharness preview`

Render figures as PNG images, to look at them before trusting them.

**Usage**:

```console
$ labharness preview [OPTIONS]
```

**Options**:

* `--only <str>`: Preview a single figure, by name.
* `--document / --no-document`: Also render every page of the compiled paper.pdf.  [default: no-document]
* `--dpi <int range>`: Resolution of the images.  [default: 200; 36&lt;=x&lt;=1200]
* `--help`: Show this message and exit.

## `labharness eject`

Copy this workspace into a folder that regenerates without LabHarness.

**Usage**:

```console
$ labharness eject [OPTIONS] {target}
```

**Arguments**:

* `target`: New folder for the standalone copy.  [required]

**Options**:

* `--force / --no-force`: Write into a folder that is not empty.  [default: no-force]
* `--help`: Show this message and exit.

## `labharness accept`

Accept a change to a raw data file, recording who, when and what it replaced.

**Usage**:

```console
$ labharness accept [OPTIONS] {files}...
```

**Arguments**:

* `files...`: Data files whose change you accept.  [required]

**Options**:

* `--help`: Show this message and exit.

## `labharness resolve`

Turn a name into a SMILES file, offline: the lab library first, then OPSIN.

**Usage**:

```console
$ labharness resolve [OPTIONS] {name}
```

**Arguments**:

* `name`: A compound of the lab library, or a systematic IUPAC name.  [required]

**Options**:

* `-o, --output <path>`: Where to write the SMILES.  [required]
* `--help`: Show this message and exit.

## `labharness cite`

Add a work to the bibliography from its DOI, asking doi.org. Needs the network.

**Usage**:

```console
$ labharness cite [OPTIONS] {doi}
```

**Arguments**:

* `doi`: The DOI, as 10.1021/... or https://doi.org/...  [required]

**Options**:

* `--bib <path>`: The bibliography. Default: the workspace&#x27;s references.bib.
* `--help`: Show this message and exit.

## `labharness doctor`

Check that this machine has everything LabHarness needs.

**Usage**:

```console
$ labharness doctor [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `labharness hook`

The git hook that stops unaccepted data changes being committed.

**Usage**:

```console
$ labharness hook [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `install`: Install the pre-commit hook in the git...
* `check`: What the hook runs: refuse staged data...

### `labharness hook install`

Install the pre-commit hook in the git repository of this workspace.

**Usage**:

```console
$ labharness hook install [OPTIONS]
```

**Options**:

* `--force / --no-force`: Replace a pre-commit hook LabHarness did not write.  [default: no-force]
* `--help`: Show this message and exit.

### `labharness hook check`

What the hook runs: refuse staged data changes that were not accepted.

**Usage**:

```console
$ labharness hook check [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `labharness library`

The lab&#x27;s compound inventory, named by  in the manifest.

**Usage**:

```console
$ labharness library [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `check`: Check every compound: unreadable SMILES,...

### `labharness library check`

Check every compound: unreadable SMILES, missing stereochemistry, wrong formula.

**Usage**:

```console
$ labharness library check [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.
