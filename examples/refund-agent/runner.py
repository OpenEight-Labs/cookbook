"""Shared command handling; framework composition stays in the two small runners."""

import argparse
import asyncio
import json
import os

from openeight import ApprovalTimeout, BlockedError, OpenEightConfig, SDKError
from openeight.langchain import ApprovalConfig

from scenario import ORDERS, Scenario


def configuration():
    return OpenEightConfig(
        endpoint=os.environ["OPENEIGHT_ENDPOINT"],
        credential=os.environ["OPENEIGHT_API_KEY"],
        agent_name=os.environ["OPENEIGHT_AGENT_NAME"],
        approval=ApprovalConfig(timeout=3600),
        on_block="raise",
    )


def blocked(error):
    result = {"state": error.state}
    if error.result is not None:
        result.update(decision_id=error.result.decision_id, run_id=error.result.run_id)
    else:
        result["explanation"] = "Execution blocked without a returned Decision."
    return result


def publication(owner, delivery):
    return {
        "state": "publication",
        "catalog_delivery": delivery.catalog_delivery_state,
        "bindings": [
            {key: row[key] for key in ("child_path", "native_name", "name")}
            for row in owner.catalog_snapshot().bindings
        ],
    }


def delivery_state(delivery):
    if delivery.failed_records or delivery.dropped_records:
        return "failed"
    return "pending" if delivery.pending_records else "acknowledged"


def run_sync(agent, scenario, command):
    if command == "publish":
        agent.publish()
        return publication(agent, agent.delivery_status())
    try:
        agent.invoke({"messages": [("user", scenario.order.prompt)]})
    except ApprovalTimeout as error:
        outcome = blocked(error)
    except BlockedError as error:
        outcome = blocked(error)
    else:
        outcome = {
            "state": "receipt_recorded"
            if scenario.receipts
            else "missing_refund_attempt"
        }
    return {
        **outcome,
        "receipts": scenario.receipts,
        "delivery": delivery_state(agent.delivery_status()),
    }


async def run_async(agent, scenario, command):
    if command == "publish":
        await agent.apublish()
        return publication(agent, agent.delivery_status())
    try:
        await agent.ainvoke({"messages": [("user", scenario.order.prompt)]})
    except ApprovalTimeout as error:
        outcome = blocked(error)
    except BlockedError as error:
        outcome = blocked(error)
    else:
        outcome = {
            "state": "receipt_recorded"
            if scenario.receipts
            else "missing_refund_attempt"
        }
    return {
        **outcome,
        "receipts": scenario.receipts,
        "delivery": delivery_state(agent.delivery_status()),
    }


def main(build):
    parser = argparse.ArgumentParser(
        description="Simulate a governed full-order refund."
    )
    parser.add_argument("command", choices=("publish", "run"))
    parser.add_argument("order", nargs="?", choices=tuple(ORDERS), default="ORD-1041")
    parser.add_argument("--execution", choices=("sync", "async"), default="sync")
    args = parser.parse_args()
    scenario = Scenario(args.order)
    try:
        owner = build(os.environ["REFERENCE_AGENT_MODEL"], scenario, configuration())
        result = (
            run_sync(owner, scenario, args.command)
            if args.execution == "sync"
            else asyncio.run(run_async(owner, scenario, args.command))
        )
    except (SDKError, ValueError, KeyError):
        print(
            json.dumps(
                {
                    "state": "failed",
                    "explanation": "Check configuration, readiness and the selected order.",
                    "receipts": scenario.receipts,
                }
            )
        )
        return 1
    except Exception:
        print(
            json.dumps(
                {
                    "state": "failed",
                    "explanation": "Model or execution failed; inspect console telemetry.",
                    "receipts": scenario.receipts,
                }
            )
        )
        return 1
    print(json.dumps(result))
    if args.command == "publish":
        return 0 if result["catalog_delivery"] == "acknowledged" else 1
    return (
        0
        if result["state"] == "receipt_recorded"
        and result["delivery"] == "acknowledged"
        else 1
    )
