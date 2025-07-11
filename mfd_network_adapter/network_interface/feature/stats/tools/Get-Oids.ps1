<#
  Copyright (C) 2025 Intel Corporation
  SPDX-License-Identifier: MIT
 .Synopsis
  Gets all OID values from a network adapter.

 .Description
  Gets all OID values from a network adapter. Will return false or an
  error message if it fails (adapter not found). On success a dictionary
  is returned containing OID names and values.

 .Parameter adapter_name
  Friendly name of the adapter.

 .Parameter oid_name
  Only return OIDs where the Name field equals the name of the OID.

 .Example
  .\Get-Oids.ps1 TestAdapter2
  .\Get-Oids.ps1 TestAdapter2 -oid_name "OID_GEN_BROADCAST_FRAMES_XMIT"
#>
param (
    [Parameter(Mandatory = $True)][string]$adapter_name,
    [Parameter(Mandatory = $False)][string]$oid_name = ""
)

Add-Type -Path "$PSScriptRoot\Adapter.dll"
$adp = New-Object -Type "Intel.Network.Adapter"
$ret = $adp.GetAdapter($adapter_name, $( "$PSScriptRoot\oids.xml" ))

if ($ret.Passed -ne $true)
{
    return $ret.Description
}

$a = $ret.FunctionReturnValue

$oids = $a.Oids.GetOids()
$table = @{
}
foreach ($oid in $oids.GetEnumerator())
{
    $table.Add($oid.Key,$oid.Value.GetCurrentValue())
}

if ($oid_name -ne "")
{
    $table = $table.GetEnumerator() | Where-Object {$_.Name -eq $oid_name}
}

return $table | Format-List