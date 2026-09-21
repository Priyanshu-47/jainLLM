# Task 53: VM Rollback Instructions

## Original Configuration
ORIGINAL_VM_SIZE = Standard_B2as_v2
ORIGINAL_VCPUS = 2
ORIGINAL_RAM_GB = 8
ORIGINAL_DISK_GB = 29

## Current Configuration
CURRENT_VM_SIZE = Standard_B4as_v2
CURRENT_VCPUS = 4
CURRENT_RAM_GB = 16
CURRENT_DISK_GB = 128

## How to Rollback VM Size
az vm resize --resource-group Jain --name JainVM --size Standard_B2as_v2

## How to Rollback Disk Size
Requires VM to be stopped first:
az vm stop --resource-group Jain --name JainVM
az disk update --resource-group Jain --name JainVM_OsDisk_1_b2d76675cbd44319a904e2465832caef --set diskSizeGb=29
az vm start --resource-group Jain --name JainVM

## Via Azure Portal
1. Go to https://portal.azure.com
2. Navigate to JainVM
3. Click Size to change VM size
4. Click Disks to change disk size

## Cost Impact
Standard_B2as_v2: ~\.04/hr (2 vCPU, 8GB, 29GB disk)
Standard_B4as_v2: ~\.08/hr (4 vCPU, 16GB, 128GB disk)
Difference: ~\.04/hr
