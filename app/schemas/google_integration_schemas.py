from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GoogleIntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    connected_at: datetime
    expires_at: datetime
    scopes: list[str]
