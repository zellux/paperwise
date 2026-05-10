from pydantic import BaseModel, Field


class CollectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=2000)


class CollectionDocumentsRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    tag: list[str] = Field(default_factory=list)
    document_type: list[str] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    top_k_chunks: int = Field(default=18, ge=3, le=60)
    max_documents: int = Field(default=12, ge=1, le=50)
    tag: list[str] = Field(default_factory=list)
    document_type: list[str] = Field(default_factory=list)
    debug: bool = False
