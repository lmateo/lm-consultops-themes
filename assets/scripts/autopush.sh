#!/usr/bin/env bash
set -e

EXPECTED_GIT_BASH_PATH="/c/Program Files/Git/git-bash.exe"

require_git_bash() {
  if [ -z "${BASH_VERSION:-}" ]; then
    echo "Error: this script must run in Bash."
    exit 1
  fi

  case "$(uname -s)" in
    MINGW*|MSYS*)
      ;;
    *)
      echo "Error: push operations must run from Git Bash on Windows."
      echo "Open: C:\\Program Files\\Git\\git-bash.exe"
      exit 1
      ;;
  esac

  if [ ! -x "$EXPECTED_GIT_BASH_PATH" ]; then
    echo "Error: expected Git Bash was not found at:"
    echo "  C:\\Program Files\\Git\\git-bash.exe"
    exit 1
  fi
}

require_git_bash

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

BRANCH=$(git branch --show-current)

if [ -z "$BRANCH" ]; then
  echo "Error: could not determine current git branch."
  exit 1
fi

echo "Current branch: $BRANCH"
echo "Checking git status..."
git status

run_preview_audits() {
  if [ ! -f "scripts/audit_crafto_hash_links.py" ]; then
    return
  fi

  echo "Running preview audit checks..."
  py scripts/audit_crafto_hash_links.py > scripts/audit_crafto_hash_links_report.txt
  HASH_MATCHES="$(awk -F': ' '/^matches:/ {print $2}' scripts/audit_crafto_hash_links_report.txt || true)"
  HASH_MATCHES="${HASH_MATCHES:-0}"

  if ! [[ "$HASH_MATCHES" =~ ^[0-9]+$ ]]; then
    echo "Error: could not parse hash-link audit result:"
    echo "  scripts/audit_crafto_hash_links_report.txt"
    exit 1
  fi

  if [ "$HASH_MATCHES" -gt 0 ]; then
    echo "Error: hash-link audit found $HASH_MATCHES invalid links."
    echo "Fix '/crafto/#' or bare '#' links before autopush."
    echo "See: scripts/audit_crafto_hash_links_report.txt"
    exit 1
  fi

  if [ -f "scripts/audit_preview_header_footer_links.py" ]; then
    py scripts/audit_preview_header_footer_links.py > scripts/audit_report.txt
  fi

  if [ -f "scripts/audit_preview_titles.py" ]; then
    py scripts/audit_preview_titles.py > scripts/audit_preview_titles_report.txt
    TITLE_MISMATCHES="$(awk -F': ' '/^mismatches:/ {print $2}' scripts/audit_preview_titles_report.txt || true)"
    TITLE_MISMATCHES="${TITLE_MISMATCHES:-0}"

    if ! [[ "$TITLE_MISMATCHES" =~ ^[0-9]+$ ]]; then
      echo "Error: could not parse title audit result:"
      echo "  scripts/audit_preview_titles_report.txt"
      exit 1
    fi

    if [ "$TITLE_MISMATCHES" -gt 0 ]; then
      echo "Error: title audit found $TITLE_MISMATCHES mismatches."
      echo "Fix preview <title> values before autopush."
      echo "See: scripts/audit_preview_titles_report.txt"
      exit 1
    fi
  fi

  if [ -f "scripts/audit_assets_components.py" ]; then
    py scripts/audit_assets_components.py > scripts/audit_assets_report.txt
  fi
}

run_preview_audits

echo "Staging changes..."
git add .

if git diff --cached --quiet; then
  echo "No staged changes to commit. Exiting."
  exit 0
fi

# Derive a sensible conventional commit message when none is provided.
if [ -z "${1:-}" ]; then
  STAGED_FILES="$(git diff --cached --name-only)"

  if echo "$STAGED_FILES" | grep -qE '(^|/)tests?/'; then
    TYPE="test"
  elif echo "$STAGED_FILES" | grep -qiE '\.(md|rst)$'; then
    TYPE="docs"
  elif echo "$STAGED_FILES" | grep -qiE '\.(ya?ml|json)$'; then
    TYPE="chore"
  elif echo "$STAGED_FILES" | grep -qiE '\.(css|scss|sass|less|html|js|ts|tsx)$'; then
    TYPE="style"
  else
    TYPE="chore"
  fi

  MESSAGE="${TYPE}: automated Cursor update"
else
  MESSAGE="$1"
fi

echo "Creating commit..."
git commit -m "$MESSAGE"

echo "Pulling latest changes with rebase..."
git pull --rebase origin "$BRANCH"

echo "Pushing to GitHub..."
git push origin "$BRANCH"

echo "Auto-push complete."
