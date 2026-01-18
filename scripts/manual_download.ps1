# Manual Fairy-Stockfish Download Script for Windows
# Use this if the automatic script fails

Write-Host "=== Manual Fairy-Stockfish Download ===" -ForegroundColor Green

# Create directory
$installDir = "C:\fairy-stockfish"
if (!(Test-Path $installDir)) {
	New-Item -ItemType Directory -Path $installDir -Force
}

Write-Host "Installation directory: $installDir" -ForegroundColor Cyan

# Direct download URLs for common versions
$downloadUrls = @(
	"https://github.com/fairy-stockfish/Fairy-Stockfish/releases/download/fairy_sf_14/fairy-stockfish-x86_64.exe",
	"https://github.com/fairy-stockfish/Fairy-Stockfish/releases/download/fairy_sf_13/fairy-stockfish-x86_64.exe",
	"https://github.com/fairy-stockfish/Fairy-Stockfish/releases/download/fairy_sf_12/fairy-stockfish-x86_64.exe"
)

$downloaded = $false

foreach ($url in $downloadUrls) {
	try {
		Write-Host "Trying: $url" -ForegroundColor Yellow
		$filename = Split-Path $url -Leaf
		$filePath = Join-Path $installDir "fairy-stockfish.exe"
        
		Invoke-WebRequest -Uri $url -OutFile $filePath -UseBasicParsing
		$downloaded = $true
		Write-Host "Downloaded successfully!" -ForegroundColor Green
		break
	}
 catch {
		Write-Host "Failed: $_" -ForegroundColor Red
		continue
	}
}

if ($downloaded) {
	# Test the executable
	$exePath = Join-Path $installDir "fairy-stockfish.exe"
	Write-Host "Testing installation..." -ForegroundColor Yellow
    
	try {
		& $exePath --version
		Write-Host "Fairy-Stockfish installed successfully!" -ForegroundColor Green
		Write-Host "Location: $exePath" -ForegroundColor Cyan
        
		# Add to PATH instruction
		Write-Host "`nTo use from anywhere, add this to your PATH:" -ForegroundColor Yellow
		Write-Host "  $installDir" -ForegroundColor White
        
		# Update Python code to use full path
		Write-Host "`nIn Python, use this path:" -ForegroundColor Yellow
		Write-Host "  stockfish_path = r'$exePath'" -ForegroundColor White
        
	}
 catch {
		Write-Host "Installation test failed" -ForegroundColor Red
		Write-Host "You may need to run: $exePath" -ForegroundColor Yellow
	}
}
else {
	Write-Host "All download attempts failed" -ForegroundColor Red
	Write-Host "Please download manually from:" -ForegroundColor Yellow
	Write-Host "https://github.com/fairy-stockfish/Fairy-Stockfish/releases" -ForegroundColor Cyan
	Write-Host "And save as: $installDir\fairy-stockfish.exe" -ForegroundColor White
}

Write-Host "`n=== Manual Download Complete ===" -ForegroundColor Green
