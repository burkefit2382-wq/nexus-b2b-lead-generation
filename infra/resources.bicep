@minLength(2)
@maxLength(39)
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

var containerAppsEnvironmentName = 'cae-${environmentName}'
var apiContainerAppName = 'api-${environmentName}'
var registryName = 'acr${replace(environmentName, '-', '')}nexus'
var staticWebAppName = 'web-${environmentName}'

// Azure Container Registry for azd remote Docker builds.
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

// Container Apps environment for the Dockerized backend.
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppsEnvironmentName
  location: location
  tags: tags
  properties: {}
}

// Container App for the NEXUS backend API. azd deploy replaces the initial image.
resource apiContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: apiContainerAppName
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 4173
        transport: 'auto'
      }
      secrets: [
        {
          name: 'stripe-secret-key'
          value: stripeSecretKey
        }
        {
          name: 'stripe-webhook-secret'
          value: stripeWebhookSecret
        }
        {
          name: 'price-id'
          value: priceId
        }
        {
          name: 'database-url'
          value: databaseUrl
        }
        {
          name: 'resend-api-key'
          value: resendApiKey
        }
        {
          name: 'hubspot-access-token'
          value: hubspotAccessToken
        }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: [
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
              secretRef: 'stripe-secret-key'
            }
            {
              name: 'STRIPE_WEBHOOK_SECRET'
              secretRef: 'stripe-webhook-secret'
            }
            {
              name: 'PRICE_ID'
              secretRef: 'price-id'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'RESEND_API_KEY'
              secretRef: 'resend-api-key'
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
              secretRef: 'hubspot-access-token'
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
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, apiContainerApp.id, 'AcrPull')
  scope: containerRegistry
  properties: {
    principalId: apiContainerApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
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

output API_URI string = 'https://${apiContainerApp.properties.configuration.ingress.fqdn}'
output WEB_URI string = 'https://${staticWebApp.properties.defaultHostname}'
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.properties.loginServer
