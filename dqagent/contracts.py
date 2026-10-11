from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = str


class Kind(StrEnum):
    null = "null"
    duplicate = "duplicate"
    reference = "reference"
    row_count = "row_count"
    freshness = "freshness"
    numeric_range = "numeric_range"
    schema = "schema"
    reconciliation = "reconciliation"
    business_rule = "business_rule"
    anomaly = "anomaly"


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=120)
    table: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    schema_name: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    kind: Kind
    column: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    other_table: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    other_column: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    minimum: float | None = None
    maximum: float | None = None
    tolerance: float = Field(default=0, ge=0)
    severity: Literal["warning", "failure"] = "failure"
    expected_schema: dict[str, str] = Field(default_factory=dict, max_length=100)
    operator: Literal["le", "ge", "eq"] = "le"

    @model_validator(mode="after")
    def valid_parameters(self):
        if self.kind not in {Kind.row_count, Kind.schema, Kind.anomaly} and not self.column:
            raise ValueError("column required")
        if self.kind in {Kind.reference, Kind.reconciliation} and not (
            self.other_table and self.other_column
        ):
            raise ValueError("reference/reconciliation requires other table and column")
        if self.kind == Kind.business_rule and not self.other_column:
            raise ValueError("business rule requires other column")
        if self.kind in {Kind.freshness, Kind.anomaly} and (self.maximum is None or self.maximum < 0):
            raise ValueError("freshness/anomaly requires a nonnegative maximum")
        if (
            self.kind in {Kind.row_count, Kind.numeric_range}
            and self.minimum is None
            and self.maximum is None
        ):
            raise ValueError("at least one bound required")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum exceeds maximum")
        if self.kind == Kind.schema and not self.expected_schema:
            raise ValueError("schema baseline required")
        return self


class Result(BaseModel):
    check_id: str
    name: str
    table: str
    kind: Kind
    executed_at: str
    status: Literal["pass", "warning", "failure", "error"]
    measured: float | None
    expected: dict
    affected_records: int | None = None
    details: dict = Field(default_factory=dict)
    duration_ms: float


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1000)
    pipeline: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    run_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    use_ai: bool = False
