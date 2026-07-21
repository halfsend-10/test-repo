#!/usr/bin/env bash
# dispatch-route-helpers.sh — Reference implementation of the dispatch
# routing helpers, kept in sync by hand with the inline copies in
# dispatch.yml (per-org) and reusable-dispatch.yml (per-repo).
#
# The workflows define these functions inline rather than sourcing this
# file, since sourcing would require an extra checkout step in every
# dispatch run. This file exists so the routing logic is unit-testable
# (ADR-0005) — see dispatch-route-helpers-test.sh.
#
# Required env vars (set by the caller before sourcing):
#   GITHUB_REPOSITORY  — full repo name (org/repo)
#   ORG_NAME           — repository owner / org name
#   GH_TOKEN           — GitHub token for API calls
#
# Optional env vars (used by routing callers):
#   COMMENT_USER_LOGIN, COMMENT_BODY, COMMENT_USER_TYPE,
#   COMMENT_AUTHOR_ASSOC, ISSUE_LABELS, PR_LABELS,
#   ISSUE_USER_LOGIN, PR_USER_LOGIN, EVENT_SENDER_LOGIN,
#   REVIEW_USER_LOGIN, REVIEW_STATE, TRIGGERING_LABEL,
#   PR_HEAD_REPO, PR_BASE_REPO

# Collaborator role_name vs min (write|triage). See #5223 / ADR 0054.
# API resolves org membership regardless of visibility (gh-aw-mcpg#2862).
has_repo_permission() {
  local username="${1:-}" min="${2:-write}" role api_err
  [[ -z "${username}" ]] && return 1
  api_err=$(mktemp) || {
    echo "::warning::Failed to create temp file for permission check of ${username}" >&2
    return 1
  }
  role=$(gh api "repos/${GITHUB_REPOSITORY}/collaborators/${username}/permission" \
    --jq '.role_name' 2>"${api_err}") || {
    # Sanitize before logging: a crafted API/gh-cli error containing "::"
    # could otherwise be interpreted as a GitHub Actions workflow command.
    local sanitized_err
    sanitized_err=$(tr '\n' ' ' < "${api_err}" | sed 's/::/: /g')
    echo "::warning::Permission API call failed for ${username}: ${sanitized_err}" >&2
    rm -f "${api_err}"
    return 1
  }
  rm -f "${api_err}"
  case "${role}" in
    admin|maintain|write) return 0 ;;
    triage) [[ "${min}" == "triage" ]] && return 0 || return 1 ;;
    *) return 1 ;;
  esac
}

# Slash-command auth; optional $1 = write|triage (default write).
is_authorized() {
  has_repo_permission "${COMMENT_USER_LOGIN:-}" "${1:-write}"
}

# Event-actor auth; $1=user, optional $2 = write|triage (default write).
is_event_actor_authorized() {
  has_repo_permission "${1:-}" "${2:-write}"
}

# Check whether a username is one of the org's own first-party agent bots
# (${ORG_NAME}-coder[bot], ${ORG_NAME}-review[bot], ${ORG_NAME}-triage[bot],
# etc. — any ${ORG_NAME}-*[bot]). These are GitHub App bot identities that
# the collaborator permission API does not recognize (#5188, #2636), so
# they always fail is_event_actor_authorized/has_repo_permission even
# though they have legitimate push/comment access via their app
# installation grant. The org-name prefix excludes third-party bots
# (renovate[bot], dependabot[bot], qodo-code-review[bot], etc.), which
# don't get this bypass.
is_org_bot() {
  local username="${1:-}"
  [[ -z "${username}" ]] && return 1
  [[ -z "${ORG_NAME:-}" ]] && return 1
  # Quoted glob, not a regex: ORG_NAME is matched literally (org names could
  # otherwise contain regex metacharacters) and "[bot]" isn't parsed as a
  # bracket expression.
  [[ "${username}" == "${ORG_NAME}-"*"[bot]" ]]
}

# Helper: check if user is the PR/issue author
is_issue_author() {
  [[ "${COMMENT_USER_LOGIN:-}" == "${ISSUE_USER_LOGIN:-}" ]]
}

# Helper: check if a label is present in a comma-separated list.
# Usage: has_label <name> [label_csv]  (defaults to ISSUE_LABELS)
has_label() {
  local needle="$1"
  local csv="${2:-${ISSUE_LABELS:-}}"
  IFS=',' read -ra labels <<< "${csv}"
  for l in "${labels[@]}"; do
    [[ "$l" == "$needle" ]] && return 0
  done
  return 1
}
