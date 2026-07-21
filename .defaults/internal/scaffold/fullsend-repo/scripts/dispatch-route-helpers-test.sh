#!/usr/bin/env bash
# dispatch-route-helpers-test.sh — Tests for dispatch-route-helpers.sh
#
# Run from the repo root:
#   bash internal/scaffold/fullsend-repo/scripts/dispatch-route-helpers-test.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPERS="${SCRIPT_DIR}/dispatch-route-helpers.sh"
FAILURES=0

# --- Helpers ---

run_test() {
  local test_name="$1"
  local expected_rc="$2"  # expected return code
  local func_call="$3"    # function name + args
  local env_overrides="${4:-}"

  # Build env array
  local env_cmd=(
    env
    GITHUB_REPOSITORY="test-org/test-repo"
    ORG_NAME="test-org"
    GH_TOKEN="fake-token"
    COMMENT_USER_LOGIN=""
    ISSUE_USER_LOGIN=""
    ISSUE_LABELS=""
  )

  if [[ -n "${env_overrides}" ]]; then
    while IFS= read -r kv; do
      [[ -n "${kv}" ]] && env_cmd+=("${kv}")
    done <<< "${env_overrides}"
  fi

  local actual_rc=0
  # Source the helpers and call the function in a subshell
  "${env_cmd[@]}" bash -c "
    source '${HELPERS}'
    ${func_call}
  " > /dev/null 2>&1 || actual_rc=$?

  if [[ "${actual_rc}" -ne "${expected_rc}" ]]; then
    echo "FAIL: ${test_name} — expected rc=${expected_rc}, got rc=${actual_rc}"
    FAILURES=$((FAILURES + 1))
    return
  fi

  echo "PASS: ${test_name}"
}

# --- is_org_bot tests ---

# Org coder bot matches
run_test "is_org_bot: coder bot matches" 0 \
  'is_org_bot "test-org-coder[bot]"'

# Org code bot matches
run_test "is_org_bot: code bot matches" 0 \
  'is_org_bot "test-org-code[bot]"'

# Random bot does not match
run_test "is_org_bot: random bot rejected" 1 \
  'is_org_bot "random-bot[bot]"'

# Human user does not match
run_test "is_org_bot: human user rejected" 1 \
  'is_org_bot "human-dev"'

# Empty username returns 1
run_test "is_org_bot: empty username rejected" 1 \
  'is_org_bot ""'

# No argument returns 1
run_test "is_org_bot: no argument rejected" 1 \
  'is_org_bot'

# Empty ORG_NAME returns 1
run_test "is_org_bot: empty ORG_NAME rejected" 1 \
  'is_org_bot "test-org-coder[bot]"' \
  "ORG_NAME="

# Different org bot does not match
run_test "is_org_bot: different org rejected" 1 \
  'is_org_bot "other-org-coder[bot]"'

# Any org-prefixed first-party agent bot matches, not just coder/code
run_test "is_org_bot: review bot matches" 0 \
  'is_org_bot "test-org-review[bot]"'

run_test "is_org_bot: triage bot matches" 0 \
  'is_org_bot "test-org-triage[bot]"'

run_test "is_org_bot: retro bot matches" 0 \
  'is_org_bot "test-org-retro[bot]"'

run_test "is_org_bot: prioritize bot matches" 0 \
  'is_org_bot "test-org-prioritize[bot]"'

# Third-party bots without the org prefix are rejected even though they
# end in [bot]
run_test "is_org_bot: third-party bot rejected" 1 \
  'is_org_bot "renovate[bot]"'

# ORG_NAME is matched literally, not as a regex fragment — an org name
# containing regex metacharacters must not be treated as a pattern
run_test "is_org_bot: org name with regex metacharacters matches literally" 0 \
  'is_org_bot "a+b.c-coder[bot]"' \
  "ORG_NAME=a+b.c"

run_test "is_org_bot: regex-metachar org name rejects unrelated bot" 1 \
  'is_org_bot "abXc-coder[bot]"' \
  "ORG_NAME=a+b.c"

# --- has_label tests ---

run_test "has_label: label present" 0 \
  'has_label "bug"' \
  "ISSUE_LABELS=bug,enhancement,ready-to-code"

run_test "has_label: label absent" 1 \
  'has_label "feature"' \
  "ISSUE_LABELS=bug,enhancement"

run_test "has_label: empty labels" 1 \
  'has_label "bug"' \
  "ISSUE_LABELS="

run_test "has_label: custom csv" 0 \
  'has_label "ready-for-review" "ready-for-review,bug"'

run_test "has_label: custom csv miss" 1 \
  'has_label "ready-for-review" "bug,enhancement"'

# has_label must not hard-fail under `set -u` when ISSUE_LABELS is truly
# unset (not just empty) — regression test, since the caller documents
# ISSUE_LABELS as optional but workflows source this under set -euo pipefail.
actual_rc=0
stderr_output=$(env -u ISSUE_LABELS GITHUB_REPOSITORY="test-org/test-repo" ORG_NAME="test-org" GH_TOKEN="fake-token" \
  bash -c "set -u; source '${HELPERS}'; has_label 'bug'" 2>&1 >/dev/null) || actual_rc=$?
if [[ "${actual_rc}" -eq 1 && "${stderr_output}" != *"unbound variable"* ]]; then
  echo "PASS: has_label: unset ISSUE_LABELS under set -u returns 1, not unbound-variable error"
else
  echo "FAIL: has_label: unset ISSUE_LABELS under set -u — expected clean rc=1, got rc=${actual_rc} stderr=${stderr_output}"
  FAILURES=$((FAILURES + 1))
fi

# --- is_issue_author tests ---

run_test "is_issue_author: matching" 0 \
  'is_issue_author' \
  "$(printf '%s\n%s' 'COMMENT_USER_LOGIN=alice' 'ISSUE_USER_LOGIN=alice')"

run_test "is_issue_author: not matching" 1 \
  'is_issue_author' \
  "$(printf '%s\n%s' 'COMMENT_USER_LOGIN=alice' 'ISSUE_USER_LOGIN=bob')"

# --- Summary ---

echo ""
if [[ ${FAILURES} -gt 0 ]]; then
  echo "${FAILURES} test(s) failed"
  exit 1
fi
echo "All tests passed"
