# Contributing to Hi-Hola

Thank you for considering a contribution to Hi-Hola! Contributions may
include bug fixes, features, tests, documentation improvements,
accessibility improvements, and developer-experience changes.

## 1. Before you start

-   Read the [README](README.md) to understand the project.
-   Follow the [setup guide](docs/setup.md) to prepare your development
    environment.
-   Check existing issues and pull requests to avoid duplicating work.
-   For a substantial change, open an issue first to discuss the problem
    and proposed approach.

If you are unsure where to start, open an issue describing what you
would like to work on.

## 2. Ways to contribute

### Report a bug

Use the **Bug report** issue template. Include: - What you expected to
happen. - What actually happened. - Steps to reproduce the issue. -
Relevant environment details and logs, with secrets and personal data
removed.

### Suggest an enhancement

Use the **Feature request** issue template. Explain the user problem,
the proposed behavior, and any alternatives you considered.

### Improve documentation

Documentation contributions are welcome. Keep instructions reproducible,
use the names of commands and files that exist in the repository, and
update related documentation when behavior changes.

## 3. Development workflow

1.  Fork the repository (for external contributors) or use an authorized
    repository clone.
2.  Sync your local copy with the upstream default branch.
3.  Create a focused branch from the current default branch.
4.  Make a small, logically grouped change.
5.  Add or update tests and documentation where relevant.
6.  Run the project's tests and quality checks locally.
7.  Push your branch and open a pull request against the default branch.
8.  Respond to review comments and update the pull request as needed.

Suggested branch names:

``` text
feature/short-description
fix/short-description
docs/short-description
test/short-description
```

Avoid committing directly to the protected default branch.

## 4. Code quality and tests

Before opening a pull request, run the checks supported by the
repository. The project currently uses pytest for tests and Ruff for
code quality.

``` bash
pytest
ruff check .
```

If the repository's `pyproject.toml` defines additional formatting,
type-checking, or test commands, follow those as well. Mention any check
you could not run and why.

For changes involving speech or model services: - Keep tests
deterministic where possible. - Mock external/local model services in
unit tests when appropriate. - Do not require large model downloads for
ordinary unit tests. - Include tests for invalid inputs and failure
paths.

## 5. Pull request expectations

A pull request should: - Have a clear, descriptive title. - Explain the
problem and the change. - Link related issues using GitHub keywords
where applicable (for example, `Closes #123`). - Include tests performed
and their results. - Include screenshots or a short recording for
visible UI changes, when useful. - Update documentation when setup,
usage, configuration, or behavior changes.

Keep pull requests focused. If a change is large, consider splitting it
into smaller reviewable pull requests.

Use the repository's pull request template when opening a PR.

## 6. Review and merging

Hi-Hola uses pull requests for changes to the protected default branch.
The repository's branch rules require at least one approving review
before merging, along with approval of the most recent reviewable push
if that rule is enabled.

A reviewer may: - Approve the pull request. - Request changes. - Leave
comments or questions.

Please address review feedback and push follow-up commits to the same
branch. Required checks and review rules must pass before the PR can be
merged.

Do not assume that opening a PR or passing CI means it is automatically
approved.

## 7. Commit guidance

Write concise commit messages that describe the change. For example:

``` text
docs: clarify local setup instructions
fix: handle empty speech transcription
test: cover pronunciation input validation
```

Use a consistent style within a contribution. Avoid unrelated formatting
changes in a functional pull request.

## 8. Security, privacy, and model use

-   Never commit passwords, tokens, API keys, or private configuration.
-   Do not commit private recordings or personal learner data.
-   Remove sensitive information from logs and issue reports.
-   Respect the licenses and terms of use for dependencies, models, and
    external services.
-   Do not add model weights or large generated files unless the project
    explicitly intends to distribute them.

For a suspected security vulnerability, avoid publishing exploit details
in a public issue. Contact the project maintainer privately through the
repository's available contact method.

## 9. Code of conduct

Be respectful, constructive, and welcoming. Critique code and ideas
rather than people. Assume good intent, explain feedback clearly, and
help keep collaboration accessible to contributors with different
experience levels.

## 10. Questions

If the contribution guidance does not cover your situation, open an
issue with your question or contact the repository maintainer through
the contact information published in the repository.
