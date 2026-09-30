# Bounties for modules

Anyone can ask for a module for their field, and anyone can put a bounty on it. A module is a
package of its own (ADR 31), so a request has a clear shape, and so does the work.

Everything is handled by the maintainer, by hand: no platform sits in the middle.

The other half, building one yourself, is in [Build a module for your field](modules.md).

## Asking for a module

Open an issue with the [*New figure kind or module*](../.github/ISSUE_TEMPLATE/new_module.yml)
form: the figure you make today, what the raw data looks like, and the field. If you would put
money on it, say so in the last field.

If the maintainer finds it worth doing, he does it, free. If not, or not soon, it can carry a
bounty.

## Putting up a bounty, and claiming it

- **Anyone can put a bounty on a request**, the person who asked or not, in the issue. The amount
  is written there.
- **Anyone can claim it**, the maintainer or someone else: say so in the issue. The maintainer
  assigns it, so that two people do not build the same module.
- **The terms are agreed in the issue before anyone starts**: the amount, the maintainer's
  commission, and how it is paid. They are not changed afterwards.

## What a module must be to be paid

The same as any module, and this is what the maintainer checks:

1. **A package of its own**, started with `labharness new-domain`, registered through entry
   points, **without touching LabHarness's core**. LabHarness has a test that fails if the core
   imports a module.
2. **Templates for `labharness add`, its rules for AI agents** (`AGENTS.<field>.md`) **and
   tests**, and its tests pass in CI.
3. **Data is read with LabHarness's reader** and never written to.
4. **MIT licence**, like LabHarness.

Without the maintainer's approval, it is not paid. The author signs the package: the module
carries their name.
