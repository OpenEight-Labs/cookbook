import asyncio

import pytest
from control_service import ControlService
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from openeight import APIError, BlockedError, OpenEightConfig
from openeight.langchain import ApprovalConfig, _owner

import deepagents_agent
import langchain_agent
from runner import blocked, configuration, run_async, run_sync
from scenario import Scenario


class ToolModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture(autouse=True)
def control(monkeypatch):
    ControlService.instances = []
    ControlService.outcome = "allow"
    ControlService.pending_check = None
    monkeypatch.setattr(_owner, "Client", ControlService)


def config():
    return OpenEightConfig(
        endpoint="http://localhost:7777",
        credential="ctk_test",
        agent_name="refund",
        on_block="raise",
        approval=ApprovalConfig(
            timeout=0.04, poll_interval=0.001, poll_max_interval=0.002
        ),
    )


def model(scenario, missing=False):
    def call(name, args, identity):
        return AIMessage(
            content="", tool_calls=[{"name": name, "args": args, "id": identity}]
        )

    return ToolModel(
        responses=(
            [
                call("lookup_order", {"order_id": scenario.order.order_id}, "lookup"),
                call(
                    "issue_refund",
                    {
                        "order_id": scenario.order.order_id,
                        "amount_minor": scenario.order.amount_minor,
                    },
                    "refund",
                ),
            ]
            if not missing
            else []
        )
        + [AIMessage(content="done")]
    )


def execute(framework, mode, scenario, command="run", missing=False):
    owner = framework.build(model(scenario, missing), scenario, config())
    value = (
        run_sync(owner, scenario, command)
        if mode == "sync"
        else asyncio.run(run_async(owner, scenario, command))
    )
    return value, ControlService.instances[-1]


@pytest.mark.parametrize("framework", [langchain_agent, deepagents_agent])
@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize(
    "outcome,order_id,state",
    [
        ("allow", "ORD-1041", "receipt_recorded"),
        ("approved", "ORD-1042", "receipt_recorded"),
        ("deny", "ORD-1043", "deny"),
        ("rejected", "ORD-1042", "approval_rejected"),
        ("expired", "ORD-1042", "approval_expired"),
        ("pending", "ORD-1042", "approval_wait_timed_out"),
        ("stale", "ORD-1042", "AUTHORIZATION_STALE"),
    ],
)
def test_native_attempts(framework, mode, outcome, order_id, state):
    ControlService.outcome = outcome
    scenario = Scenario(order_id)
    ControlService.pending_check = staticmethod(
        lambda: not scenario.receipts or pytest.fail("effect while pending")
    )
    result, client = execute(framework, mode, scenario)
    assert result["state"] == state
    assert len(scenario.receipts) == (1 if state == "receipt_recorded" else 0)
    assert client.closed and client.requests
    assert all(
        request["selected_values"]
        == [{"path": "amount_minor", "value": scenario.order.amount_minor}]
        for request in client.requests
    )
    assert len(client.requests) == (2 if outcome == "approved" else 1)
    if outcome == "approved":
        assert client.requests[0] == client.requests[1]
    if outcome == "stale":
        assert "decision_id" not in result and "run_id" not in result
    elif state != "receipt_recorded":
        assert result["decision_id"] == client.requests[0]["decision_id"]
    events = [
        event
        for batch in client.writes
        for event in batch.get("events", [])
        if event.get("observation_kind") == "tool_call"
    ]
    refund_id = client.requests[0]["tool_id"]
    assert any(event.get("tool_id") != refund_id for event in events)
    assert len([event for event in events if event.get("tool_id") == refund_id]) == (
        1 if state == "receipt_recorded" else 0
    )
    # A late server approval cannot restart the completed local invocation.
    if outcome == "pending":
        client.outcome = "approved"
        assert client.approval_state() == "approved" and not scenario.receipts


@pytest.mark.parametrize("framework", [langchain_agent, deepagents_agent])
@pytest.mark.parametrize("mode", ["sync", "async"])
def test_publish_and_missing_attempt(framework, mode):
    scenario = Scenario("ORD-1041")
    result, client = execute(framework, mode, scenario, "publish")
    assert result["catalog_delivery"] == "acknowledged" and result["bindings"]
    assert not client.requests and not client.writes and not scenario.receipts
    assert client.closed
    result, client = execute(framework, mode, scenario, missing=True)
    assert result["state"] == "missing_refund_attempt" and not client.requests


@pytest.mark.parametrize("framework", [langchain_agent, deepagents_agent])
@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("outcome", ["unavailable", "revoked"])
def test_service_unavailable_has_no_effect(framework, mode, outcome):
    ControlService.outcome = outcome
    scenario = Scenario("ORD-1041")
    with pytest.raises(APIError):
        execute(framework, mode, scenario)
    assert not scenario.receipts
    assert ControlService.instances[-1].closed


def test_safe_blocked_result_and_one_hour_config(monkeypatch):
    for key, value in {
        "OPENEIGHT_ENDPOINT": "http://localhost:7777",
        "OPENEIGHT_API_KEY": "ctk_test",
        "OPENEIGHT_AGENT_NAME": "refund",
    }.items():
        monkeypatch.setenv(key, value)
    assert configuration().approval.timeout == 3600
    assert configuration().on_block == "raise"
    assert blocked(BlockedError(None, "governance_unconfigured")) == {
        "state": "governance_unconfigured",
        "explanation": "Execution blocked without a returned Decision.",
    }


@pytest.mark.parametrize("command", ["publish", "run"])
def test_cli_output_serializes(monkeypatch, capsys, command):
    import json
    import sys
    from runner import main

    for key, value in {
        "OPENEIGHT_ENDPOINT": "http://localhost:7777",
        "OPENEIGHT_API_KEY": "ctk_test",
        "OPENEIGHT_AGENT_NAME": "refund",
        "REFERENCE_AGENT_MODEL": "openai:explicit-test-model",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "argv", ["langchain_agent.py", command])
    assert (
        main(
            lambda _, scenario, config: langchain_agent.build(
                model(scenario), scenario, config
            )
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == (
        "publication" if command == "publish" else "receipt_recorded"
    )
