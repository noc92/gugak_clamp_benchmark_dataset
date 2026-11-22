[CmdletBinding()]
param(
    [switch]$AllowPartial
)

$ErrorActionPreference = 'Stop'

$bash = 'C:\Program Files\Git\bin\bash.exe'
$aihubshell = 'C:\Users\jeide\Downloads\aihubshell'
$datasetKey = '71955'
$destination = Join-Path (Split-Path -Parent $PSScriptRoot) 'data\label_download'

if (-not (Test-Path -LiteralPath $bash)) {
    throw "Git Bash not found: $bash"
}
if (-not (Test-Path -LiteralPath $aihubshell)) {
    throw "aihubshell not found: $aihubshell"
}

Write-Host 'Reading AI-Hub file list...'
$expectedLabels = 1004
$fileListUri = 'https://aihub.or.kr/aihubdata/data/aJaxS3FileList.do'
$response = Invoke-RestMethod -Uri $fileListUri -Method Post -Body @{
    dataSetSn = $datasetKey
    dataPckageSn = ''
}
if (-not $response.success) {
    throw "AI-Hub file-list API failed: $($response.msg)"
}

$labelRows = @(
    $response.list |
        Where-Object { $_.fileStreCours -match '/(?:TL|VL)_[^/]+\.zip$' } |
        ForEach-Object {
            [pscustomobject]@{
                Name = Split-Path $_.fileStreCours -Leaf
                Size = $_.fileSize
                FileKey = [string]$_.fileSn
            }
        } |
        Sort-Object Name
)

if ($labelRows.Count -eq 0) {
    throw 'No TL/VL label archives were found. Nothing will be downloaded.'
}
$trainingCount = @($labelRows | Where-Object Name -Like 'TL_*').Count
$validationCount = @($labelRows | Where-Object Name -Like 'VL_*').Count
$fileKeyArgument = $labelRows.FileKey -join ','

Write-Host "Found $($labelRows.Count) label archives (TL=$trainingCount, VL=$validationCount)."
Write-Host "Destination: $destination"
if ($labelRows.Count -lt $expectedLabels) {
    Write-Warning "AI-Hub exposes only $($labelRows.Count) of the $expectedLabels stated label archives through its file-list API."
    if (-not $AllowPartial) {
        throw "Incomplete label list. Download aborted before API-key input. Use -AllowPartial only if you explicitly accept a partial dataset."
    }
    Write-Warning 'Proceeding with a partial label download because -AllowPartial was specified.'
}

$secureApiKey = Read-Host 'Enter AI-Hub API key (input is hidden)' -AsSecureString
$apiKeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureApiKey)

try {
    $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($apiKeyPointer).Trim()
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        throw 'API key was empty.'
    }
    if ($apiKey -match '[\x00-\x1F\x7F]') {
        throw 'API key contains a control character. At the hidden prompt, do not use Ctrl+V; use terminal right-click Paste or type the key.'
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    Push-Location $destination
    try {
        # Windows PowerShell 5.1 turns normal native stderr output (curl progress)
        # into NativeCommandError when the global preference is Stop.
        $previousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $downloadOutput = @(& $bash $aihubshell `
                -mode d `
                -datasetkey $datasetKey `
                -filekey $fileKeyArgument `
                -aihubapikey $apiKey 2>&1)
            $downloadExitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        $downloadOutput | ForEach-Object { Write-Host $_ }
        $downloadText = $downloadOutput -join "`n"
        if ($downloadText -match 'Download failed with HTTP status 502') {
            throw 'AI-Hub rejected authentication or dataset access. Confirm both: (1) an issued AI-Hub Open API key, and (2) approved download access for dataset 71955.'
        }
        if (
            $downloadExitCode -ne 0 -or
            $downloadText -match 'Download failed|HTTP Status [45]\d\d|Authentication failed'
        ) {
            throw "aihubshell download failed (exit code $downloadExitCode). See the error output above."
        }
    } finally {
        Pop-Location
    }
} finally {
    if ($apiKeyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($apiKeyPointer)
    }
    Remove-Variable apiKey -ErrorAction SilentlyContinue
    Remove-Variable secureApiKey -ErrorAction SilentlyContinue
}

Write-Host 'Label download completed.'
