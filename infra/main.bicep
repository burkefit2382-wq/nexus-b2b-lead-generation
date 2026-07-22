targetScope = 'subscription'

@minLength(2)
@maxLength(39)
@description('Name of the environment (e.g. dev, prod)')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@secure()
param stripeSecretKey string = ''

@secure()
param stripeWebhookSecret string = ''

@secure()
param priceId string = ''

@secure()
param databaseUrl string = ''

@secure()
param resendApiKey string = ''

param resendFrom string = ''

param waitlistNotifyTo string = ''

@secure()
param hubspotAccessToken string = ''

param hubspotPortalId string = ''

param runtimeEnvironment string = 'production'

var tags = { 'azd-env-name': environmentName }
var resourceGroupName = 'rg-${environmentName}'

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module resources './resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    environmentName: environmentName
    location: location
    tags: tags
    stripeSecretKey: stripeSecretKey
    stripeWebhookSecret: stripeWebhookSecret
    priceId: priceId
    databaseUrl: databaseUrl
    resendApiKey: resendApiKey
    resendFrom: resendFrom
    waitlistNotifyTo: waitlistNotifyTo
    hubspotAccessToken: hubspotAccessToken
    hubspotPortalId: hubspotPortalId
    runtimeEnvironment: runtimeEnvironment
  }
}

output API_URI string = resources.outputs.API_URI
output WEB_URI string = resources.outputs.WEB_URI
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.AZURE_CONTAINER_REGISTRY_ENDPOINT
