# Contributing

Open an issue for a recipe idea or send a focused pull request with a runnable
example. Organize recipes by use case under `examples/`, including multi-agent
examples. Keep dependencies and tests within each recipe.

Each recipe should include:

- A README with prerequisites, installation, commands, console setup, expected
  outcomes and execution/recovery limitations.
- An `.env.example` containing placeholders only.
- Dependency metadata and tests that double external services.
- Clear distinctions between authorization, reported execution and actual effects.

Use `pip install openeight` or `uv add openeight` for the SDK. Keep model and
provider choices explicit. Do not vendor the SDK or verifier, commit credentials,
or use real payment effects in tests. CI should not require provider credentials.

For the refund recipe, follow its README to install dependencies, then run:

```bash
cd examples/refund-agent
python -m pytest
```

Scenario-only checks can run without the SDK:

```bash
python -m pip install 'langchain-core==1.6.7' 'pydantic==2.14.2' 'pytest>=8,<10'
python -m pytest tests/test_scenario.py
```

Contributions are accepted under this repository's MIT license. Only submit
material you have permission to contribute, and preserve applicable third-party
notices. Report SDK or service issues with the relevant version and non-secret
identifiers; never attach tokens, credentials or private request bodies.
