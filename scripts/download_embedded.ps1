# Download Fairy-Stockfish to embedded engines folder
# This script downloads the engine directly into your project

Write-Host "=== Downloading Fairy-Stockfish to Project ===" -ForegroundColor Green

# Get project root
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$enginesDir = Join-Path $projectRoot "engines"

# Create engines directory
if (!(Test-Path $enginesDir)) {
	New-Item -ItemType Directory -Path $enginesDir -Force
	Write-Host "Created engines directory: $enginesDir"
}

# Target file path
$targetPath = Join-Path $enginesDir "stockfish.exe"

# Direct download URLs (try multiple versions)
$downloadUrls = @(
	"https://github.com/fairy-stockfish/Fairy-Stockfish/releases/download/fairy_sf_14/fairy-stockfish-largeboard_x86-64-bmi2.exe",
	"https://github.com/fairy-stockfish/Fairy-Stockfish/releases/download/fairy_sf_13/fairy-stockfish-largeboard_x86-64-bmi2.exe",
	"https://github.com/fairy-stockfish/Fairy-Stockfish/releases/download/fairy_sf_12/fairy-stockfish-largeboard_x86-64-bmi2.exe"
)

$downloaded = $false

foreach ($url in $downloadUrls) {
	try {
		Write-Host "Downloading: $url" -ForegroundColor Yellow
		Write-Host "Target: $targetPath" -ForegroundColor Cyan
        
		Invoke-WebRequest -Uri $url -OutFile $targetPath -UseBasicParsing
		$downloaded = $true
		Write-Host "Download successful!" -ForegroundColor Green
		break
	}
 catch {
		Write-Host "Failed: $_" -ForegroundColor Red
		continue
	}
}

if ($downloaded) {
	# Test the executable
	Write-Host "Testing embedded engine..." -ForegroundColor Yellow
    
	try {
		& $targetPath --version
		Write-Host "✅ Fairy-Stockfish embedded successfully!" -ForegroundColor Green
		Write-Host "Location: $targetPath" -ForegroundColor Cyan
        
		# Update .gitignore to exclude the executable
		$gitignorePath = Join-Path $projectRoot ".gitignore"
		if (Test-Path $gitignorePath) {
			$gitignoreContent = Get-Content $gitignorePath
			if ("engines/stockfish.exe" -notin $gitignoreContent) {
				Add-Content -Path $gitignorePath -Value "`n# Embedded chess engines`nengines/stockfish.exe"
				Write-Host "Added to .gitignore" -ForegroundColor Yellow
			}
		}
        
		Write-Host "`n🎯 Ready to use!" -ForegroundColor Green
		Write-Host "The Drawback Chess Engine will automatically find and use this embedded engine." -ForegroundColor White
        
	}
 catch {
		Write-Host "⚠️  Downloaded but test failed" -ForegroundColor Yellow
		Write-Host "The file may be corrupted or incompatible" -ForegroundColor Red
	}
}
else {
	Write-Host "❌ All download attempts failed" -ForegroundColor Red
	Write-Host "`nManual installation:" -ForegroundColor Yellow
	Write-Host "1. Download: fairy-stockfish-largeboard_x86-64-bmi2.exe" -ForegroundColor White
	Write-Host "2. From: https://github.com/fairy-stockfish/Fairy-Stockfish/releases" -ForegroundColor White
	Write-Host "3. Save as: $targetPath" -ForegroundColor White
}

Write-Host "`n=== Download Complete ===" -ForegroundColor Green
