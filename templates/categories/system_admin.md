### Category: System Administration

Tasks involving server configuration, service deployment, virtualization, process/resource management, and infrastructure management.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Service Configuration:*
- Configure web servers (Nginx, Apache) with specific logging and rate limiting
- Set up SSH/VPN access with security hardening
- Email server setup (Postfix, Mailman, mailing lists)
- SSL/TLS certificate generation and configuration (OpenSSL)
- Multi-branch Git server with web deployment integration

*Virtualization & Containers:*
- QEMU/VM management and OS installation (Alpine, Windows, custom images)
- Container orchestration basics
- Dockerfile analysis and optimization (without running Docker)
- docker-compose.yml configuration validation and fixing

*Process & Resource Management:*
- Debug and fix zombie/orphan process issues
- Configure process priorities and resource limits (nice, ulimit, cgroups)
- Implement process supervision and auto-restart
- Debug file descriptor leaks and handle limits
- Memory usage analysis and OOM debugging
- CPU/IO performance bottleneck identification
- Background job management (nohup, screen, tmux sessions)

*System Recovery & Maintenance:*
- System recovery from various failure modes
- Automated deployment pipelines (Git push to web deployment)
- Service monitoring, logging, and alerting
- Network configuration and troubleshooting
- Disk space management and cleanup automation
- Log rotation configuration and management

**Skills & Tools** (tag suggestions for your task):
- Core: `system`, `sys-admin`, `troubleshooting`, `process-management`
- Services: `nginx`, `apache`, `ssh`, `docker`, `qemu`, `postfix`, `mailman`
- Process: `systemd`, `supervisor`, `cgroups`, `ulimit`, `nice`, `ionice`
- Security: `openssl`, `certificates`, `tls`
- Monitoring: `top`, `htop`, `ps`, `lsof`, `strace`, `perf`
- Related: `virtualization`, `networking`, `vnc`, `telnet`

**Possible Input Data** (be creative with environment files!):
- VM/OS images (`.iso` files like Alpine, `.qcow2` disk images, Windows 3.11 floppies)
- Configuration files (`nginx.conf`, `supervisord.conf`, `sshd_config`)
- Docker artifacts (Dockerfiles, compose files for analysis)
- Network configs (iptables rules, DNS zone files, hosts files)
- SSL/TLS materials (certificates, CSRs, CA chains, `.pem`, `.key`, `.crt`)
- Systemd units (service files, timer units with issues)
- Log files (syslog, journald exports, application logs)
- Git server configurations (bare repos, hooks, deployment scripts)
- Mail server configs (Postfix main.cf, Mailman settings)
- Process dumps (ps output, /proc filesystem snapshots)
- Resource usage data (top/htop output, cgroup configurations)
- Boot configurations (GRUB configs, kernel parameters)

**Verification Approaches**:
- Test service availability (SSH, HTTP, VNC, telnet on specific ports)
- Check configuration files have correct settings
- Verify network connectivity and routing
- Validate security configurations (certificate validity, key permissions)
- Test Git clone/push/pull functionality
- Verify email delivery and mailing list functionality
- Check process running status and resource usage
- Verify no zombie processes remain
- Confirm resource limits are correctly applied

**Remember**: Design realistic sysadmin scenarios that test understanding of service configuration, process lifecycle, and infrastructure setup. Combine multiple services or create interesting deployment and orchestration challenges!
