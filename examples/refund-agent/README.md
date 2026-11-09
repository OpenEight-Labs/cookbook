# A refund assistant, governed before it acts

The customer asks for a refund. The agent looks up the order, then calls
`issue_refund`. OpenEight allows, requires approval, or denies that call before
the handler executes. The handler records a **simulated receipt** in memory;
no real money moves. LangChain and Deep Agents use the same two business tools.

## Install and connect

Use standard CPython 3.11–3.14. This example is qualified with LangChain 1.4.3,
Deep Agents 0.7.23 and the dependency versions in `requirements-qualified.txt`.
Install OpenEight normally; the example download contains neither SDK nor
verifier code. From this directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install openeight
pip install -r requirements-qualified.txt '.[test]'
```

With uv, from the same directory:

```bash
uv add openeight
uv sync --extra test
```

`requirements-qualified.txt` records the exact dependency closure used for offline
qualification. Keep your lockfile aligned with the supported framework versions.

Create a managed LangChain Agent in your OpenEight Workspace and save its key.
Set these variables in your shell; `.env.example` lists the same placeholders.
The program reads the shell environment and does not load `.env` automatically.

```bash
export OPENEIGHT_ENDPOINT='https://<your-openeight-api-host>'
export OPENEIGHT_API_KEY='<your-agent-api-key>'
export OPENEIGHT_AGENT_NAME='<your-immutable-agent-name>'
export REFERENCE_AGENT_MODEL='openai:<a-tool-calling-model-enabled-for-your-account>'
export OPENAI_API_KEY='<your-openai-api-key>'
```

The model and provider are explicit; calls use your provider account. Hosted
HTTPS must have a certificate trusted by the SDK. Loopback HTTP is optional for
local development. Ambient `SSL_CERT_FILE` does not configure this SDK transport.

## Configure new tools once

Invocation publishes tools automatically. If these tools are already configured,
skip to the three requests. For a new Agent, publish schemas without running the
model so you can configure their policies first:

```bash
python langchain_agent.py publish
```

Expect `catalog_delivery: "acknowledged"` and the native-to-catalog `bindings`.
Publication registers schemas; console policy activation is still required.

In the console, open this Agent and review its catalog:

- Classify `lookup_order` as Read. It emits execution telemetry without a Decision.
- Classify `issue_refund` as Write. Configure a Tool policy selecting the native
  integer field `amount_minor`. All amounts are **USD cents**: $50 is 5,000.
- Set this intent, optionally using Assist: “Deny nonpositive amounts. Allow
  refunds from 1 through 5,000 cents. Require approval from 5,001 through 20,000
  cents. Deny amounts above 20,000 cents.” Review, test and activate the policy
  and its exact Tool binding. The application does not install policy.

Save console policy cases for 0, 1, 5,000, 5,001, 20,000 and 20,001 cents; expect
respectively deny, allow, allow, approval, approval and deny. Confirm readiness
before invoking. These policy tests use representative inputs; the business
handler separately enforces the selected order and its full amount.

## Try the three requests

```bash
python langchain_agent.py run ORD-1041
python langchain_agent.py run ORD-1042
python langchain_agent.py run ORD-1043
```

| Order and fixed customer request | Expected result |
|---|---|
| ORD-1041: “Order ORD-1041 arrived damaged. Please refund $25.” | Allow 2,500 cents; `receipt_recorded` and one simulated receipt |
| ORD-1042: “Order ORD-1042 arrived damaged. Please refund $180.” | Approval required for 18,000 cents; zero effects while pending; one receipt after approval and exact Decision replay |
| ORD-1043: “Order ORD-1043 arrived damaged. Please refund $500.” | Deny 50,000 cents; `deny` and no receipt |

Keep the $180 process running. Find its pending request under this Agent in the
console and approve it. The SDK polls for up to **one hour**, configured as
`ApprovalConfig(timeout=3600)`, and replays the original Decision before dispatch.
A rejection, expiry or local timeout executes no refund. The backend approval
expiry is independent of this local wait. Approval after local waiting stops
does not revive that invocation. Blocked outcomes exit nonzero by design.

A model-only answer is `missing_refund_attempt`, a failed demonstration rather
than proof of denial. Model prose is not a receipt. `delivery` reports telemetry
acknowledgment separately from the local effect; failed/pending delivery does not
undo a recorded receipt. Do not retry a recorded refund to fix telemetry.

## Deep Agents and async execution

Create a **separate Deep Agents Agent/key**, update `OPENEIGHT_AGENT_NAME` and
`OPENEIGHT_API_KEY`, then run the same commands with `deepagents_agent.py`.
Its in-memory `StateBackend` adds native filesystem tools; use the printed
bindings to review their actual catalog names, classifications and write policies
too. The example disables the general-purpose child and adds no subagents or shell.

Sync is the default. Add `--execution async` to either runner's `publish` or `run`
command to use `apublish` or `ainvoke` with the same behavior. The SDK opens
and settles a temporary session for each call, including inline approval waiting.
No explicit managed context or flush is needed for these ordinary calls.

## Inspect and verify

Under the selected Agent, inspect the Run, lookup Event, refund Decision and,
for approval, the human actor and replay. An authorized execution Event links to
its Decision. Compare those records with the printed local receipt. Blocking
without a returned Decision reports a safe state without inventing IDs. Missing
configuration or unavailable authorization must leave receipts empty.

Run the offline checks with `python -m pytest`. These use real SDK/native
framework code and doubles for external model/control services. They do not
qualify your provider account or backend. Usage/spend requires model telemetry
and pricing; unpriced usage is not free. Use the console's Cost model and Audit
pages to inspect pricing and evidence. An audit bundle does not prove a payment
occurred.

Receipts and duplicate protection exist only in the current process. Each new
process starts a fresh simulated demonstration. There is no restart/resume or
cross-process exactly-once guarantee. For durable recovery, use the supported
SDK's advanced recovery guidance and destination reconciliation rather than
extending this in-memory example to real payments.

## SDK availability and license

The managed runners require an OpenEight SDK release supporting these APIs. If
`pip install openeight` cannot find a distribution on your package index, obtain
an available SDK release from OpenEight before running them. The automated
cookbook CI checks scenario logic without the SDK; managed integration tests are
also available through the workflow's manual option.

This example is covered by the repository's [MIT license](../../LICENSE).
The OpenEight SDK and third-party dependencies retain their own licenses.
