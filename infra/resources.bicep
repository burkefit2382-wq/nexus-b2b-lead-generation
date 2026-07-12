param environmentName string
param location string
param tags object

@secure()
param stripeSecretKey string

@secure()
param stripeWebhookSecret string

@secure()
param priceId string

@secure()
param databaseUrl string

@secure()
param resendApiKey string

param resendFrom string
param waitlistNotifyTo string

@secure()
param hubspotAccessToken string

param hubspotPortalId string
param runtimeEnvironment string

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
      appCommandLine: 'python main.py'
      appSettings: [
        {
          name: 'LAUNCH_HOST'
          value: '0.0.0.0'
        }
        {
          name: 'PUBLIC_BASE_URL'
          value: 'https://${staticWebApp.properties.defaultHostname}'
        }
        {
          name: 'TRACKING_ALLOWED_ORIGIN'
          value: 'https://${staticWebApp.properties.defaultHostname}'
        }
        {
          name: 'STRIPE_SECRET_KEY'
          value: stripeSecretKey
        }
        {
          name: 'STRIPE_WEBHOOK_SECRET'
          value: stripeWebhookSecret
        }
        {
          name: 'PRICE_ID'
          value: priceId
        }
        {
          name: 'DATABASE_URL'
          value: databaseUrl
        }
        {
          name: 'RESEND_API_KEY'
          value: resendApiKey
        }
        {
          name: 'RESEND_FROM'
          value: resendFrom
        }
        {
          name: 'WAITLIST_NOTIFY_TO'
          value: waitlistNotifyTo
        }
        {
          name: 'HUBSPOT_ACCESS_TOKEN'
          value: hubspotAccessToken
        }
        {
          name: 'HUBSPOT_PORTAL_ID'
          value: hubspotPortalId
        }
        {
          name: 'ENVIRONMENT'
          value: runtimeEnvironment
        }
      ]
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
