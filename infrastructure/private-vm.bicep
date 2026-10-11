targetScope = 'resourceGroup'

@description('Existing private subnet with a verified VPN/private operator route and outbound package access. No public IP is created.')
param subnetId string
param location string = resourceGroup().location
param vmName string = 'dq-monitor'
param vmSize string = 'Standard_B2als_v2'
param adminUsername string = 'dqoperator'
@description('Public SSH key only. Never supply a private key.')
param sshPublicKey string
@description('Private operator source CIDR; restrict to the approved VPN client range.')
param operatorCidr string

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: '${vmName}-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'ssh-private-operator'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: operatorCidr
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'deny-other-inbound'
        properties: {
          priority: 200
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}
resource nic 'Microsoft.Network/networkInterfaces@2024-05-01' = {
  name: '${vmName}-nic'
  location: location
  properties: {
    networkSecurityGroup: { id: nsg.id }
    ipConfigurations: [
      {
        name: 'private'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: { id: subnetId }
        }
      }
    ]
  }
}
resource vm 'Microsoft.Compute/virtualMachines@2024-07-01' = {
  name: vmName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    hardwareProfile: { vmSize: vmSize }
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        provisionVMAgent: true
        ssh: {
          publicKeys: [{ path: '/home/${adminUsername}/.ssh/authorized_keys', keyData: sshPublicKey }]
        }
      }
    }
    storageProfile: {
      imageReference: { publisher: 'Canonical', offer: 'ubuntu-24_04-lts', sku: 'server', version: 'latest' }
      osDisk: {
        createOption: 'FromImage'
        diskSizeGB: 32
        managedDisk: { storageAccountType: 'StandardSSD_LRS' }
        deleteOption: 'Detach'
      }
      dataDisks: [
        {
          lun: 0
          name: '${vmName}-monitoring'
          createOption: 'Empty'
          diskSizeGB: 32
          caching: 'None'
          managedDisk: { storageAccountType: 'StandardSSD_LRS' }
          deleteOption: 'Detach'
        }
      ]
    }
    networkProfile: { networkInterfaces: [{ id: nic.id }] }
    securityProfile: {
      securityType: 'TrustedLaunch'
      uefiSettings: { secureBootEnabled: true, vTpmEnabled: true }
    }
    diagnosticsProfile: { bootDiagnostics: { enabled: false } }
  }
}
output vmId string = vm.id
output privateIp string = nic.properties.ipConfigurations[0].properties.privateIPAddress
