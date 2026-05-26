#!/usr/bin/env bash
set -euo pipefail

# ── Baked-in values (from Copier template) ─────────────────
PROJECT="${PROJECT:-deliverable-canvas-mcp}"
OWNER="${OWNER:-stromy-org}"
REPO="${REPO:-deliverable-canvas-mcp}"
RG="${RG:-rg-deliverable-canvas-mcp}"
REGION="${REGION:-westeurope}"

# ── Helpers ────────────────────────────────────────────────
info()  { printf '\033[0;34m[INFO]\033[0m  %s\n' "$1"; }
ok()    { printf '\033[0;32m[OK]\033[0m    %s\n' "$1"; }
warn()  { printf '\033[0;33m[WARN]\033[0m  %s\n' "$1"; }
die()   { printf '\033[0;31m[ERR]\033[0m   %s\n' "$1" >&2; exit 1; }

# ── Phase 0: Prerequisites ────────────────────────────────
check_prerequisites() {
  info "Checking prerequisites..."
  command -v az >/dev/null 2>&1 || die "Azure CLI (az) not found. Install: https://aka.ms/installazurecli"
  command -v gh >/dev/null 2>&1 || die "GitHub CLI (gh) not found. Install: https://cli.github.com"

  az account show >/dev/null 2>&1 || die "Not logged in to Azure. Run: az login"
  gh auth status >/dev/null 2>&1 || die "Not logged in to GitHub. Run: gh auth login"

  SUB_ID=$(az account show --query id -o tsv)
  TENANT_ID=$(az account show --query tenantId -o tsv)

  gh repo view "${OWNER}/${REPO}" >/dev/null 2>&1 \
    || die "GitHub repo ${OWNER}/${REPO} not found. Create it first."

  ok "Prerequisites met (subscription: ${SUB_ID})"
}

# ── Phase 1: Resource Group ───────────────────────────────
create_resource_group() {
  info "Resource group: ${RG}"
  if az group show --name "$RG" >/dev/null 2>&1; then
    ok "Resource group ${RG} already exists"
  else
    az group create --name "$RG" --location "$REGION" -o none
    ok "Created resource group ${RG} in ${REGION}"
  fi
}

# ── Phase 2: ARM Deployment ──────────────────────────────
deploy_infrastructure() {
  info "Deploying ARM template..."
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

  az deployment group create \
    --resource-group "$RG" \
    --template-file "${SCRIPT_DIR}/template.json" \
    --parameters "@${SCRIPT_DIR}/parameters.json" \
    --parameters \
      "subscriptionId=${SUB_ID}" \
      "environmentId=/subscriptions/${SUB_ID}/resourceGroups/${RG}/providers/Microsoft.App/managedEnvironments/mcp-env" \
    -o none

  ok "Infrastructure deployed (Container App + Environment + Log Analytics)"
}

# ── Phase 3: OIDC Identity ──────────────────────────────
setup_oidc_identity() {
  info "Setting up OIDC identity..."

  local mode="${1:-}"

  if [ -z "$mode" ]; then
    printf '  [1] Create a NEW app registration (%s-gha)\n' "$PROJECT"
    printf '  [2] Reuse an EXISTING app registration\n'
    printf 'Choose [1/2]: '
    read -r choice
    case "${choice:-1}" in
      2) mode="existing" ;;
      *) mode="new" ;;
    esac
  fi

  case "$mode" in
    existing)
      printf 'App display name to search [stromy-mcp-gha]: '
      read -r search_name
      search_name="${search_name:-stromy-mcp-gha}"

      az ad app list --display-name "$search_name" \
        --query "[].{name:displayName, appId:appId}" -o table

      printf 'Enter the appId to use: '
      read -r APP_ID
      [ -n "$APP_ID" ] || die "No appId provided"
      ;;
    *)
      local app_name="${PROJECT}-gha"
      found=$(az ad app list --display-name "$app_name" --query "[0].appId" -o tsv 2>/dev/null || true)

      if [ -n "$found" ]; then
        APP_ID="$found"
        ok "App registration ${app_name} already exists (${APP_ID})"
      else
        APP_ID=$(az ad app create --display-name "$app_name" --query appId -o tsv)
        ok "Created app registration ${app_name} (${APP_ID})"
      fi

      if az ad sp show --id "$APP_ID" >/dev/null 2>&1; then
        ok "Service principal already exists"
      else
        az ad sp create --id "$APP_ID" -o none
        ok "Created service principal"
      fi
      ;;
  esac
}

# ── Phase 4: Federated Credential ───────────────────────
setup_federated_credential() {
  info "Setting up federated credential..."
  local cred_name="github-${REPO}-main"

  existing=$(az ad app federated-credential list --id "$APP_ID" \
    --query "[?name=='${cred_name}'].name" -o tsv 2>/dev/null || true)

  if [ -n "$existing" ]; then
    ok "Federated credential ${cred_name} already exists"
  else
    az ad app federated-credential create --id "$APP_ID" --parameters "{
      \"name\": \"${cred_name}\",
      \"issuer\": \"https://token.actions.githubusercontent.com\",
      \"subject\": \"repo:${OWNER}/${REPO}:ref:refs/heads/main\",
      \"audiences\": [\"api://AzureADTokenExchange\"]
    }" -o none
    ok "Created federated credential ${cred_name}"
  fi
}

# ── Phase 5: Role Assignment ─────────────────────────────
setup_role_assignment() {
  info "Setting up role assignment..."
  SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)
  local scope="/subscriptions/${SUB_ID}/resourceGroups/${RG}"

  existing=$(az role assignment list \
    --assignee "$SP_OBJECT_ID" \
    --role Contributor \
    --scope "$scope" \
    --query "[0].id" -o tsv 2>/dev/null || true)

  if [ -n "$existing" ]; then
    ok "Contributor role already assigned"
  else
    az role assignment create \
      --assignee-object-id "$SP_OBJECT_ID" \
      --assignee-principal-type ServicePrincipal \
      --role Contributor \
      --scope "$scope" \
      -o none
    ok "Assigned Contributor role on ${RG}"
  fi
}

# ── Phase 6: GitHub Variables ────────────────────────────
set_github_variables() {
  info "Setting GitHub repository variables..."
  gh variable set AZURE_CLIENT_ID       --body "$APP_ID"    --repo "${OWNER}/${REPO}"
  gh variable set AZURE_TENANT_ID       --body "$TENANT_ID" --repo "${OWNER}/${REPO}"
  gh variable set AZURE_SUBSCRIPTION_ID --body "$SUB_ID"    --repo "${OWNER}/${REPO}"
  gh variable set AZURE_RESOURCE_GROUP  --body "$RG"        --repo "${OWNER}/${REPO}"
  ok "GitHub variables set"
  gh variable list --repo "${OWNER}/${REPO}"
}

# ── Phase 7: GHCR Registry ──────────────────────────────
setup_ghcr_registry() {
  info "GHCR registry credentials..."

  local pat="${GHCR_PAT:-}"
  local from_env=false

  if [ -n "$pat" ]; then
    from_env=true
  else
    printf '  Enter a GitHub PAT with read:packages scope\n'
    printf '  (or press Enter to skip and make the package public later): '
    read -rs pat
    echo
  fi

  if [ -n "$pat" ]; then
    az containerapp registry set \
      --name "$PROJECT" \
      --resource-group "$RG" \
      --server ghcr.io \
      --username "$OWNER" \
      --password "$pat" \
      -o none
    if [ "$from_env" = true ]; then
      ok "GHCR registry credentials configured (from \$GHCR_PAT)"
    else
      ok "GHCR registry credentials configured"
      warn "Tip: export GHCR_PAT in ~/.zshrc to skip this prompt next time"
    fi
  else
    warn "Skipped GHCR registry credentials"
    info "After first deploy, make the package public:"
    printf '  gh api -X PATCH /orgs/%s/packages/container/%s/visibility -f visibility=public\n' "$OWNER" "$REPO"
  fi
}

# ── Phase 8: OAuth App Registration (optional) ──────────
setup_oauth_app() {
  local enable_oauth="${1:-false}"
  [ "$enable_oauth" = "true" ] || return 0

  info "Setting up OAuth app registration..."

  local oauth_app_name="${PROJECT}-oauth"
  local oauth_app_id
  oauth_app_id=$(az ad app list --display-name "$oauth_app_name" --query "[0].appId" -o tsv 2>/dev/null || true)

  if [ -n "$oauth_app_id" ]; then
    ok "OAuth app registration ${oauth_app_name} already exists (${oauth_app_id})"
  else
    oauth_app_id=$(az ad app create \
      --display-name "$oauth_app_name" \
      --sign-in-audience "AzureADMyOrg" \
      --query appId -o tsv)
    ok "Created OAuth app registration ${oauth_app_name} (${oauth_app_id})"
  fi

  if az ad sp show --id "$oauth_app_id" >/dev/null 2>&1; then
    ok "OAuth service principal already exists"
  else
    az ad sp create --id "$oauth_app_id" -o none
    ok "Created OAuth service principal"
  fi

  local oauth_object_id
  oauth_object_id=$(az ad app show --id "$oauth_app_id" --query id -o tsv)
  az rest --method PATCH \
    --url "https://graph.microsoft.com/v1.0/applications/${oauth_object_id}" \
    --headers "Content-Type=application/json" \
    --body '{"api":{"requestedAccessTokenVersion":2}}' \
    || warn "Could not set token version to v2 — set manually in Portal > Manifest"

  local app_fqdn
  app_fqdn=$(az containerapp show -n "$PROJECT" -g "$RG" \
    --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || true)

  local base_url="https://${app_fqdn}"
  if [ -z "$app_fqdn" ]; then
    base_url="http://localhost:8000"
    warn "Container App not yet deployed; using localhost for redirect URI"
  fi

  az ad app update --id "$oauth_app_id" \
    --web-redirect-uris "${base_url}/auth/callback"

  az ad app update --id "$oauth_app_id" \
    --public-client-redirect-uris "http://localhost" "http://127.0.0.1" \
    || warn "Could not set public client redirect URIs"

  local api_uri="api://${oauth_app_id}"
  az ad app update --id "$oauth_app_id" \
    --identifier-uris "$api_uri" 2>/dev/null || true

  local scope_id
  scope_id=$(uuidgen | tr '[:upper:]' '[:lower:]')
  az rest --method PATCH \
    --url "https://graph.microsoft.com/v1.0/applications/${oauth_object_id}" \
    --headers "Content-Type=application/json" \
    --body "{\"api\":{\"oauth2PermissionScopes\":[{\"adminConsentDescription\":\"Access MCP server\",\"adminConsentDisplayName\":\"MCP Access\",\"id\":\"${scope_id}\",\"isEnabled\":true,\"type\":\"User\",\"userConsentDescription\":\"Access MCP server\",\"userConsentDisplayName\":\"MCP Access\",\"value\":\"mcp.access\"}]}}" \
    || warn "Could not set API scope — may already exist"

  local secret_output
  secret_output=$(az ad app credential reset --id "$oauth_app_id" \
    --display-name "copier-generated" --years 2 --query password -o tsv)

  OAUTH_CLIENT_ID="$oauth_app_id"
  OAUTH_CLIENT_SECRET="$secret_output"
  OAUTH_TENANT_ID_VAL="$TENANT_ID"
  OAUTH_BASE_URL="$base_url"
  # Whitespace-delimited per OAuth 2.0 RFC 6749. `offline_access` is REQUIRED
  # so the connector receives a refresh token (silent re-auth) — without it,
  # users see the "Reconnect" prompt every ~1h when the access token expires.
  OAUTH_REQUIRED_SCOPES="mcp.access offline_access"

  ok "OAuth app registration complete"
}

# ── Phase 9: Write OAuth to .env ────────────────────────
write_oauth_env() {
  [ -z "${OAUTH_CLIENT_ID:-}" ] && return 0

  local env_file=".env"
  if [ ! -f "$env_file" ]; then
    cp .env.example "$env_file" 2>/dev/null || true
  fi

  cat >> "$env_file" <<EOF

# OAuth (auto-generated by setup-aca.sh)
OAUTH_ENABLE=true
OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID}
OAUTH_CLIENT_SECRET=${OAUTH_CLIENT_SECRET}
OAUTH_TENANT_ID=${OAUTH_TENANT_ID_VAL}
OAUTH_BASE_URL=${OAUTH_BASE_URL}
OAUTH_REQUIRED_SCOPES="${OAUTH_REQUIRED_SCOPES}"
EOF

  ok "OAuth credentials written to .env"
}

# ── Phase 10: Configure OAuth on ACA ───────────────────
write_oauth_aca_secrets() {
  [ -z "${OAUTH_CLIENT_ID:-}" ] && return 0

  info "Configuring OAuth on Azure Container App..."

  az containerapp secret set \
    --name "$PROJECT" --resource-group "$RG" \
    --secrets oauth-client-secret="${OAUTH_CLIENT_SECRET}" \
    -o none 2>/dev/null || warn "Could not set ACA secret — Container App may not be ready yet"

  az containerapp update \
    --name "$PROJECT" --resource-group "$RG" \
    --set-env-vars \
      OAUTH_ENABLE=true \
      OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID}" \
      OAUTH_TENANT_ID="${OAUTH_TENANT_ID_VAL}" \
      OAUTH_BASE_URL="${OAUTH_BASE_URL}" \
      OAUTH_REQUIRED_SCOPES="${OAUTH_REQUIRED_SCOPES}" \
      OAUTH_CLIENT_SECRET=secretref:oauth-client-secret \
    -o none 2>/dev/null || warn "Could not update ACA env vars — configure manually after first deploy"

  ok "OAuth configured on Azure Container App"
}

# ── Phase 11: Summary ───────────────────────────────────
print_summary() {
  echo
  printf '\033[0;32m━━━ Setup complete ━━━\033[0m\n'
  echo
  info "Next steps:"
  printf '  1. git push origin main\n'
  printf '  2. Wait for GitHub Actions to finish, then verify:\n'
  printf '     APP_FQDN=$(az containerapp show -n %s -g %s --query properties.configuration.ingress.fqdn -o tsv)\n' "$PROJECT" "$RG"
  printf '     curl https://$APP_FQDN/health\n'
}

# ── Main ─────────────────────────────────────────────────
main() {
  local oidc_mode=""
  local enable_oauth="false"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --oidc-mode) oidc_mode="$2"; shift 2 ;;
      --enable-oauth) enable_oauth="true"; shift ;;
      *) shift ;;
    esac
  done

  echo
  printf '\033[1mAzure Container Apps Setup — %s\033[0m\n' "$PROJECT"
  echo

  check_prerequisites
  create_resource_group
  deploy_infrastructure
  setup_oidc_identity "$oidc_mode"
  setup_federated_credential
  setup_role_assignment
  set_github_variables
  setup_ghcr_registry
  setup_oauth_app "$enable_oauth"
  write_oauth_env
  write_oauth_aca_secrets
  print_summary
}

main "$@"
