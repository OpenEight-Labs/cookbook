# OpenEight cookbook

Runnable examples for governing and observing agents with OpenEight. Each recipe
has its own dependencies, setup instructions and offline tests.

| Recipe | Frameworks | What it demonstrates |
| --- | --- | --- |
| [Refund agent](examples/refund-agent/) | LangChain, Deep Agents · Python sync and async | Tool registration, policy allow/deny, human approval, Decision replay and execution telemetry |

## Start with the refund agent

```bash
git clone https://github.com/OpenEight-Labs/cookbook.git
cd cookbook/examples/refund-agent
```

Follow the [recipe README](examples/refund-agent/README.md) to install dependencies,
connect an Agent, configure its policy in the console and try three requests:
$25 allowed, $180 requiring approval and $500 denied. The refund handler records
simulated receipts; no real money moves. Model calls use your provider account.

You need an OpenEight Workspace, an Agent API key, and an OpenEight SDK release
supporting the documented managed APIs. Install the SDK with `pip install openeight`
or `uv add openeight`. If your package index does not yet provide it, obtain an
available SDK release from OpenEight before running the managed examples. This
repository does not bundle SDK or verifier code.

## Repository structure

Recipes live under `examples/<use-case>/`. A recipe may demonstrate one agent or
several cooperating agents. Framework runners share business logic when that makes
the comparison clearer. Each recipe remains independently installable and runnable.

## Tests

Automatic CI runs the refund scenario tests without the OpenEight SDK or provider
credentials. The workflow's manual **Run managed SDK tests** option additionally
installs `openeight` from the configured public index and runs the complete recipe
suite. Enable it when a compatible SDK distribution is available; a missing package
fails that job rather than substituting another implementation. Neither test job
calls a live model provider or OpenEight deployment.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). For problems or recipe ideas, open an
[issue](https://github.com/OpenEight-Labs/cookbook/issues). Do not include API keys
or private customer data.

## License

The examples and documentation in this repository are licensed under [MIT](LICENSE).
The OpenEight SDK and third-party dependencies are licensed separately.
