# Contributing to Statement

Thank you for your interest in contributing to Statement! We welcome contributions from the community and appreciate your help in making this open-source financial intelligence platform better.

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Git

### Setting Up Your Development Environment

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Statement.git
   cd Statement
   ```

2. **Set up the backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   # Update .env with your configuration
   ```

3. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   # Create .env.local if needed
   ```

4. **Start the development environment**
   ```bash
   docker compose up -d
   ```

## How to Contribute

### Reporting Bugs

Before creating a bug report, please check if the issue already exists. When creating a bug report, include:

- **Clear title and description** - Be as descriptive as possible
- **Steps to reproduce** - Exact steps to reproduce the issue
- **Expected behavior** - What you expected to happen
- **Actual behavior** - What actually happened
- **Screenshots/logs** - If applicable
- **Environment** - OS, Python version, Node version, Docker version
- **Additional context** - Any other relevant information

### Suggesting Features

We love feature suggestions! When proposing a feature:

- **Use a clear, descriptive title**
- **Provide a detailed description** of the suggested feature
- **Explain the use case** - Why would this be useful?
- **List examples** - Show how other projects have implemented similar features
- **Explain the expected benefits**

### Pull Requests

We actively welcome your pull requests! Here's the process:

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-number-description
   ```

2. **Make your changes**
   - Follow the code style guidelines (see below)
   - Write clear, descriptive commit messages
   - Add tests for new functionality
   - Update documentation as needed

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "type: brief description

   Longer explanation if needed. Reference issues with #123."
   ```

   Commit types:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `style:` - Code style changes (formatting, missing semicolons, etc.)
   - `refactor:` - Code refactoring without feature changes
   - `perf:` - Performance improvements
   - `test:` - Test additions/changes
   - `chore:` - Build, dependency, or tooling changes

4. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request**
   - Use the pull request template
   - Fill in all relevant sections
   - Link related issues
   - Wait for review and feedback

## Code Style Guidelines

### Backend (Python)

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where possible
- Max line length: 100 characters
- Use 4 spaces for indentation
- Use descriptive variable and function names

Example:
```python
def calculate_financial_metrics(transactions: List[dict]) -> Dict[str, float]:
    """
    Calculate key financial metrics from transactions.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Dictionary containing calculated metrics
    """
    total_revenue = sum(t.get('amount', 0) for t in transactions if t.get('type') == 'income')
    return {'total_revenue': total_revenue}
```

### Frontend (JavaScript/React)

- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use functional components with hooks
- Use descriptive component and function names
- Use camelCase for variables and functions
- Use PascalCase for components
- Add PropTypes or TypeScript types

Example:
```javascript
const ChatMessage = ({ message, timestamp, sender }) => {
  return (
    <div className="chat-message">
      <p className="sender">{sender}</p>
      <p className="content">{message}</p>
      <span className="timestamp">{timestamp}</span>
    </div>
  );
};
```

## Testing

### Backend Tests
```bash
cd backend
pytest
# or with coverage
pytest --cov=.
```

### Frontend Tests
```bash
cd frontend
npm test
```

All pull requests must:
- Include tests for new functionality
- Pass all existing tests
- Maintain or improve code coverage

## Documentation

- Update `README.md` for significant changes
- Add docstrings to all functions and classes
- Update `.env.example` if adding new environment variables
- Document API changes in code comments
- Update relevant docs in comments

## Docker Development

To test your changes with Docker:

```bash
# Rebuild the containers with your changes
docker compose down
docker compose up --build

# Run backend tests
docker compose exec backend pytest

# Run frontend tests
docker compose exec frontend npm test
```

## Database Migrations

If your changes affect the database schema:

1. Document the migration in your PR
2. Ensure backward compatibility if possible
3. Include migration scripts in the `backend` directory if needed
4. Update the initialization scripts

## Performance Considerations

- Test with realistic data volumes
- Monitor database query performance
- Optimize API responses
- Consider rate limiting for external API calls
- Document any performance trade-offs

## Security

- Never commit secrets or API keys (use `.env.example` template)
- Validate and sanitize all user inputs
- Use environment variables for sensitive data
- Follow secure coding practices
- Report security vulnerabilities responsibly (see SECURITY.md if available)

## Review Process

1. A maintainer will review your PR within 2-5 business days
2. Please be responsive to feedback and comments
3. Make requested changes on the same branch
4. Once approved, your PR will be merged by a maintainer
5. Your contribution will be credited

## Release Process

Contributors don't need to worry about releases - the maintainers handle version bumping and deployments.

## Questions or Need Help?

- Open an issue for questions
- Check existing issues and discussions
- Review the documentation
- Ask in the community discussions section

## Recognition

Contributors are recognized in:
- The commit history
- Release notes for significant changes
- The project README (optional, upon request)

## License

By contributing to Statement, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

Thank you for helping make Statement better! 🎉
