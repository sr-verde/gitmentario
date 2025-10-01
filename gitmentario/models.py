from typing import Annotated

from pydantic import BaseModel, Field, constr, field_validator


class Comment(BaseModel):
    """User comment with validation.

    This model represents a user comment with validations on fields
    to ensure well-formed input such as length restrictions, ASCII-only
    constraints, and alphabetic checks.
    """

    author: Annotated[
        str, constr(strip_whitespace=True, min_length=1, max_length=64)
    ] = Field(
        ...,
        description="Name of the commenter",
    )
    message: Annotated[
        str, constr(strip_whitespace=True, min_length=1, max_length=1024)
    ] = Field(
        ...,
        description="Comment message content",
    )
    archetype: Annotated[
        str, constr(strip_whitespace=True, min_length=1, max_length=32)
    ] = Field(
        default="default",
        description="User archetype, classifying user category or role",
    )
    page_id: Annotated[
        str, constr(strip_whitespace=True, min_length=1, max_length=1024)
    ] = Field(
        ...,
        description="Identifier of the page related to the comment",
    )

    @field_validator("archetype", mode="after")
    @classmethod
    def archetype_must_be_alpha(cls, value: str) -> str:
        """Validate that the archetype contains only alphabetic characters."""
        if not value.isalpha():
            raise ValueError("Archetype must contain only alphabetic characters")
        return value

    @field_validator("page_id")
    @classmethod
    def page_id_must_be_ascii(cls, value: str) -> str:
        """Validate that the page_id contains only ASCII characters."""
        if not value.isascii():
            raise ValueError("Page ID must contain only ASCII characters")
        return value
