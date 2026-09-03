from pydantic import BaseModel


class OpenExternalRequest(BaseModel):
    url: str
