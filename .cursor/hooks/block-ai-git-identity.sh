#!/bin/bash
# Block shell git commits that would attribute work to AI/agent identities.

input=$(cat)
command=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("command",""))')

if ! printf '%s' "$command" | grep -Eq '(^|[;&|[:space:]])git([[:space:]]|$)'; then
  printf '{ "permission": "allow" }\n'
  exit 0
fi

if ! printf '%s' "$command" | grep -Eq 'git[[:space:]]+commit'; then
  printf '{ "permission": "allow" }\n'
  exit 0
fi

deny() {
  printf '{
    "permission": "deny",
    "user_message": "Blocked: git commits must use your human identity only. AI agents must never appear as contributors.",
    "agent_message": "Do not set --author, GIT_AUTHOR_*, GIT_COMMITTER_*, or Co-authored-by for AI. Commit with the repository owner git config only."
  }\n'
  exit 0
}

# Override author/committer identity
if printf '%s' "$command" | grep -Eq '--author=|-c[[:space:]]+user\.(name|email)=|GIT_(AUTHOR|COMMITTER)_(NAME|EMAIL)='; then
  deny
fi

# Co-author trailers commonly added by AI tooling
if printf '%s' "$command" | grep -Eiq 'co-authored-by|trailer[[:space:]]+Co-authored-by'; then
  deny
fi

# Agent email addresses in author/committer overrides only
if printf '%s' "$command" | grep -Eiq '(--author=|GIT_(AUTHOR|COMMITTER)_(NAME|EMAIL)=|-c[[:space:]]+user\.(name|email)=).*@(cursor\.com|cursoragent\.com|users\.noreply\.github\.com)'; then
  deny
fi

if printf '%s' "$command" | grep -Eiq 'Co-authored-by:.*@(cursor\.com|cursoragent\.com)'; then
  deny
fi

printf '{ "permission": "allow" }\n'
exit 0
