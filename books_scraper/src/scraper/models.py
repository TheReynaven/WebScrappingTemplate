from pydantic import BaseModel, Field, HttpUrl


class Book(BaseModel):
    """A catalogue book, validated field by field."""

    title       : str    = Field(min_length=1)
    price       : float  = Field(gt=0)
    rating      : int    = Field(ge=1, le=5)
    availability: str    = Field(min_length=1)
    url         : HttpUrl
