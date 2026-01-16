# Security Policy

## Overview

Statement is an open-source financial intelligence platform. We take security seriously and are committed to maintaining a secure codebase for our users and contributors. This document outlines our security practices and how to responsibly report security vulnerabilities.

## Supported Versions

We actively maintain and provide security updates for the following versions:

| Version | Status | Support Until |
|---------|--------|----------------|
| 1.x (Latest) | Active | Current development |
| 0.x | Limited | Security fixes only |

We recommend always using the latest stable version for security patches and new features.

## Reporting a Security Vulnerability

**Please do not open public GitHub issues for security vulnerabilities.** This could expose the vulnerability before a fix is available.

### How to Report

If you discover a security vulnerability in Statement, please report it responsibly:

1. **Email**: Send a detailed report to `security@askstatement.com` (or the appropriate security contact)
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce (if applicable)
   - Potential impact
   - Suggested fix (if you have one)
   - Your contact information

3. **What to Expect**:
   - Initial response within 48 hours
   - Acknowledgment of the vulnerability
   - Updates on progress toward a fix
   - Credit in the security advisory (unless you prefer to remain anonymous)

### Responsible Disclosure Timeline

- **Day 1**: Report received and initial assessment
- **Days 2-7**: Investigation and patch development
- **Days 8-30**: Testing and preparation for release
- **Day 31**: Public disclosure and release of patch

We ask that you refrain from publicly disclosing the vulnerability for at least 90 days to allow time for patch development and deployment.

## Security Best Practices for Users

### Installation & Deployment

- **Always use the latest version**: Stay updated with the latest releases for security patches
- **Use HTTPS**: Deploy Statement with proper SSL/TLS certificates
- **Secure your environment**:
  - Keep environment variables secure
  - Use strong API keys and secrets
  - Never commit secrets to version control (use `.env.example` as a template)
  - Rotate credentials regularly

### Configuration

- **Authentication**: Enable all authentication features
- **API Keys**: Use strong, randomly generated API keys
- **Database Security**:
  - Use strong MongoDB credentials
  - Restrict database access to authorized networks
  - Enable MongoDB authentication
  - Regularly backup your data
- **Elasticsearch**:
  - Use authentication credentials
  - Restrict network access
  - Keep sensitive data encrypted at rest

### Monitoring & Maintenance

- **Monitor Logs**: Review application and system logs regularly
- **Update Dependencies**: Keep all dependencies current (see section below)
- **Security Scanning**: Run security scans on your deployment
- **Access Control**: Limit access to admin panels and sensitive features
- **Rate Limiting**: Enable and configure rate limiting to prevent abuse

### Third-Party Integrations

Statement integrates with several services. Secure your credentials:

- **Plaid**: Use secure API keys and refresh tokens regularly
- **Stripe**: Keep API keys confidential, use restricted API keys where possible
- **OpenAI**: Protect your API keys, monitor usage for anomalies
- **AWS S3**: Use IAM roles with minimal required permissions
- **Azure MSAL**: Keep client secrets secure

## Dependency Management

### Security Updates

We regularly:
- Monitor dependencies for security vulnerabilities using automated tools
- Update vulnerable dependencies promptly
- Test updates thoroughly before release
- Document breaking changes in release notes

### Dependencies to Monitor

**Backend (Python)**:
- FastAPI & Starlette
- Motor (MongoDB async driver)
- Python-Jose & Passlib (Authentication)
- OpenAI SDK
- Boto3 (AWS)

**Frontend (JavaScript)**:
- Next.js & React
- MSAL (Azure authentication)
- Axios (HTTP client)

### How to Check for Vulnerabilities

**Backend**:
```bash
cd backend
pip install safety
safety check
```

**Frontend**:
```bash
cd frontend
npm audit
npm audit fix  # For automatic fixes
```

## Known Security Considerations

### Current Limitations

1. **SQL Injection**: Not applicable (using document databases), but always validate user input
2. **CORS**: Configure CORS appropriately for your deployment
3. **Rate Limiting**: Configure based on your infrastructure capacity
4. **Data Encryption**: Ensure data in transit uses HTTPS; consider encryption at rest for sensitive data
5. **Secrets Management**: Never hardcode secrets; use environment variables

### Areas of Focus

- Regular security audits of AI agent interactions
- Validation of user queries to prevent prompt injection
- Proper authorization checks for financial data access
- Secure handling of API credentials and tokens
- Audit logging for financial transactions and data access

## Security Headers

When deploying Statement, implement these security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## Authentication & Authorization

- **Frontend**: Uses Azure MSAL for enterprise authentication
- **Backend**: Uses Python-Jose with JWT tokens and Passlib for password hashing
- **API Keys**: Implement proper API key management and rotation
- **Session Security**: Use secure, httpOnly cookies; set appropriate expiration times

## Incident Response

If a security incident occurs:

1. **Immediate Action**:
   - Assess the impact and scope
   - Contain the incident
   - Preserve evidence for investigation

2. **Notification**:
   - Notify affected users if data was compromised
   - Provide guidance on protective measures
   - Offer technical support

3. **Follow-up**:
   - Conduct a thorough investigation
   - Implement fixes to prevent recurrence
   - Release security update
   - Document lessons learned

## Contributing to Security

Want to help improve Statement's security?

- Review code for vulnerabilities
- Test security features thoroughly
- Suggest security improvements
- Report bugs responsibly
- Help with security documentation

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

## Compliance & Standards

Statement aims to follow security best practices:

- OWASP Top 10 prevention
- Secure coding standards
- Data protection and privacy principles
- Industry-standard encryption

If you're deploying Statement in a regulated environment (banking, healthcare, etc.), ensure your deployment meets applicable compliance requirements (PCI-DSS, HIPAA, SOC 2, etc.).

## Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/advanced/security/)
- [Node.js Security](https://nodejs.org/en/docs/guides/nodejs-security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE: Common Weakness Enumeration](https://cwe.mitre.org/)

## Questions?

For security-related questions:
- Email: `security@askstatement.com`
- Open a discussion (for non-sensitive topics)
- Check existing issues and documentation

---

Last Updated: January 2026

Thank you for helping keep Statement secure!
