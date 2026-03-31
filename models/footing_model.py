from pydantic import BaseModel, Field
import math

class FootingInput(BaseModel):
    number_of_footings: int = Field(gt=0)
    length: float = Field(gt=0)
    breadth: float = Field(gt=0)
    footing_depth: float = Field(gt=0)
    excavation_depth: float = Field(gt=0)
    pcc_thickness: float = Field(gt=0)
    steel_diameter: float = Field(gt=0)
    steel_spacing: float = Field(gt=0)
    excavation_rate: float = Field(ge=0)
    pcc_rate: float = Field(ge=0)
    rcc_rate: float = Field(ge=0)
    steel_rate: float = Field(ge=0)