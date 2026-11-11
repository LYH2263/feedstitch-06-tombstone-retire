from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    mode: str = Field(default="incremental", pattern="^(incremental|full)$")


class LookbackUpdate(BaseModel):
    lookback_seconds: int = Field(ge=0, le=86400 * 30)


class SettingUpdate(BaseModel):
    value: str
