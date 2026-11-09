"""LangChain entry point: python langchain_agent.py publish or run ORD-1041."""

from openeight.langchain import create_agent

from runner import main
from scenario import SYSTEM_PROMPT


def build(model, scenario, config):
    return create_agent(
        model=model,
        tools=scenario.tools(),
        system_prompt=SYSTEM_PROMPT,
        openeight=config,
    )


if __name__ == "__main__":
    raise SystemExit(main(build))
