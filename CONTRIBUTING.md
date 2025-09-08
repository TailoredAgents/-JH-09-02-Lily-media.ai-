# Contributing to Lily Media AI for Pressure Washing

Thank you for your interest in contributing to Lily Media AI! This document provides guidelines for contributing to our pressure washing industry-focused social media automation platform.

## 🤝 How to Contribute

### Reporting Issues

1. **Search Existing Issues**: Before creating a new issue, please search existing ones to avoid duplicates
2. **Use Issue Templates**: Use the provided issue templates for bug reports and feature requests
3. **Provide Details**: Include as much relevant information as possible:
   - Operating system and version
   - Python/Node.js versions
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs
   - Screenshots if applicable

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/ai-social-media-agent.git
   cd ai-social-media-agent
   ```

2. **Create Virtual Environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   # Backend dependencies
   pip install -r requirements.txt
   pip install -e ".[dev]"
   
   # Frontend dependencies
   cd frontend
   npm install
   ```

4. **Setup Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

5. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Run Tests**
   ```bash
   # Backend tests
   pytest
   
   # Frontend tests
   cd frontend
   npm test
   ```

### Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix-name
   ```

2. **Make Changes**
   - Follow the coding standards outlined below
   - Write tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new social media integration"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

## 📋 Coding Standards

### Python (Backend)

- **Formatting**: Use Black (`black .`)
- **Import Sorting**: Use isort (`isort .`)
- **Linting**: Use flake8 (`flake8 backend/`)
- **Type Hints**: Required for all functions and methods
- **Docstrings**: Use Google-style docstrings for all public functions
- **Line Length**: 88 characters maximum

**Example:**
```python
from typing import Optional, List
from pydantic import BaseModel

def create_social_post(
    content: str, 
    platforms: List[str], 
    scheduled_time: Optional[datetime] = None
) -> SocialPost:
    """Create a new social media post.
    
    Args:
        content: The post content text
        platforms: List of platform names to post to
        scheduled_time: Optional scheduling time
        
    Returns:
        Created SocialPost instance
        
    Raises:
        ValidationError: If content or platforms are invalid
    """
    # Implementation here
    pass
```

### JavaScript/React (Frontend)

- **Formatting**: Use Prettier (`npm run format`)
- **Linting**: Use ESLint (`npm run lint`)
- **Component Structure**: Use functional components with hooks
- **TypeScript**: Prefer TypeScript where possible
- **Testing**: Write tests for all components and hooks

**Example:**
```jsx
import React, { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';

interface CreatePostProps {
  onSuccess: (post: SocialPost) => void;
  platforms: string[];
}

export const CreatePost: React.FC<CreatePostProps> = ({ 
  onSuccess, 
  platforms 
}) => {
  const [content, setContent] = useState('');
  
  const createPostMutation = useMutation({
    mutationFn: (postData: CreatePostData) => api.createPost(postData),
    onSuccess: (post) => {
      onSuccess(post);
      setContent('');
    },
  });

  const handleSubmit = useCallback((e: FormEvent) => {
    e.preventDefault();
    createPostMutation.mutate({ content, platforms });
  }, [content, platforms, createPostMutation]);

  return (
    <form onSubmit={handleSubmit}>
      {/* Component implementation */}
    </form>
  );
};
```

## 🧪 Testing Requirements

### Backend Testing

- **Minimum Coverage**: 80% overall, 90% for critical paths
- **Test Types**: Unit, integration, and API tests
- **Test Structure**: Use pytest fixtures and factories
- **Mocking**: Mock external services (OpenAI, social media APIs)

```python
# Example test structure
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

class TestContentAPI:
    def test_create_content_success(self, client: TestClient, mock_openai):
        """Test successful content creation."""
        # Test implementation
        pass
    
    def test_create_content_invalid_data(self, client: TestClient):
        """Test content creation with invalid data."""
        # Test implementation
        pass
```

### Frontend Testing

- **Minimum Coverage**: 60% overall
- **Test Types**: Component, hook, and integration tests
- **Testing Library**: React Testing Library preferred
- **Mocking**: Mock API calls and external dependencies

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CreatePost } from './CreatePost';

describe('CreatePost', () => {
  it('creates post successfully', async () => {
    const mockOnSuccess = jest.fn();
    const queryClient = new QueryClient();
    
    render(
      <QueryClientProvider client={queryClient}>
        <CreatePost onSuccess={mockOnSuccess} platforms={['twitter']} />
      </QueryClientProvider>
    );
    
    // Test implementation
  });
});
```

## 🔒 Security Guidelines

### Sensitive Data
- **Never commit API keys, secrets, or credentials**
- **Use environment variables for all configuration**
- **Sanitize user inputs properly**
- **Follow OWASP security guidelines**

### Social Media Integration
- **Handle OAuth flows securely**
- **Respect API rate limits**
- **Store tokens encrypted**
- **Implement proper error handling**

### Authentication
- **Use Auth0 best practices**
- **Validate JWT tokens properly**
- **Implement role-based access control**
- **Secure sensitive endpoints**

## 📚 Documentation

### Code Documentation
- **Docstrings**: All public functions must have comprehensive docstrings
- **Comments**: Explain complex logic and business rules
- **Type Hints**: Required for all Python functions
- **README Updates**: Update relevant documentation when adding features

### API Documentation
- **OpenAPI/Swagger**: Automatically generated from FastAPI
- **Examples**: Provide request/response examples
- **Error Codes**: Document all possible error responses
- **Authentication**: Document auth requirements

## 🐛 Bug Fixes

### Investigation Process
1. **Reproduce Locally**: Confirm the bug exists
2. **Isolate the Problem**: Identify the root cause
3. **Write Failing Test**: Create a test that demonstrates the bug
4. **Fix the Issue**: Implement the minimal fix
5. **Verify Fix**: Ensure the test passes and no regressions occur

### Bug Fix Checklist
- [ ] Issue reproduced locally
- [ ] Root cause identified
- [ ] Test case written (that initially fails)
- [ ] Fix implemented
- [ ] All tests pass
- [ ] Manual testing completed
- [ ] Documentation updated if necessary

## 🚀 Feature Development

### Feature Planning
1. **Discussion**: Discuss feature in GitHub Discussions or issues
2. **Design Document**: For large features, create a design document
3. **API Design**: Plan API changes and backwards compatibility
4. **Implementation Plan**: Break down into smaller tasks

### Feature Checklist
- [ ] Feature discussed and approved
- [ ] API design reviewed
- [ ] Implementation completed
- [ ] Tests written (unit, integration, e2e)
- [ ] Documentation updated
- [ ] Performance impact assessed
- [ ] Security implications reviewed
- [ ] Backwards compatibility maintained

## 🎯 Pull Request Guidelines

### Before Submitting
- [ ] Code follows project standards
- [ ] All tests pass locally
- [ ] Pre-commit hooks pass
- [ ] Changes are well-documented
- [ ] No merge conflicts

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] Documentation updated
```

### Review Process
1. **Automated Checks**: All CI/CD checks must pass
2. **Code Review**: At least one maintainer approval required
3. **Testing**: Reviewer should test the changes
4. **Documentation**: Verify documentation is adequate

## 🏷️ Commit Message Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build process or auxiliary tool changes
- `perf`: Performance improvements
- `ci`: CI/CD changes

### Examples
```
feat(api): add Instagram post scheduling
fix(auth): resolve token refresh issue
docs(readme): update installation instructions
test(content): add unit tests for content generation
```

## 🎖️ Recognition

Contributors will be recognized in:
- GitHub contributors list
- CHANGELOG.md for significant contributions
- README.md acknowledgments
- Social media shout-outs for major features

## 📞 Getting Help

- **GitHub Discussions**: For questions and general discussion
- **GitHub Issues**: For bug reports and feature requests
- **Discord**: Real-time chat with the community
- **Email**: team@aisocialmediaagent.com for sensitive issues

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to the AI Social Media Content Agent! 🚀