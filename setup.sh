#!/bin/bash

# =====================================================
# Esteira Geo - Setup Script for Linux/macOS
# Instala dependências e configura ambiente
# =====================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "\n${CYAN}$(printf '=%.0s' {1..60})${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' {1..60})${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Install Docker (Linux)
install_docker_linux() {
    print_header "Installing Docker (Linux)"
    
    if command_exists docker; then
        print_info "Docker already installed"
        docker --version
        return 0
    fi
    
    print_info "Installing Docker via apt..."
    
    # Remove old versions
    sudo apt-get remove -y docker docker.io containerd runc 2>/dev/null || true
    
    # Install dependencies
    sudo apt-get update
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repo
    echo \
      "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # Allow current user to use Docker without sudo
    sudo usermod -aG docker "$USER"
    
    print_success "Docker installed"
    print_warning "You may need to log out and back in for group changes to take effect"
    print_info "Or run: newgrp docker"
}

# Install Docker Compose
install_docker_compose() {
    print_header "Installing Docker Compose"
    
    if command_exists docker-compose; then
        print_info "Docker Compose already installed"
        docker-compose --version
        return 0
    fi
    
    print_info "Installing Docker Compose..."
    
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    print_success "Docker Compose installed"
    docker-compose --version
}

# Install Git
install_git() {
    if command_exists git; then
        print_info "Git already installed"
        git --version
        return 0
    fi
    
    print_info "Installing Git..."
    
    OS=$(detect_os)
    if [ "$OS" = "linux" ]; then
        sudo apt-get install -y git
    elif [ "$OS" = "macos" ]; then
        brew install git
    fi
    
    print_success "Git installed"
}

# Setup Python virtual environment
setup_python_env() {
    print_header "Setting up Python Virtual Environment"
    
    if ! command_exists python3; then
        print_error "Python 3 not found. Please install Python 3.9+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_info "Python version: $PYTHON_VERSION"
    
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate venv
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel
    
    # Install requirements
    if [ -f "pipeline/requirements.txt" ]; then
        print_info "Installing Python dependencies..."
        pip install -r pipeline/requirements.txt
        print_success "Dependencies installed"
    fi
}

# Make scripts executable
make_scripts_executable() {
    print_header "Making scripts executable"
    
    chmod +x docker.sh 2>/dev/null || true
    chmod +x setup.sh 2>/dev/null || true
    
    if [ -f "pipeline/Makefile" ]; then
        chmod +x pipeline/Makefile 2>/dev/null || true
    fi
    
    print_success "Scripts are executable"
}

# Create .env file if doesn't exist
setup_env_file() {
    print_header "Setting up .env file"
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_info "Creating .env from .env.example..."
            cp .env.example .env
            print_success ".env created (customize as needed)"
        elif [ -f ".env.docker" ]; then
            print_info "Creating .env from .env.docker (Docker mode)..."
            cp .env.docker .env
            print_success ".env created"
        fi
    else
        print_info ".env already exists"
    fi
}

# Setup data directories
setup_data_dirs() {
    print_header "Setting up data directories"
    
    mkdir -p logs
    mkdir -p pipeline/data/bronze
    mkdir -p pipeline/data/silver
    mkdir -p pipeline/data/gold
    
    print_success "Data directories created"
}

# Main setup
main() {
    clear
    print_header "Esteira Geo Setup"
    
    OS=$(detect_os)
    print_info "Detected OS: $OS"
    
    if [ "$OS" = "unknown" ]; then
        print_error "Unsupported OS"
        exit 1
    fi
    
    # Full setup or Docker-only
    read -p "Setup type? (1=Full [default], 2=Docker Only): " setup_type
    setup_type=${setup_type:-1}
    
    case $setup_type in
        1)
            print_header "Full Setup"
            install_git
            if [ "$OS" = "linux" ]; then
                install_docker_linux
            fi
            install_docker_compose
            setup_python_env
            setup_env_file
            setup_data_dirs
            make_scripts_executable
            ;;
        2)
            print_header "Docker Setup Only"
            if [ "$OS" = "linux" ]; then
                install_docker_linux
            fi
            install_docker_compose
            setup_env_file
            setup_data_dirs
            make_scripts_executable
            ;;
        *)
            print_error "Invalid option"
            exit 1
            ;;
    esac
    
    # Final info
    print_header "Setup Complete!"
    echo ""
    print_success "Environment ready for development"
    echo ""
    print_info "Next steps:"
    echo "  1. Review and customize .env file"
    echo "  2. Start Docker environment:"
    echo "     ./docker.sh up"
    echo "  3. Run pipeline:"
    echo "     ./docker.sh pipeline"
    echo "  4. Check dashboard:"
    echo "     http://localhost:5000"
    echo ""
    print_info "For more info:"
    echo "  ./docker.sh help"
    echo "  cat DOCKER_SETUP.md"
    echo ""
}

# Run main
main
