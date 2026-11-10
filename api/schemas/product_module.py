"""Contracts of the product-module switches (dashboard shell and super-admin page)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EnabledProductModuleResponse(BaseModel):
    """A module the dashboard may show: installed and switched on."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str


class ProductModuleStatusResponse(BaseModel):
    """One line of the super-admin modules page."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    description: str
    is_installed: bool
    is_enabled: bool
    is_switchable: bool = Field(description="False for the websites module (the core) and for a module not installed")
    load_error: str | None = Field(default=None, description="Why an installed module could not load")
    updated_at: datetime | None = None


class ProductModuleSwitchRequest(BaseModel):
    """The new position of a module switch."""

    is_enabled: bool
