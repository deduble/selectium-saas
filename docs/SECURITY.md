# Selextract Cloud Security Guide

This comprehensive guide covers security best practices, audit procedures, and compliance measures for Selextract Cloud deployment and operations.

## Table of Contents

- [Security Architecture Overview](#security-architecture-overview)
- [Server Hardening](#server-hardening)
- [Network Security](#network-security)
- [Application Security](#application-security)
- [Database Security](#database-security)
- [Authentication and Authorization](#authentication-and-authorization)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Container Security](#container-security)
- [Data Protection](#data-protection)
- [Monitoring and Incident Response](#monitoring-and-incident-response)
- [Security Auditing](#security-auditing)
- [Compliance Checklist](#compliance-checklist)
- [Emergency Response Procedures](#emergency-response-procedures)

---

## Security Architecture Overview

### Defense in Depth Strategy

Selextract Cloud implements multiple layers of security:

```
┌─────────────────────────────────────────────┐
│                   Users                     │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│             CDN/WAF (Optional)              │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│              Firewall (UFW)                │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│            Nginx (Reverse Proxy)           │
│     • SSL Termination                      │
│     • Rate Limiting                        │
│     • Request Filtering                    │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│          Application Layer                  │
│     • JWT Authentication                   │
│     • Input Validation                     │
│     • CORS Protection                      │
│     • API Rate Limiting                    │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│            Data Layer                      │
│     • Database Encryption                  │
│     • Connection Security                  │
│     • Backup Encryption                    │
└─────────────────────────────────────────────┘
```

### Security Principles

1. **Least Privilege:** Grant minimum necessary permissions
2. **Defense in Depth:** Multiple security layers
3. **Fail Secure:** Default to deny access
4. **Security by Design:** Built-in security from the start
5. **Regular Updates:** Keep all components current
6. **Monitoring:** Continuous security monitoring
7. **Incident Response:** Prepared response procedures

---

## Server Hardening

### Operating System Security

```bash
#!/bin/bash
# comprehensive-server-hardening.sh

echo "=== Comprehensive Server Hardening ==="

# 1. Update system packages
echo "Updating system packages..."
apt update && apt upgrade -y

# 2. Configure automatic security updates
echo "Configuring automatic security updates..."
apt install -y unattended-upgrades apt-listchanges
echo 'Unattended-Upgrade::Automatic-Reboot "false";' >> /etc/apt/apt.conf.d/50unattended-upgrades
echo 'Unattended-Upgrade::Remove-Unused-Dependencies "true";' >> /etc/apt/apt.conf.d/50unattended-upgrades
echo 'Unattended-Upgrade::AutoFixInterruptedDpkg "true";' >> /etc/apt/apt.conf.d/50unattended-upgrades

# 3. Disable unused services
echo "Disabling unused services..."
systemctl disable --now bluetooth
systemctl disable --now cups
systemctl disable --now avahi-daemon
systemctl disable --now cups-browsed

# 4. Configure SSH security
echo "Hardening SSH configuration..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

cat > /etc/ssh/sshd_config << 'EOF'
# SSH Security Configuration
Port 22
Protocol 2
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key

# Authentication
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
IgnoreUserKnownHosts yes
HostbasedAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
KerberosAuthentication no
GSSAPIAuthentication no

# Session settings
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PrintMotd no
TCPKeepAlive yes
Compression no
ClientAliveInterval 300
ClientAliveCountMax 2
MaxAuthTries 3
MaxSessions 2

# Limit users
AllowUsers deploy
DenyUsers root

# Logging
SyslogFacility AUTH
LogLevel VERBOSE
EOF

# 5. Configure kernel parameters
echo "Configuring kernel security parameters..."
cat > /etc/sysctl.d/99-security.conf << 'EOF'
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
net.ipv6.conf.all.accept_ra = 0
net.ipv6.conf.default.accept_ra = 0

# Kernel security
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
fs.suid_dumpable = 0
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
EOF

sysctl -p /etc/sysctl.d/99-security.conf

# 6. Set file permissions
echo "Setting secure file permissions..."
chmod 600 /etc/ssh/sshd_config
chmod 700 /root
chmod 644 /etc/passwd
chmod 644 /etc/group
chmod 600 /etc/shadow
chmod 600 /etc/gshadow

# 7. Configure audit logging
echo "Setting up audit logging..."
apt install -y auditd audispd-plugins
systemctl enable auditd

cat > /etc/audit/rules.d/audit.rules << 'EOF'
# Audit rules for security monitoring
-D
-b 8192

# Monitor authentication
-w /etc/passwd -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/gshadow -p wa -k identity
-w /etc/sudoers -p wa -k identity
-w /etc/sudoers.d/ -p wa -k identity

# Monitor system calls
-a always,exit -F arch=b64 -S adjtimex -S settimeofday -k time-change
-a always,exit -F arch=b32 -S adjtimex -S settimeofday -S stime -k time-change
-a always,exit -F arch=b64 -S clock_settime -k time-change
-a always,exit -F arch=b32 -S clock_settime -k time-change

# Monitor network configuration
-a always,exit -F arch=b64 -S sethostname -S setdomainname -k system-locale
-a always,exit -F arch=b32 -S sethostname -S setdomainname -k system-locale
-w /etc/issue -p wa -k system-locale
-w /etc/issue.net -p wa -k system-locale
-w /etc/hosts -p wa -k system-locale
-w /etc/network/ -p wa -k system-locale

# Monitor file access
-w /etc/selextract/ -p wa -k selextract-config
-w /opt/selextract-cloud/ -p wa -k selextract-files
-w /var/log/selextract/ -p wa -k selextract-logs

# Make rules immutable
-e 2
EOF

systemctl restart auditd

# 8. Install and configure fail2ban
echo "Installing and configuring fail2ban..."
apt install -y fail2ban

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = systemd
destemail = admin@selextract.com
sendername = Fail2Ban
mta = sendmail

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
port = http,https
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-botsearch]
enabled = true
port = http,https
filter = nginx-botsearch
logpath = /var/log/nginx/access.log
maxretry = 2
EOF

systemctl enable fail2ban
systemctl restart fail2ban

# 9. Configure log rotation
echo "Configuring secure log rotation..."
cat > /etc/logrotate.d/security << 'EOF'
/var/log/auth.log
/var/log/syslog
/var/log/kern.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 640 syslog adm
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}
EOF

# 10. Set up file integrity monitoring
echo "Setting up file integrity monitoring..."
apt install -y aide
aideinit
mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

echo "0 3 * * * /usr/bin/aide --check" | crontab -

echo "Server hardening completed successfully!"
echo "Please reboot the server to apply all changes."
```

### User Account Security

```bash
#!/bin/bash
# user-security-setup.sh

echo "=== User Account Security Setup ==="

# 1. Create deployment user with restricted permissions
useradd -m -s /bin/bash -G docker deploy
usermod -aG sudo deploy

# 2. Configure sudo with restrictions
cat > /etc/sudoers.d/deploy << 'EOF'
# Deploy user sudo configuration
deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose, /bin/systemctl restart nginx, /bin/systemctl reload nginx
deploy ALL=(ALL) PASSWD: ALL
EOF

# 3. Set up SSH key authentication
mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
touch /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

# 4. Configure password policies
apt install -y libpam-pwquality
cat > /etc/security/pwquality.conf << 'EOF'
minlen = 12
dcredit = -1
ucredit = -1
ocredit = -1
lcredit = -1
minclass = 3
maxrepeat = 2
maxclasschg = 8
EOF

# 5. Configure account lockout
cat >> /etc/pam.d/common-auth << 'EOF'
auth required pam_tally2.so deny=3 unlock_time=900 onerr=fail audit even_deny_root
EOF

echo "User security setup completed!"
```

---

## Network Security

### Firewall Configuration

```bash
#!/bin/bash
# firewall-setup.sh

echo "=== Firewall Configuration ==="

# 1. Reset UFW to defaults
ufw --force reset

# 2. Set default policies
ufw default deny incoming
ufw default allow outgoing

# 3. Allow essential services
ufw allow ssh
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS

# 4. Allow specific IP ranges (adjust as needed)
# ufw allow from 10.0.0.0/8 to any port 22
# ufw allow from 172.16.0.0/12 to any port 22
# ufw allow from 192.168.0.0/16 to any port 22

# 5. Rate limiting for SSH
ufw limit ssh

# 6. Advanced rules for monitoring (optional)
# ufw allow from trusted_monitoring_ip to any port 9090  # Prometheus
# ufw allow from trusted_monitoring_ip to any port 3000  # Grafana

# 7. Enable logging
ufw logging on

# 8. Enable UFW
ufw --force enable

# 9. Display status
ufw status verbose

echo "Firewall configuration completed!"
```

### DDoS Protection

```nginx
# nginx/conf.d/ddos-protection.conf
# DDoS protection configuration

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=frontend:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

# Connection limiting
limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;

# Server configuration with DDoS protection
server {
    listen 443 ssl http2;
    server_name api.selextract.com;

    # Connection limits
    limit_conn conn_limit_per_ip 20;
    
    # Rate limiting
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        limit_req_status 429;
        proxy_pass http://api:8000;
    }
    
    location /auth/ {
        limit_req zone=auth burst=10 nodelay;
        limit_req_status 429;
        proxy_pass http://api:8000;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;

    # Hide Nginx version
    server_tokens off;

    # Request size limits
    client_max_body_size 10M;
    client_body_buffer_size 128k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;

    # Timeout settings
    client_body_timeout 12;
    client_header_timeout 12;
    keepalive_timeout 15;
    send_timeout 10;

    # Block common attack patterns
    location ~* \.(aspx|php|jsp|cgi)$ {
        return 404;
    }
    
    location ~* /(wp-admin|wp-login|admin|phpmyadmin) {
        return 404;
    }
}
```

---

## Application Security

### Input Validation and Sanitization

```python
# api/security/validation.py
"""Input validation and sanitization utilities."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import bleach
from pydantic import BaseModel, validator
import validators

class SecurityValidator:
    """Comprehensive input validation and sanitization."""
    
    # Allowed HTML tags for user input
    ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
    ALLOWED_ATTRIBUTES = {}
    
    # Common malicious patterns
    MALICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'eval\s*\(',
        r'expression\s*\(',
        r'url\s*\(',
        r'@import',
        r'<iframe',
        r'<object',
        r'<embed',
        r'<applet',
        r'<meta',
        r'<link',
    ]
    
    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """Sanitize HTML input to prevent XSS."""
        if not text:
            return ""
        
        # Remove malicious patterns
        for pattern in cls.MALICIOUS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean HTML with bleach
        cleaned = bleach.clean(
            text,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        return cleaned.strip()
    
    @classmethod
    def validate_url(cls, url: str, allowed_schemes: List[str] = None) -> bool:
        """Validate URL and check against allowed schemes."""
        if not url:
            return False
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme.lower() not in allowed_schemes:
                return False
            
            # Check for malicious patterns
            url_lower = url.lower()
            for pattern in cls.MALICIOUS_PATTERNS:
                if re.search(pattern, url_lower):
                    return False
            
            # Use validators library for comprehensive validation
            return validators.url(url)
            
        except Exception:
            return False
    
    @classmethod
    def validate_selector(cls, selector: str) -> bool:
        """Validate CSS selector to prevent injection."""
        if not selector or len(selector) > 1000:
            return False
        
        # Allow only safe CSS selector characters
        safe_pattern = r'^[a-zA-Z0-9\s\-_\.#\[\]"\'=:(),>+~\*]+$'
        
        if not re.match(safe_pattern, selector):
            return False
        
        # Block dangerous patterns
        dangerous_patterns = [
            r'javascript:',
            r'expression\s*\(',
            r'@import',
            r'url\s*\(',
            r'<.*>',
        ]
        
        selector_lower = selector.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, selector_lower):
                return False
        
        return True
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        if not filename:
            return ""
        
        # Remove path separators and dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\.\.', '', filename)
        filename = filename.strip('. ')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:240] + ('.' + ext if ext else '')
        
        return filename

class SecureTaskConfig(BaseModel):
    """Secure task configuration with validation."""
    
    urls: List[str]
    selectors: Dict[str, str]
    output_format: str = "json"
    timeout: int = 60
    wait_time: int = 0
    
    @validator('urls')
    def validate_urls(cls, v):
        """Validate all URLs in the list."""
        if not v or len(v) > 100:  # Limit number of URLs
            raise ValueError("Invalid number of URLs")
        
        validated_urls = []
        for url in v:
            if not SecurityValidator.validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            validated_urls.append(url)
        
        return validated_urls
    
    @validator('selectors')
    def validate_selectors(cls, v):
        """Validate all CSS selectors."""
        if not v or len(v) > 50:  # Limit number of selectors
            raise ValueError("Invalid number of selectors")
        
        validated_selectors = {}
        for key, selector in v.items():
            # Validate key
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValueError(f"Invalid selector key: {key}")
            
            # Validate selector
            if not SecurityValidator.validate_selector(selector):
                raise ValueError(f"Invalid CSS selector: {selector}")
            
            validated_selectors[key] = selector
        
        return validated_selectors
    
    @validator('output_format')
    def validate_output_format(cls, v):
        """Validate output format."""
        allowed_formats = ['json', 'csv', 'xml']
        if v not in allowed_formats:
            raise ValueError(f"Invalid output format. Allowed: {allowed_formats}")
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout value."""
        if not isinstance(v, int) or v < 1 or v > 300:  # Max 5 minutes
            raise ValueError("Timeout must be between 1 and 300 seconds")
        return v
```

### API Security Middleware

```python
# api/security/middleware.py
"""Security middleware for API protection."""

import time
import hashlib
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis
from datetime import datetime, timedelta
import json

class SecurityMiddleware:
    """Comprehensive security middleware."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.rate_limit_prefix = "rate_limit"
        self.ip_ban_prefix = "ip_ban"
        self.suspicious_activity_prefix = "suspicious"
    
    async def __call__(self, request: Request, call_next):
        """Main middleware handler."""
        client_ip = self._get_client_ip(request)
        
        # Check if IP is banned
        if await self._is_ip_banned(client_ip):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP address is banned"
            )
        
        # Rate limiting
        if not await self._check_rate_limit(client_ip, request.url.path):
            await self._log_suspicious_activity(client_ip, "rate_limit_exceeded")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Request validation
        await self._validate_request(request, client_ip)
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add security headers
        self._add_security_headers(response)
        
        # Log request
        await self._log_request(request, response, client_ip, process_time)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address safely."""
        # Check X-Forwarded-For header (from load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        return request.client.host
    
    async def _is_ip_banned(self, ip: str) -> bool:
        """Check if IP address is banned."""
        ban_key = f"{self.ip_ban_prefix}:{ip}"
        return bool(self.redis.get(ban_key))
    
    async def _check_rate_limit(self, ip: str, endpoint: str) -> bool:
        """Implement sliding window rate limiting."""
        # Different rate limits for different endpoints
        rate_limits = {
            "/auth/": {"requests": 5, "window": 60},      # 5 per minute
            "/api/tasks": {"requests": 20, "window": 60}, # 20 per minute
            "default": {"requests": 60, "window": 60}     # 60 per minute
        }
        
        # Find applicable rate limit
        limit_config = rate_limits["default"]
        for pattern, config in rate_limits.items():
            if pattern in endpoint:
                limit_config = config
                break
        
        # Sliding window rate limiting
        window_start = int(time.time()) - limit_config["window"]
        rate_key = f"{self.rate_limit_prefix}:{ip}:{endpoint}"
        
        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(rate_key, 0, window_start)
        pipe.zcard(rate_key)
        pipe.zadd(rate_key, {str(time.time()): time.time()})
        pipe.expire(rate_key, limit_config["window"])
        
        results = pipe.execute()
        current_requests = results[1]
        
        return current_requests < limit_config["requests"]
    
    async def _validate_request(self, request: Request, ip: str):
        """Validate request for suspicious activity."""
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
            await self._log_suspicious_activity(ip, "large_request")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
        
        # Check user agent
        user_agent = request.headers.get("user-agent", "")
        suspicious_agents = [
            "sqlmap", "nikto", "nmap", "masscan", "zap",
            "burp", "w3af", "acunetix", "nessus"
        ]
        
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            await self._log_suspicious_activity(ip, "suspicious_user_agent")
            await self._ban_ip(ip, duration=3600)  # 1 hour ban
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Suspicious activity detected"
            )
        
        # Check for common attack patterns in path
        suspicious_paths = [
            "wp-admin", "admin", "phpmyadmin", ".env", "config",
            "backup", "sql", "dump", ".git", ".svn"
        ]
        
        path_lower = str(request.url.path).lower()
        if any(pattern in path_lower for pattern in suspicious_paths):
            await self._log_suspicious_activity(ip, "suspicious_path")
    
    async def _log_suspicious_activity(self, ip: str, activity_type: str):
        """Log suspicious activity for monitoring."""
        activity_key = f"{self.suspicious_activity_prefix}:{ip}"
        activity_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": activity_type,
            "ip": ip
        }
        
        # Store in Redis with expiration
        self.redis.lpush(activity_key, json.dumps(activity_data))
        self.redis.expire(activity_key, 86400)  # 24 hours
        
        # Check if IP should be banned (multiple suspicious activities)
        activity_count = self.redis.llen(activity_key)
        if activity_count >= 5:  # 5 suspicious activities
            await self._ban_ip(ip, duration=3600)  # 1 hour ban
    
    async def _ban_ip(self, ip: str, duration: int = 3600):
        """Ban IP address for specified duration."""
        ban_key = f"{self.ip_ban_prefix}:{ip}"
        self.redis.setex(ban_key, duration, "banned")
    
