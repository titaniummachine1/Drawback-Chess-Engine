#!/bin/bash
# Compile Fairy-Stockfish from Source
# Use this if pre-compiled binaries don't work for your system

set -e

echo "=== Compiling Fairy-Stockfish from Source ==="

# Check for required tools
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed"
    exit 1
fi

if ! command -v make &> /dev/null; then
    echo "Error: make is not installed"
    exit 1
fi

if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null; then
    echo "Error: C++ compiler (g++ or clang++) is not installed"
    exit 1
fi

# Create installation directory
INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

# Clone repository
REPO_DIR="/tmp/fairy-stockfish"
if [[ -d "$REPO_DIR" ]]; then
    rm -rf "$REPO_DIR"
fi

echo "Cloning Fairy-Stockfish repository..."
git clone https://github.com/fairy-stockfish/Fairy-Stockfish.git "$REPO_DIR"

cd "$REPO_DIR/src"

# Detect architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "x86_64" ]]; then
    ARCH_TARGET="x86-64-modern"
elif [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
    ARCH_TARGET="armv8"
else
    echo "Using generic architecture target"
    ARCH_TARGET="general-64"
fi

echo "Building for architecture: $ARCH_TARGET"

# Compile
echo "Compiling Fairy-Stockfish..."
make build ARCH="$ARCH_TARGET" -j$(nproc)

# Install
if [[ -f "stockfish" ]]; then
    cp stockfish "$INSTALL_DIR/fairy-stockfish"
    chmod +x "$INSTALL_DIR/fairy-stockfish"
    echo "Fairy-Stockfish compiled and installed to: $INSTALL_DIR/fairy-stockfish"
else
    echo "Error: stockfish executable not found after compilation"
    exit 1
fi

# Add to PATH if needed
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "Adding $INSTALL_DIR to PATH..."
    
    # Determine shell profile
    if [[ "$SHELL" == */zsh ]]; then
        PROFILE="$HOME/.zshrc"
    else
        PROFILE="$HOME/.bashrc"
        if [[ ! -f "$PROFILE" ]]; then
            PROFILE="$HOME/.profile"
        fi
    fi
    
    echo "" >> "$PROFILE"
    echo "# Fairy-Stockfish" >> "$PROFILE"
    echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$PROFILE"
    
    echo "Added to PATH in: $PROFILE"
fi

# Test installation
echo "Testing installation..."
if command -v fairy-stockfish &> /dev/null; then
    echo "Fairy-Stockfish version:"
    fairy-stockfish --version
    echo "Compilation successful!"
else
    echo "Installation test failed."
    echo "Try running directly: $INSTALL_DIR/fairy-stockfish"
fi

# Cleanup
cd /
rm -rf "$REPO_DIR"

echo ""
echo "=== Compilation Complete ==="
echo "Fairy-Stockfish location: $INSTALL_DIR/fairy-stockfish"
