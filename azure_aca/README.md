# Azure Container Apps — Deliverable Canvas MCP

Automated setup script or manual commands to deploy the MCP server to Azure Container Apps.

## Quick setup

```bash
bash azure_aca/setup-aca.sh
```

All steps are idempotent — safe to re-run.

## Prerequisites

```bash
az login
gh auth login
```

## Step-by-step commands

If the setup script did not run (or you prefer manual control), execute the following in order.

### 1. Resource Group

```bash
az group create --name rg-deliverable-canvas-mcp --location westeurope
```

### 2. ARM deployment

```bash
az deployment group create \
  --resource-group rg-deliverable-canvas-mcp \
  --template-file azure_aca/template.json \
  --parameters @azure_aca/parameters.json \
  --parameters \
    "subscriptionId=$(az account show --query id -o tsv)" \
    "environmentId=/subscriptions/$(az account show --query id -o tsv)/resourceGroups/rg-deliverable-canvas-mcp/providers/Microsoft.App/managedEnvironments/mcp-env"
```

This creates: Log Analytics workspace, Container Apps Environment, and a Container App with scale-to-zero on port 8080.

### 3. OIDC identity (GitHub → Azure trust)

```bash
APP_ID=$(az ad app create --display-name "deliverable-canvas-mcp-gha" --query appId -o tsv)
az ad sp create --id $APP_ID
```

### 4. Federated credential

```bash
az ad app federated-credential create --id $APP_ID --parameters "{
  \"name\": \"github-deliverable-canvas-mcp-main\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:stromy-org/deliverable-canvas-mcp:ref:refs/heads/main\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}"
```

### 5. Role assignment

```bash
SUB_ID=$(az account show --query id -o tsv)
SP_OBJECT_ID=$(az ad sp show --id $APP_ID --query id -o tsv)

az role assignment create \
  --assignee-object-id $SP_OBJECT_ID \
  --assignee-principal-type ServicePrincipal \
  --role Contributor \
  --scope "/subscriptions/$SUB_ID/resourceGroups/rg-deliverable-canvas-mcp"
```

### 6. GitHub repo variables

```bash
TENANT_ID=$(az account show --query tenantId -o tsv)

gh variable set AZURE_CLIENT_ID       --body "$APP_ID"    --repo "stromy-org/deliverable-canvas-mcp"
gh variable set AZURE_TENANT_ID       --body "$TENANT_ID" --repo "stromy-org/deliverable-canvas-mcp"
gh variable set AZURE_SUBSCRIPTION_ID --body "$SUB_ID"    --repo "stromy-org/deliverable-canvas-mcp"
gh variable set AZURE_RESOURCE_GROUP  --body "rg-deliverable-canvas-mcp" --repo "stromy-org/deliverable-canvas-mcp"
```

### 7. GHCR registry credentials

For private repos, create a GitHub PAT with `read:packages` scope:

```bash
export GHCR_PAT=ghp_...  # add to ~/.zshrc for persistence

az containerapp registry set \
  --name deliverable-canvas-mcp \
  --resource-group rg-deliverable-canvas-mcp \
  --server ghcr.io \
  --username stromy-org \
  --password $GHCR_PAT
```

For public repos, skip credentials and make the package public after first deploy:

```bash
gh api -X PATCH /orgs/stromy-org/packages/container/deliverable-canvas-mcp/visibility -f visibility=public
```


## After setup

```bash
git push origin main

# Verify after GitHub Actions completes:
APP_FQDN=$(az containerapp show -n deliverable-canvas-mcp -g rg-deliverable-canvas-mcp --query properties.configuration.ingress.fqdn -o tsv)
curl https://$APP_FQDN/health
```

## Cost

With `minReplicas: 0` and Consumption plan, idle cost is ~$0. Set `minReplicas: 1` for always-on (~$5/mo).
