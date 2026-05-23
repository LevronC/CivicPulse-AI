#!/bin/sh
# Enable repository git hooks that block AI/agent contributor identities.

set -e

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg

printf 'Git hooks enabled (core.hooksPath=.githooks).\n'
printf 'Allowed commit emails are listed in .githooks/allowed-authors\n'
