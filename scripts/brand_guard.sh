#!/usr/bin/env bash
set -euo pipefail

# Guard script: fails if the forbidden brand term appears
# in tracked file contents or file paths.

# Build the search term without writing it literally in this file
term="ama"; term="${term}deus"

echo "Running brand guard..."

# Search committed tree (HEAD) contents first (CI and pre-push typical case)
set +e
content_hits=$(git grep -n -I -i --color=never -- "$term" HEAD 2>/dev/null)
set -e

# Search tracked file names in HEAD
set +e
name_hits=$(git ls-files | grep -i "$term" || true)
set -e

if [[ -n "${content_hits}" || -n "${name_hits}" ]]; then
  echo "Forbidden brand term detected in repository:" >&2
  if [[ -n "${name_hits}" ]]; then
    echo "- In file paths:" >&2
    echo "${name_hits}" >&2
  fi
  if [[ -n "${content_hits}" ]]; then
    echo "- In file contents (file:line):" >&2
    echo "${content_hits}" >&2
  fi
  exit 1
fi

# Fallback: check working tree tracked files (in case HEAD is missing or detached)
set +e
wt_hits=$(git ls-files -z | xargs -0 grep -I -n -H -i -- "$term" 2>/dev/null || true)
set -e
if [[ -n "${wt_hits}" ]]; then
  echo "Forbidden brand term detected in working tree tracked files:" >&2
  echo "${wt_hits}" >&2
  exit 1
fi

echo "Brand guard passed: no forbidden term found."

