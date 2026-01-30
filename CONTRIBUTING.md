# Contributing to Video Generator

Thank you for your interest in contributing! This project welcomes contributions from everyone.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- A clear description of the problem
- Steps to reproduce the issue
- Your environment (OS, Python version, Node version)
- Expected vs actual behavior
- Any relevant logs or error messages

### Suggesting Features

Feature requests are welcome! Please open an issue with:
- A clear description of the feature
- Use cases and examples
- Why this feature would be valuable

### Submitting Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the code style guidelines below
3. **Test your changes** to ensure they work as expected
4. **Update documentation** if you're adding or changing functionality
5. **Commit your changes** with clear, descriptive commit messages
6. **Push to your fork** and submit a pull request

## Code Style Guidelines

### Python Code
- Follow [PEP 8](https://pep8.org/) style guide
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose

### TypeScript Code
- Use consistent indentation (2 spaces)
- Add type annotations
- Follow existing code patterns in the project

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Keep the first line under 50 characters
- Add detailed description if needed in the commit body

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/video-generator.git
cd video-generator

# Install Node dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Testing

Before submitting a pull request:
- Test your changes manually with the CLI
- Ensure existing functionality still works
- Test edge cases and error handling

## Questions?

Feel free to open an issue if you have questions about contributing!

## Code of Conduct

Be respectful and constructive in all interactions. We aim to foster an inclusive and welcoming community.
