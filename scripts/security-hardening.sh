#!/bin/bash

# Selextract Cloud Security Hardening Script
# This script implements security best practices for the production server

set -euo pipefail

# Configuration
LOG_FILE="/var/log/security-hardening.log"
BACKUP_DIR="/root/security-backups"

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

# Create backup directory
setup_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"
    info "Backup directory created at $BACKUP_DIR"
}

# Update system packages
update_system() {
    info "Updating system packages..."
    
    if [[ -f /etc/debian_version ]]; then
        apt-get update && apt-get upgrade -y
        apt-get autoremove -y
        apt-get autoclean
    elif [[ -f /etc/redhat-release ]]; then
        dnf update -y || yum update -y
    else
        warning "Unknown operating system, skipping package updates"
    fi
    
    success "System packages updated"
}

# Configure UFW firewall
configure_firewall() {
    info "Configuring UFW firewall..."
    
    # Install UFW if not present
    if ! command -v ufw &> /dev/null; then
        if [[ -f /etc/debian_version ]]; then
            apt-get install -y ufw
        elif [[ -f /etc/redhat-release ]]; then
            dnf install -y ufw || yum install -y ufw
        fi
    fi
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (be careful with this!)
    ufw allow ssh
    ufw allow 22/tcp
    
    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow specific Docker ports for internal communication
    ufw allow from 172.16.0.0/12 to any port 5432 comment 'PostgreSQL internal'
    ufw allow from 172.16.0.0/12 to any port 6379 comment 'Redis internal'
    ufw allow from 172.16.0.0/12 to any port 9090 comment 'Prometheus internal'
    ufw allow from 172.16.0.0/12 to any port 3001 comment 'Grafana internal'
    
    # Enable UFW
    ufw --force enable
    
    success "Firewall configured successfully"
}

# Configure SSH security
configure_ssh() {
    info "Configuring SSH security..."
    
    # Backup original SSH config
    cp /etc/ssh/sshd_config "$BACKUP_DIR/sshd_config.backup"
    
    # Create new SSH configuration
    cat > /etc/ssh/sshd_config << 'EOF'
# Selextract Cloud SSH Configuration

# Basic Configuration
Port 22
Protocol 2
AddressFamily inet

# Authentication
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes

# Security Settings
X11Forwarding no
MaxAuthTries 3
MaxStartups 10:30:60
ClientAliveInterval 300
ClientAliveCountMax 2
LoginGraceTime 30
StrictModes yes

# Disable unused authentication methods
KerberosAuthentication no
GSSAPIAuthentication no
HostbasedAuthentication no

# Logging
SyslogFacility AUTH
LogLevel VERBOSE

# Banner
Banner /etc/ssh/banner

# Subsystem
Subsystem sftp /usr/lib/openssh/sftp-server

# Allow specific users only (uncomment and modify as needed)
# AllowUsers deploy admin

# Deny specific users
DenyUsers root guest nobody
EOF
    
    # Create SSH banner
    cat > /etc/ssh/banner << 'EOF'
********************************************************************************
*                           AUTHORIZED ACCESS ONLY                           *
*                                                                              *
*  This system is for authorized users only. All activity is monitored        *
*  and logged. Unauthorized access is strictly prohibited and may result      *
*  in legal action.                                                           *
*                                                                              *
*                        Selextract Cloud Infrastructure                       *
********************************************************************************
EOF
    
    # Test SSH configuration
    if sshd -t; then
        systemctl restart sshd
        success "SSH configuration updated successfully"
    else
        error "SSH configuration test failed"
    fi
}

# Configure fail2ban
configure_fail2ban() {
    info "Configuring fail2ban..."
    
    # Install fail2ban
    if [[ -f /etc/debian_version ]]; then
        apt-get install -y fail2ban
    elif [[ -f /etc/redhat-release ]]; then
        dnf install -y fail2ban || yum install -y fail2ban
    fi
    
    # Create fail2ban configuration
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
# Ban hosts for 1 hour
bantime = 3600
# Find 5 failures within 10 minutes
findtime = 600
maxretry = 5
# Ignore local IPs
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/*error.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/*error.log
maxretry = 10

[nginx-botsearch]
enabled = true
filter = nginx-botsearch
port = http,https
logpath = /var/log/nginx/*access.log
maxretry = 2
EOF
    
    # Create custom nginx filters
    cat > /etc/fail2ban/filter.d/nginx-botsearch.conf << 'EOF'
[Definition]
failregex = ^<HOST> .* "(GET|POST|HEAD).*HTTP.*" (400|401|403|404|405|444) .*$
ignoreregex =
EOF
    
    # Enable and start fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
    
    success "Fail2ban configured successfully"
}

# Configure automatic security updates
configure_auto_updates() {
    info "Configuring automatic security updates..."
    
    if [[ -f /etc/debian_version ]]; then
        # Install unattended-upgrades
        apt-get install -y unattended-upgrades apt-listchanges
        
        # Configure automatic updates
        cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF
        
        cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Mail "admin@selextract.com";
EOF
        
        success "Automatic security updates configured"
    else
        warning "Automatic updates configuration skipped for non-Debian systems"
    fi
}

# Configure system limits and kernel parameters
configure_system_limits() {
    info "Configuring system limits and kernel parameters..."
    
    # Backup original files
    cp /etc/security/limits.conf "$BACKUP_DIR/limits.conf.backup"
    cp /etc/sysctl.conf "$BACKUP_DIR/sysctl.conf.backup"
    
    # Configure limits
    cat >> /etc/security/limits.conf << 'EOF'

# Selextract Cloud limits
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768
root soft nofile 65536
root hard nofile 65536
EOF
    
    # Configure kernel parameters
    cat > /etc/sysctl.d/99-selextract-security.conf << 'EOF'
# Selextract Cloud security settings

# Network security
net.ipv4.ip_forward = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1

# IPv6 security
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Performance and security
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
vm.max_map_count = 262144
EOF
    
    # Apply sysctl settings
    sysctl -p /etc/sysctl.d/99-selextract-security.conf
    
    success "System limits and kernel parameters configured"
}

# Configure log rotation
configure_log_rotation() {
    info "Configuring log rotation..."
    
    cat > /etc/logrotate.d/selextract << 'EOF'
/var/log/selextract/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    create 644 root root
}

/var/log/nginx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 `cat /var/run/nginx.pid`
        fi
    endscript
}

/var/log/ssl-*.log {
    weekly
    missingok
    rotate 12
    compress
    delaycompress
    notifempty
    copytruncate
    create 644 root root
}
EOF
    
    success "Log rotation configured"
}

# Install and configure monitoring tools
install_monitoring_tools() {
    info "Installing system monitoring tools..."
    
    # Install essential monitoring tools
    if [[ -f /etc/debian_version ]]; then
        apt-get install -y htop iotop nethogs iftop sysstat
    elif [[ -f /etc/redhat-release ]]; then
        dnf install -y htop iotop nethogs iftop sysstat || yum install -y htop iotop nethogs iftop sysstat
    fi
    
    # Enable sysstat
    systemctl enable sysstat
    systemctl start sysstat
    
    success "Monitoring tools installed"
}

# Create security audit script
create_security_audit_script() {
    info "Creating security audit script..."
    
    cat > /usr/local/bin/security-audit.sh << 'EOF'
#!/bin/bash

# Selextract Cloud Security Audit Script

echo "=================================="
echo "Security Audit Report"
echo "Date: $(date)"
echo "=================================="

echo
echo "1. System Information:"
echo "   - Hostname: $(hostname)"
echo "   - OS: $(lsb_release -d | cut -f2)"
echo "   - Kernel: $(uname -r)"
echo "   - Uptime: $(uptime -p)"

echo
echo "2. User Accounts:"
echo "   - Users with shell access:"
grep -E ':(\/bin\/bash|\/bin\/sh)$' /etc/passwd | cut -d: -f1 | sort

echo
echo "3. SSH Configuration:"
echo "   - Root login: $(grep '^PermitRootLogin' /etc/ssh/sshd_config || echo 'Default')"
echo "   - Password auth: $(grep '^PasswordAuthentication' /etc/ssh/sshd_config || echo 'Default')"

echo
echo "4. Firewall Status:"
ufw status numbered

echo
echo "5. Fail2ban Status:"
fail2ban-client status

echo
echo "6. SSL Certificate Status:"
if [[ -f /etc/nginx/ssl/selextract.com/fullchain.pem ]]; then
    echo "   - Certificate expires: $(openssl x509 -in /etc/nginx/ssl/selextract.com/fullchain.pem -noout -enddate | cut -d= -f2)"
else
    echo "   - No SSL certificate found"
fi

echo
echo "7. Disk Usage:"
df -h | grep -E '^(/dev/|tmpfs)'

echo
echo "8. Memory Usage:"
free -h

echo
echo "9. Recent Failed Login Attempts:"
journalctl -u ssh -S yesterday | grep "Failed password" | tail -5 || echo "None found"

echo
echo "10. Open Ports:"
ss -tuln | grep LISTEN

echo
echo "=================================="
echo "Audit completed at $(date)"
echo "=================================="
EOF
    
    chmod +x /usr/local/bin/security-audit.sh
    
    success "Security audit script created"
}

# Setup intrusion detection
setup_intrusion_detection() {
    info "Setting up basic intrusion detection..."
    
    # Create directory for security scripts
    mkdir -p /opt/security
    
    # Create file integrity monitoring script
    cat > /opt/security/file-integrity-check.sh << 'EOF'
#!/bin/bash

# File Integrity Monitoring for critical system files

CRITICAL_FILES=(
    "/etc/passwd"
    "/etc/shadow"
    "/etc/group"
    "/etc/sudoers"
    "/etc/ssh/sshd_config"
    "/etc/nginx/nginx.conf"
    "/etc/hosts"
    "/etc/crontab"
)

CHECKSUM_FILE="/opt/security/checksums.md5"
LOG_FILE="/var/log/file-integrity.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Initialize checksums if they don't exist
if [[ ! -f "$CHECKSUM_FILE" ]]; then
    log "Initializing file integrity checksums"
    for file in "${CRITICAL_FILES[@]}"; do
        if [[ -f "$file" ]]; then
            md5sum "$file" >> "$CHECKSUM_FILE"
        fi
    done
    log "Checksums initialized"
    exit 0
fi

# Check for changes
log "Starting file integrity check"
changes_detected=false

for file in "${CRITICAL_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        current_checksum=$(md5sum "$file" | cut -d' ' -f1)
        stored_checksum=$(grep "$file" "$CHECKSUM_FILE" | cut -d' ' -f1)
        
        if [[ "$current_checksum" != "$stored_checksum" ]]; then
            log "WARNING: File integrity violation detected for $file"
            echo "ALERT: File $file has been modified!" | mail -s "File Integrity Alert" admin@selextract.com
            changes_detected=true
        fi
    fi
done

if [[ "$changes_detected" == "false" ]]; then
    log "File integrity check completed - no changes detected"
fi
EOF
    
    chmod +x /opt/security/file-integrity-check.sh
    
    # Initialize checksums
    /opt/security/file-integrity-check.sh
    
    # Add to cron for daily checks
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/security/file-integrity-check.sh") | crontab -
    
    success "Intrusion detection configured"
}

# Main function
main() {
    info "Starting security hardening for Selextract Cloud..."
    
    check_root
    setup_backup_dir
    update_system
    configure_firewall
    configure_ssh
    configure_fail2ban
    configure_auto_updates
    configure_system_limits
    configure_log_rotation
    install_monitoring_tools
    create_security_audit_script
    setup_intrusion_detection
    
    success "Security hardening completed successfully!"
    
    echo
    info "Security hardening summary:"
    info "- System packages updated"
    info "- UFW firewall configured and enabled"
    info "- SSH security enhanced"
    info "- Fail2ban configured for intrusion prevention"
    info "- Automatic security updates enabled"
    info "- System limits and kernel parameters optimized"
    info "- Log rotation configured"
    info "- Monitoring tools installed"
    info "- Security audit script created: /usr/local/bin/security-audit.sh"
    info "- File integrity monitoring enabled"
    
    echo
    warning "Important next steps:"
    warning "1. Review and test SSH access before logging out"
    warning "2. Configure proper backup of the server"
    warning "3. Set up monitoring and alerting"
    warning "4. Run security audit: /usr/local/bin/security-audit.sh"
    warning "5. Review firewall rules and adjust as needed"
}

# Handle command line arguments
case "${1:-}" in
    --audit)
        /usr/local/bin/security-audit.sh
        ;;
    --check-integrity)
        /opt/security/file-integrity-check.sh
        ;;
    *)
        main
        ;;
esac