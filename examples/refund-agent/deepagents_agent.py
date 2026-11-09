"""Deep Agents entry point: python deepagents_agent.py publish or run ORD-1041."""

from deepagents.backends import StateBackend
from openeight.deepagents import create_deep_agent

from runner import main
from scenario import SYSTEM_PROMPT


def build(model, scenario, config):
    return create_deep_agent(
        model=model,
        tools=scenario.tools(),
        system_prompt=SYSTEM_PROMPT,
        backend=StateBackend(),
        include_general_purpose=False,
        openeight=config,
    )


if __name__ == "__main__":
    raise SystemExit(main(build))
