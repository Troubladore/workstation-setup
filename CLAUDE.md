# Claude Development Guidelines

Development patterns and Git workflows established for the workstation-setup repository, following conventions from the data-eng-template sibling repository.

## 🔄 Git Workflow Standards

### Conventional Commits Format
All commits follow the **Conventional Commits** specification:

```
<type>: <description>

[optional body]

[optional footer]
```

**Commit Types:**
- `feat:` - New features or enhancements
- `fix:` - Bug fixes and corrections
- `docs:` - Documentation changes
- `style:` - Code formatting and style improvements
- `refactor:` - Code restructuring without changing functionality
- `test:` - Adding or modifying tests
- `chore:` - Maintenance tasks

**Examples:**
```bash
git commit -m "feat: add platform automation scripts"
git commit -m "fix: resolve authentication configuration issue"
git commit -m "docs: update API reference documentation"
```

### Branching Strategy
- **Main branch**: `main` (protected, requires PRs)
- **Feature branches**: `feature/descriptive-name`
- **Bug fix branches**: `fix/issue-description`
- **Documentation branches**: `docs/section-name`

**Workflow:**
1. Create feature branch from main: `git checkout -b feature/your-feature-name`
2. Make changes and commit with conventional format
3. Push branch: `git push -u origin feature/your-feature-name`
4. Create PR targeting main
5. Review, approve, and merge

### Pull Request Process

**PR Title Format**: Use conventional commit format
- `feat: add new pipeline feature`
- `fix: resolve configuration loading issue`
- `docs: update getting started guide`

**PR Requirements:**
1. ✅ Clear title following conventional commits
2. ✅ Comprehensive description explaining changes
3. ✅ Link to related issues (`Closes #X` or `Related to #X`)
4. ✅ Testing plan with checkboxes for reviewers
5. ✅ Impact assessment and documentation updates

**PR Template Structure:**
```markdown
## 🎯 Objective
Brief description of what this PR accomplishes

## 📋 Changes
- List of key changes made
- New features or components added
- Configurations updated

## 🧪 Testing Plan
Before merging, please verify:
- [ ] Specific test items
- [ ] Configuration validations
- [ ] Documentation accuracy

## 🔗 Related Issues
Closes #X - Brief issue description

## 📊 Impact
Description of expected impact on the platform
```

## 📝 Code Quality Standards

### Before Committing
- Run tests: `make test` (if available)
- Format code: Follow project formatting standards
- Check configurations: Validate YAML/JSON syntax
- Test changes: Verify functionality in clean environment

### Documentation Standards
- Update relevant documentation for user-facing changes
- Include code examples in documentation
- Follow established documentation patterns (layered approach)
- Use clear, concise language with progressive complexity

### Security Practices
- Never commit secrets or credentials
- Use environment variables for sensitive configuration
- Follow principle of least privilege
- Implement proper authentication patterns

## 🏗️ Project Architecture Patterns

### Three-Layer Architecture
1. **Layer 1**: Platform Foundation (Infrastructure, Prerequisites)
2. **Layer 2**: Data Processing (DataKits, dbt Projects)
3. **Layer 3**: Orchestration (Airflow DAGs, Examples)

### Documentation Structure
- **Parent pages**: High-level overviews with navigation
- **Child pages**: Detailed implementation guides
- **Progressive learning**: Beginner → Advanced pathways
- **Production-ready examples**: All code is battle-tested

## 🤖 AI Development Notes

### Commit Generation
When creating commits, always include:
```
🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Issue Creation
- Use comprehensive issue templates
- Include clear objectives and success criteria
- Break large features into manageable chunks
- Link related PRs and track progress

### PR Management
- Create feature branches for logical groupings
- Never commit directly to main
- Include thorough testing plans
- Document architectural decisions

## 📊 Development Statistics Tracking

### Implementation Metrics
- Track lines of code/documentation added
- Monitor test coverage improvements
- Measure documentation completeness
- Assess architectural compliance

### Quality Gates
- All PRs require review before merge
- Documentation must be updated for user-facing changes
- Security patterns must be followed
- Performance implications must be considered

## 🔄 Continuous Improvement

### Learning from data-eng-template
- 73% conventional commit adherence (target: 100%)
- Professional branching and PR patterns
- Comprehensive CONTRIBUTING.md guidance
- Quality-first development approach

### Repository Evolution
- Regular documentation updates
- Continuous pattern refinement
- Community feedback integration
- Best practice standardization

---

*This document should be updated as patterns evolve and new practices are established.*