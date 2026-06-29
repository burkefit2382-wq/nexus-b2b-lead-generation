targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment (e.g. dev, prod)')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

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
  }
}

output API_URI string = resources.outputs.API_URI
output WEB_URI string = resources.outputs.WEB_URI
