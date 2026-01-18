#!/bin/bash
# Fairy-Stockfish Installation Script for Linux/macOS
# Run with: bash install_fairy_stockfish.sh

set -e

echo "=== Fairy-Stockfish Installation for Linux/macOS ==="

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

# Create installation directory
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

echo "Installation directory: $INSTALL_DIR"
echo "OS: $OS"
echo "Architecture: $ARCH"

# Determine binary name based on architecture
if [[ "$ARCH" == "x86_64" ]]; then
    BINARY_PATTERN="x86_64"
elif [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
    BINARY_PATTERN="arm64"
else
    echo "Unsupported architecture: $ARCH"
    echo "Please compile from source: https://github.com/fairy-stockfish/Fairy-Stockfish"
    exit 1
fi

# Get latest release info
echo "Fetching latest Fairy-Stockfish release..."
RELEASE_INFO=$(curl -s https://api.github.com/repos/fairy-stockfish/Fairy-Stockfish/releases/latest)
VERSION=$(echo "$RELEASE_INFO" | grep '"tag_name"' | sed -E 's/.*"tag_name": "([^"]+)".*/\1/')

echo "Latest version: $VERSION"

# Find appropriate binary
DOWNLOAD_URL=$(echo "$RELEASE_INFO" | grep -o '"browser_download_url": "[^"]*' | sed -E 's/.*"([^"]+)".*/\1/' | grep "$BINARY_PATTERN" | head -1)

if [[ -z "$DOWNLOAD_URL" ]]; then
    echo "Binary not found for architecture: $BINARY_PATTERN"
    echo "Available download URLs:"
    echo "$RELEASE_INFO" | grep -o '"browser_download_url": "[^"]*' | sed -E 's/.*"([^"]+)".*/\1/'
    echo ""
    echo "Please download manually from: https://github.com/fairy-stockfish/Fairy-Stockfish/releases"
    exit 1
fi

# Determine filename
FILENAME=$(basename "$DOWNLOAD_URL")
TEMP_FILE="/tmp/$FILENAME"

echo "Downloading: $FILENAME"
echo "URL: $DOWNLOAD_URL"

# Download the binary
curl -L "$DOWNLOAD_URL" -o "$TEMP_FILE"

# Make executable
chmod +x "$TEMP_FILE"

# Install to local bin
if [[ "$FILENAME" == *.zip ]] || [[ "$FILENAME" == *.tar.* ]]; then
    # Extract archive
    echo "Extracting archive..."
    cd /tmp
    
    if [[ "$FILENAME" == *.zip ]]; then
        unzip -q "$TEMP_FILE"
    else
        tar -xf "$TEMP_FILE"
    fi
    
    # Find the executable
    EXECUTABLE=$(find . -name "stockfish" -o -name "fairy-stockfish" -type f | head -1)
    
    if [[ -z "$EXECUTABLE" ]]; then
        echo "Executable not found in archive"
        exit 1
    fi
    
    # Copy to installation directory
    cp "$EXECUTABLE" "$INSTALL_DIR/fairy-stockfish"
    chmod +x "$INSTALL_DIR/fairy-stockfish"
    
    echo "Fairy-Stockfish installed to: $INSTALL_DIR/fairy-stockfish"
else
    # Direct binary
    mv "$TEMP_FILE" "$INSTALL_DIR/fairy-stockfish"
    echo "Fairy-Stockfish installed to: $INSTALL_DIR/fairy-stockfish"
fi

# Add to PATH if not already there
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "Adding $INSTALL_DIR to PATH..."
    
    # Determine shell profile file
    if [[ "$OS" == "Darwin" ]]; then
        PROFILE="$HOME/.zshrc"
        if [[ ! -f "$PROFILE" ]]; then
            PROFILE="$HOME/.bash_profile"
        fi
    else
        PROFILE="$HOME/.bashrc"
        if [[ ! -f "$PROFILE" ]]; then
            PROFILE="$HOME/.profile"
        fi
    fi
    
    # Add to profile
    echo "" >> "$PROFILE"
    echo "# Fairy-Stockfish" >> "$PROFILE"
    echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$PROFILE"
    
    echo "Added to PATH in: $PROFILE"
    echo "Please restart your terminal or run: source $PROFILE"
fi

# Test installation
echo "Testing installation..."
if command -v fairy-stockfish &> /dev/null; then
    echo "Fairy-Stockfish version:"
    fairy-stockfish --version
    echo "Installation successful!"
else
    echo "Installation test failed."
    echo "Try running directly: $INSTALL_DIR/fairy-stockfish"
fi

# Cleanup
rm -f "$TEMP_FILE"

echo ""
echo "=== Installation Complete ==="
echo "Fairy-Stockfish location: $INSTALL_DIR/fairy-stockfish"
echo "If not in PATH, use: $INSTALL_DIR/fairy-stockfish"
