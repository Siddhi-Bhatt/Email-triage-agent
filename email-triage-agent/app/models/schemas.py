"""
Pydantic request/response models.

Keeping these separate from route handlers gives FastAPI's automatic
OpenAPI docs (/docs) accurate schemas, and gives us a single source of
truth for validation rules (e.g. minimum email length, category enum).
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class EmailCategory(str, Enum):
    """The fixed set of categories the classifier can return."""

    WORK = "Work"
    PERSONAL = "Personal"
    FINANCE = "Finance"
    SPAM = "Spam"


class ClassifyEmailRequest(BaseModel):
    email_content: str = Field(
        ...,
        min_length=1,
        max_length=20_000,
        description="The raw text content of the email to classify.",
        examples=[
            "Hi team, attaching the Q3 budget review for tomorrow's "
            "10am sync. Please review before the meeting."
        ],
    )

    @field_validator("email_content")
    @classmethod
    def not_just_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("email_content cannot be empty or only whitespace")
        return v


class ClassifyEmailResponse(BaseModel):
    category: EmailCategory = Field(..., description="The predicted email category.")
    confidence_note: str = Field(
        default="Predicted by LLM-based classification.",
        description="Short note on how the prediction was produced.",
    )


class RewriteEmailRequest(BaseModel):
    email_content: str = Field(
        ...,
        min_length=1,
        max_length=20_000,
        description="The raw text content of the email to rewrite.",
        examples=["hey can u send me the report asap, kinda need it now"],
    )
    tone: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description='Desired tone for the rewrite, e.g. "professional", "friendly".',
        examples=["professional"],
    )

    @field_validator("email_content", "tone")
    @classmethod
    def not_just_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("field cannot be empty or only whitespace")
        return v


class RewriteEmailResponse(BaseModel):
    original_email: str = Field(..., description="The original email content, unchanged.")
    tone: str = Field(..., description="The tone that was applied.")
    rewritten_email: str = Field(..., description="The rewritten email content.")


class HealthResponse(BaseModel):
    status: str
    llm_provider: str


class ErrorResponse(BaseModel):
    detail: str