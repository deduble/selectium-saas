#!/bin/bash

# Selextract Cloud SSL Certificate Setup and Management Script
# This script sets up SSL certificates using Let's Encrypt with automatic renewal

set -euo pipefail

# Configuration
DOMAIN="selextract.com"
SUBDOMAINS="app api monitoring"
EMAIL="${ADMIN_EMAIL:-admin@selextract.com}"
NGINX_CONFIG_DIR="/etc/nginx"
SSL_DIR="/etc/nginx/ssl"
CERTBOT_DIR="/etc/letsencrypt"
LOG_FILE="/var/log/ssl-setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    log "ERROR: $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
    log "WARNING: $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    log "INFO: $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    log "SUCCESS: $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
}

# Install certbot if not present
install_certbot() {
    info "Checking for certbot installation..."
    
    if ! command -v certbot &> /dev/null; then
        info "Installing certbot..."
        
        # Detect OS and install accordingly
        if [[ -f /etc/debian_version ]]; then
            apt-get update
            apt-get install -y certbot python3-certbot-nginx
        elif [[ -f /etc/redhat-release ]]; then
            dnf install -y certbot python3-certbot-nginx || yum install -y certbot python3-certbot-nginx
        else
            error "Unsupported operating system. Please install certbot manually."
        fi
        
        success "Certbot installed successfully"
    else
        info "Certbot is already installed"
    fi
}

# Create SSL directory structure
setup_ssl_directories() {
    info "Setting up SSL directory structure..."
    
    mkdir -p "$SSL_DIR/$DOMAIN"
    mkdir -p "$SSL_DIR/archive"
    mkdir -p "$SSL_DIR/live"
    
    # Set proper permissions
    chmod 755 "$SSL_DIR"
    chmod 700 "$SSL_DIR/$DOMAIN"
    
    success "SSL directories created"
}

# Generate temporary self-signed certificates for initial setup
generate_temporary_certificates() {
    info "Generating temporary self-signed certificates..."
    
    local temp_cert_dir="$SSL_DIR/$DOMAIN"
    
    # Generate private key
    openssl genrsa -out "$temp_cert_dir/privkey.pem" 2048
    
    # Generate certificate signing request
    openssl req -new -key "$temp_cert_dir/privkey.pem" \
        -out "$temp_cert_dir/cert.csr" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"
    
    # Generate self-signed certificate
    openssl x509 -req -days 365 -in "$temp_cert_dir/cert.csr" \
        -signkey "$temp_cert_dir/privkey.pem" \
        -out "$temp_cert_dir/fullchain.pem"
    
    # Create chain file (same as fullchain for self-signed)
    cp "$temp_cert_dir/fullchain.pem" "$temp_cert_dir/chain.pem"
    
    # Set proper permissions
    chmod 600 "$temp_cert_dir/privkey.pem"
    chmod 644 "$temp_cert_dir/fullchain.pem"
    chmod 644 "$temp_cert_dir/chain.pem"
    
    # Clean up CSR
    rm "$temp_cert_dir/cert.csr"
    
    success "Temporary certificates generated"
}

# Enable nginx site configuration
enable_nginx_site() {
    info "Enabling Nginx site configuration..."
    
    # Create sites-enabled directory if it doesn't exist
    mkdir -p /etc/nginx/sites-enabled
    
    # Enable the site configuration
    if [[ -f "/etc/nginx/sites-available/selextract.conf" ]]; then
        ln -sf /etc/nginx/sites-available/selextract.conf /etc/nginx/sites-enabled/
        success "Nginx site configuration enabled"
    else
        warning "Nginx site configuration not found at /etc/nginx/sites-available/selextract.conf"
    fi
    
    # Test nginx configuration
    if nginx -t; then
        info "Nginx configuration test passed"
        systemctl reload nginx
        success "Nginx reloaded successfully"
    else
        error "Nginx configuration test failed"
    fi
}

# Obtain Let's Encrypt certificates
obtain_letsencrypt_certificates() {
    info "Obtaining Let's Encrypt certificates..."
    
    # Build domain list
    local domain_args="-d $DOMAIN"
    for subdomain in $SUBDOMAINS; do
        domain_args="$domain_args -d $subdomain.$DOMAIN"
    done
    
    # Stop nginx temporarily for standalone authentication
    systemctl stop nginx || warning "Could not stop nginx"
    
    # Obtain certificates using standalone mode
    if certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        --expand \
        $domain_args; then
        
        success "Let's Encrypt certificates obtained successfully"
        
        # Copy certificates to our SSL directory
        copy_letsencrypt_certificates
        
    else
        error "Failed to obtain Let's Encrypt certificates"
    fi
    
    # Start nginx again
    systemctl start nginx || error "Could not start nginx"
}

# Copy Let's Encrypt certificates to our SSL directory
copy_letsencrypt_certificates() {
    info "Copying Let's Encrypt certificates..."
    
    local le_live_dir="/etc/letsencrypt/live/$DOMAIN"
    local ssl_cert_dir="$SSL_DIR/$DOMAIN"
    
    if [[ -d "$le_live_dir" ]]; then
        cp "$le_live_dir/fullchain.pem" "$ssl_cert_dir/fullchain.pem"
        cp "$le_live_dir/privkey.pem" "$ssl_cert_dir/privkey.pem"
        cp "$le_live_dir/chain.pem" "$ssl_cert_dir/chain.pem"
        
        # Set proper permissions
        chmod 644 "$ssl_cert_dir/fullchain.pem" "$ssl_cert_dir/chain.pem"
        chmod 600 "$ssl_cert_dir/privkey.pem"
        
        success "Certificates copied successfully"
    else
        error "Let's Encrypt certificates directory not found"
    fi
}

# Setup automatic certificate renewal
setup_auto_renewal() {
    info "Setting up automatic certificate renewal..."
    
    # Create renewal script
    cat > /usr/local/bin/renew-ssl.sh << 'EOF'
#!/bin/bash

# Certificate renewal script
LOG_FILE="/var/log/ssl-renewal.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Starting certificate renewal check..."

# Renew certificates
if certbot renew --quiet --no-self-upgrade; then
    log "Certificate renewal check completed successfully"
    
    # Copy renewed certificates
    if [[ -d "/etc/letsencrypt/live/selextract.com" ]]; then
        cp /etc/letsencrypt/live/selextract.com/fullchain.pem /etc/nginx/ssl/selextract.com/fullchain.pem
        cp /etc/letsencrypt/live/selextract.com/privkey.pem /etc/nginx/ssl/selextract.com/privkey.pem
        cp /etc/letsencrypt/live/selextract.com/chain.pem /etc/nginx/ssl/selextract.com/chain.pem
        
        # Set proper permissions
        chmod 644 /etc/nginx/ssl/selextract.com/fullchain.pem /etc/nginx/ssl/selextract.com/chain.pem
        chmod 600 /etc/nginx/ssl/selextract.com/privkey.pem
        
        log "Certificates copied and permissions set"
        
        # Reload nginx
        if systemctl reload nginx; then
            log "Nginx reloaded successfully"
        else
            log "ERROR: Failed to reload nginx"
        fi
    else
        log "WARNING: Let's Encrypt certificates directory not found"
    fi
else
    log "ERROR: Certificate renewal failed"
fi

log "Certificate renewal process completed"
EOF
    
    chmod +x /usr/local/bin/renew-ssl.sh
    
    # Create systemd service for renewal
    cat > /etc/systemd/system/ssl-renewal.service << EOF
[Unit]
Description=SSL Certificate Renewal
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/renew-ssl.sh
User=root
EOF
    
    # Create systemd timer for automatic renewal
    cat > /etc/systemd/system/ssl-renewal.timer << EOF
[Unit]
Description=SSL Certificate Renewal Timer
Requires=ssl-renewal.service

[Timer]
OnCalendar=daily
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
EOF
    
    # Enable and start the timer
    systemctl daemon-reload
    systemctl enable ssl-renewal.timer
    systemctl start ssl-renewal.timer
    
    success "Automatic certificate renewal configured"
}

# Setup monitoring password file
setup_monitoring_auth() {
    info "Setting up monitoring authentication..."
    
    # Generate random password if not provided
    local monitoring_password="${MONITORING_PASSWORD:-$(openssl rand -base64 32)}"
    
    # Install apache2-utils for htpasswd
    if [[ -f /etc/debian_version ]]; then
        apt-get install -y apache2-utils
    elif [[ -f /etc/redhat-release ]]; then
        dnf install -y httpd-tools || yum install -y httpd-tools
    fi
    
    # Create htpasswd file
    echo -n "admin:" > /etc/nginx/.htpasswd
    echo "$monitoring_password" | openssl passwd -apr1 -stdin >> /etc/nginx/.htpasswd
    
    chmod 644 /etc/nginx/.htpasswd
    
    info "Monitoring authentication configured with password: $monitoring_password"
    warning "Please save this password securely!"
}

# Verify SSL setup
verify_ssl_setup() {
    info "Verifying SSL setup..."
    
    local ssl_cert_dir="$SSL_DIR/$DOMAIN"
    
    # Check if certificate files exist
    if [[ -f "$ssl_cert_dir/fullchain.pem" && -f "$ssl_cert_dir/privkey.pem" && -f "$ssl_cert_dir/chain.pem" ]]; then
        info "Certificate files found"
        
        # Check certificate validity
        if openssl x509 -in "$ssl_cert_dir/fullchain.pem" -text -noout &>/dev/null; then
            local expiry_date=$(openssl x509 -in "$ssl_cert_dir/fullchain.pem" -noout -enddate | cut -d= -f2)
            info "Certificate is valid and expires on: $expiry_date"
            success "SSL setup verification completed successfully"
        else
            error "Certificate file is invalid"
        fi
    else
        error "Certificate files are missing"
    fi
}

# Main function
main() {
    info "Starting SSL setup for Selextract Cloud..."
    
    check_root
    install_certbot
    setup_ssl_directories
    generate_temporary_certificates
    enable_nginx_site
    
    # Ask user if they want to obtain real Let's Encrypt certificates
    read -p "Do you want to obtain real Let's Encrypt certificates now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        obtain_letsencrypt_certificates
        setup_auto_renewal
    else
        info "Skipping Let's Encrypt certificate acquisition"
        warning "You are using temporary self-signed certificates"
        info "Run this script again with --letsencrypt flag to obtain real certificates"
    fi
    
    setup_monitoring_auth
    verify_ssl_setup
    
    success "SSL setup completed successfully!"
    info "Next steps:"
    info "1. Update your DNS records to point to this server"
    info "2. Test your domains: https://app.selextract.com, https://api.selextract.com, https://monitoring.selextract.com"
    info "3. Monitor certificate renewal in /var/log/ssl-renewal.log"
}

# Handle command line arguments
case "${1:-}" in
    --letsencrypt)
        info "Obtaining Let's Encrypt certificates..."
        check_root
        obtain_letsencrypt_certificates
        setup_auto_renewal
        verify_ssl_setup
        ;;
    --renew)
        info "Renewing certificates..."
        /usr/local/bin/renew-ssl.sh
        ;;
    --verify)
        verify_ssl_setup
        ;;
    *)
        main
        ;;
esac