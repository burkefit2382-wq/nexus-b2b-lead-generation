param environmentName string
param location string
param tags object

var appServicePlanName = 'asp-${environmentName}'
var apiAppName = 'api-${environmentName}'
var staticWebAppName = 'web-${environmentName}'

// Linux App Service Plan (B1) for the FastAPI backend
resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: 'B1'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// Python App Service for the FastAPI backend
resource apiApp 'Microsoft.Web/sites@2022-03-01' = {
  name: apiAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000'
    }
    httpsOnly: true
  }
}

// Static Web App for the Vite + TypeScript frontend
resource staticWebApp 'Microsoft.Web/staticSites@2022-03-01' = {
  name: staticWebAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {}
}

output API_URI string = 'https://${apiApp.properties.defaultHostName}'
output WEB_URI string = 'https://${staticWebApp.properties.defaultHostname}'
