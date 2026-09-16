#!/usr/bin/env sh
# Watch this workspace and rebuild figures and the PDF on every save.
# All the logic lives in the package, so this is only a shortcut.
exec labharness watch "$@"
