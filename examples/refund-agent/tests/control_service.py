"""External control-service double; SDK and native graphs execute unchanged."""

from uuid import uuid4

from openeight import (
    AgentReadiness,
    APIError,
    DecisionResult,
    FieldSelector,
    PolicyInputRequirement,
    RegistrationResult,
    Tool,
    ToolReadiness,
    ToolVersion,
)


class ControlService:
    instances = []
    outcome = "allow"
    pending_check = None

    def __init__(self, *args, **kwargs):
        self.instances.append(self)
        self.publications = {}
        self.requests = []
        self.writes = []
        self.polls = 0
        self.closed = False

    def register_tools(self, facts, **kwargs):
        results = []
        for index, fact in enumerate(facts):
            read = "amount_minor" not in fact.input_schema.get("properties", {})
            tool_id, version_id = str(uuid4()), str(uuid4())
            tool = Tool(
                tool_id,
                fact.name,
                fact.description,
                "read" if read else "write",
                not read,
                None,
                None,
                "2026-11-09T00:00:00Z",
            )
            version = ToolVersion(
                version_id,
                tool_id,
                "test:1",
                "sha256:" + "0" * 64,
                fact.input_schema,
                None if read else "sha256:" + "1" * 64,
                "2026-11-09T00:00:00Z",
            )
            item = RegistrationResult(
                index,
                "registered",
                "",
                tool,
                version,
                ToolReadiness(
                    index,
                    fact.name,
                    tool_id,
                    version_id,
                    "registered",
                    not read,
                    True,
                    True,
                    "read_only" if read else "ready",
                ),
            )
            self.publications[version_id] = item
            results.append(item)
        return tuple(results)

    def get_tool_readiness(self, ids, **kwargs):
        rows = []
        for identity in ids:
            item = self.publications[identity]
            write = item.tool.capability == "write"
            requirements = (
                (
                    PolicyInputRequirement(
                        str(uuid4()),
                        str(uuid4()),
                        str(uuid4()),
                        "b" * 64,
                        (FieldSelector("amount_minor"),),
                    ),
                )
                if write
                else ()
            )
            rows.append(
                ToolReadiness(
                    None,
                    item.tool.name,
                    item.tool.id,
                    identity,
                    "registered",
                    True,
                    write,
                    True,
                    "ready",
                    "a" * 64 if write else None,
                    requirements,
                )
            )
        return AgentReadiness(tuple(rows), True, "registered", True, "ready")

    def decide(self, **request):
        self.requests.append(request)
        if self.outcome == "stale":
            raise APIError(409, "conflict", "AUTHORIZATION_STALE")
        if self.outcome == "revoked":
            raise APIError(401, "unauthorized", "credential_revoked")
        if self.outcome == "unavailable":
            raise APIError(503, "unavailable", "service_unavailable")
        verdict = "deny" if self.outcome == "deny" else "allow"
        if self.outcome in {"approved", "pending", "rejected", "expired"}:
            verdict = "approval_required"
        return DecisionResult(
            request["decision_id"],
            verdict,
            "",
            request["run_id"],
            len(self.requests) > 1,
        )

    def approval_state(self, *args, **kwargs):
        self.polls += 1
        if self.pending_check:
            self.pending_check()
        if self.outcome == "approved":
            return "pending" if self.polls == 1 else "approved"
        return self.outcome

    def write_telemetry(self, **body):
        self.writes.append(body)

    def close(self):
        self.closed = True
