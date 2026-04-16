from sqlmodel import SQLModel


class CreateBookSchema(SQLModel):
    title: str
    description: str


class UpdateBookSchema(SQLModel):
    title: str | None = None
    description: str | None = None
