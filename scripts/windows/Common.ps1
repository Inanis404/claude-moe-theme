Set-StrictMode -Version Latest
$script:AtelierProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
function Invoke-AtelierWsl {
    param([string]$Distro, [string]$LinuxUser, [string[]]$Command)
    $options = @()
    if ($Distro) { $options += @('-d', $Distro) }
    if ($LinuxUser) { $options += @('-u', $LinuxUser) }
    $result = & wsl.exe @options --exec @Command
    if ($LASTEXITCODE -ne 0) { throw "WSL command failed with exit code $LASTEXITCODE." }
    return $result
}
function Get-AtelierTarget {
    param([string]$Distro, [string]$LinuxUser)
    $saved = Join-Path $script:AtelierProjectRoot '.local\windows.json'
    if (Test-Path -LiteralPath $saved) {
        $config = Get-Content -LiteralPath $saved -Raw | ConvertFrom-Json
        if (-not $Distro) { $Distro = $config.distro }
        if (-not $LinuxUser -and $Distro -eq $config.distro) { $LinuxUser = $config.linuxUser }
    }
    if (-not $Distro) { $Distro = (Invoke-AtelierWsl -Command @('printenv', 'WSL_DISTRO_NAME') | Out-String).Trim() }
    if ($Distro -notmatch '^[A-Za-z0-9._ -]+$') { throw 'Invalid WSL distribution name.' }
    if (-not $LinuxUser) { $LinuxUser = (Invoke-AtelierWsl -Distro $Distro -Command @('id', '-un') | Out-String).Trim() }
    if ($LinuxUser -eq 'root' -or $LinuxUser -notmatch '^[a-z_][a-z0-9_-]*[$]?$') { throw 'Choose a regular Linux account, not root.' }
    $linuxRoot = (Invoke-AtelierWsl -Distro $Distro -LinuxUser $LinuxUser -Command @('wslpath', '-a', '-u', $script:AtelierProjectRoot) | Out-String).Trim()
    if (-not $linuxRoot.StartsWith('/')) { throw 'Cannot resolve the project directory in WSL.' }
    return [PSCustomObject]@{Distro=$Distro; LinuxUser=$LinuxUser; LinuxRoot=$linuxRoot}
}
function ConvertTo-AtelierArgument([string]$Value) {
    if ($Value -match '[\x00\r\n]') { throw 'Invalid argument.' }
    if ($Value.Length -gt 0 -and $Value -notmatch '[\s"]') { return $Value }
    # Windows command-line quoting; no shell interpretation or command substitution.
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}
function Save-AtelierTarget($Target) {
    $local = Join-Path $script:AtelierProjectRoot '.local'
    [System.IO.Directory]::CreateDirectory($local) | Out-Null
    $text = @{distro=$Target.Distro;linuxUser=$Target.LinuxUser} | ConvertTo-Json
    [System.IO.File]::WriteAllText((Join-Path $local 'windows.json'), $text, (New-Object System.Text.UTF8Encoding($false)))
}
