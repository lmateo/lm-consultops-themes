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

BRANCH=$(git branch --show-current)

if [ -z "$BRANCH" ]; then
  echo "Error: could not determine current git branch."
  exit 1
fi

run_pre_push_validations() {
  echo "Running pre-push validations..."
  if command -v py >/dev/null 2>&1; then
    py scripts/audit_download_packages.py
  elif command -v python >/dev/null 2>&1; then
    python scripts/audit_download_packages.py
  else
    echo "Error: Python launcher not found. Install 'py' or 'python' and retry."
    exit 1
  fi
}

run_pre_push_validations

echo "Current branch: $BRANCH"
echo "Checking git status..."
git status

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
