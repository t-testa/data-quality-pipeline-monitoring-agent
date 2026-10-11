import json

from pydantic import BaseModel, ConfigDict, Field


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipeline: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,80}$")
    run_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    table: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    limit: int = Field(default=30, ge=1, le=100)


TOOLS = {
    "list_pipelines": "Registered local pipelines and last successful execution",
    "get_pipeline_status": "Latest run for a named pipeline",
    "get_pipeline_run": "One persisted run by ID",
    "get_recent_failures": "Failed runs in a bounded recent run window",
    "list_data_quality_checks": "Recorded check definitions from one run",
    "get_data_quality_results": "Persisted quality evidence for one run",
    "get_table_quality_summary": "Checks for a table within one run",
    "get_data_freshness": "Freshness evidence for one run",
    "get_incident_details": "Run and related validation evidence",
}


class EvidenceTools:
    def __init__(self, store):
        self.store = store

    def call(self, name: str, arguments: dict, authorized: bool):
        if not authorized:
            raise PermissionError("Monitoring read access required")
        args = ToolInput.model_validate(arguments)
        if name not in TOOLS:
            raise ValueError("Tool is not approved")
        if name == "list_pipelines":
            output = self.store.pipelines()[: args.limit]
        elif name == "get_recent_failures":
            output = [r for r in self.store.runs(args.pipeline, args.limit) if r["status"] == "failed"]
        elif name == "get_pipeline_status":
            if args.pipeline is None:
                raise ValueError("pipeline required")
            output = self.store.runs(args.pipeline, 1)
        else:
            if args.run_id is None:
                raise ValueError("run_id required")
            run = self.store.run(args.run_id)
            if not run or (args.pipeline and run["pipeline"] != args.pipeline):
                raise ValueError("Run not found in requested scope")
            results = self.store.results(args.run_id, args.limit)
            if name == "get_pipeline_run":
                output = run
            elif name == "get_incident_details":
                output = {"run": run, "results": results}
            elif name == "get_data_freshness":
                output = [r for r in results if r["kind"] == "freshness"]
            elif name == "get_table_quality_summary":
                if args.table is None:
                    raise ValueError("table required")
                output = [r for r in results if r["table"] == args.table]
            else:
                output = results
        if len(json.dumps(output).encode()) > 262144:
            raise ValueError("Result too large; request a smaller limit")
        return {"data": output, "limit": args.limit, "bounded": True}
