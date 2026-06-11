# Contributing to NEXUS B2B Lead Generation

First off, thank you for considering a contribution to NEXUS! It's people like you that make NEXUS such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots and animated GIFs if possible**
* **Include your environment details** (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and expected behavior**
* **Explain why this enhancement would be useful**

### Pull Requests

* Fill in the required template
* Follow the Python/TypeScript styleguides
* Include appropriate test cases
* End all files with a newline
* Avoid platform-dependent code

## Development Setup

1. **Fork the repository**
```bash
git clone https://github.com/YOUR_USERNAME/nexus-b2b-lead-generation.git
cd nexus-b2b-lead-generation
```

2. **Set up development environment**
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Frontend
cd ../frontend
npm install
```

3. **Create a branch for your changes**
```bash
git checkout -b feature/your-feature-name
```

4. **Make your changes and add tests**

5. **Run tests and linting**
```bash
# Backend
pytest
pylint app/
black app/

# Frontend
npm run lint
npm run test
```

6. **Commit and push**
```bash
git add .
git commit -m "Add your meaningful commit message"
git push origin feature/your-feature-name
```

7. **Open a Pull Request**

## Styleguides

### Python

* Use PEP 8 style guide
* Use Black for code formatting
* Use 4 spaces for indentation
* Use type hints
* Add docstrings to all functions and classes

```python
def get_leads(company_name: str, limit: int = 50) -> List[Lead]:
    """
    Retrieve leads for a company.
    
    Args:
        company_name: Name of the company
        limit: Maximum number of leads to return
        
    Returns:
        List of Lead objects
    """
    pass
```

### TypeScript/JavaScript

* Use Prettier for code formatting
* Use ESLint for linting
* Use 2 spaces for indentation
* Use meaningful variable names
* Add JSDoc comments

```typescript
/**
 * Fetch leads from the API
 * @param companyName - Name of the company
 * @param limit - Maximum number of leads
 * @returns Promise with leads data
 */
const fetchLeads = async (companyName: string, limit: number = 50): Promise<Lead[]> => {
  // Implementation
};
```

## Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

Example:
```
Add email validation for lead filtering

Fixes #123
- Added regex pattern for email validation
- Added unit tests for validation function
- Updated documentation
```

## Testing

All new features must include tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test
pytest tests/test_osint.py::test_email_search
```

Aim for >80% code coverage on new code.

## Documentation

* Update README.md if adding new features
* Add docstrings to all functions
* Keep CHANGELOG.md updated
* Update type hints

## Questions?

Feel free to open an issue with the `question` label or email burkefit2382@gmail.com

Thank you for contributing! 🎉
