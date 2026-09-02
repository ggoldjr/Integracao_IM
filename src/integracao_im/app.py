import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


class SensorReading(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "rpm": 61.0928882027,
                    "wind_speed": 14.8490478216,
                    "current": 12.2994975525,
                    "temperature": 53.8296539588,
                    "vibration": 1.0957122047,
                    "time_days": 0,
                }
            ]
        },
    )

    rpm: float = Field(description="Rotational speed measurement")
    wind_speed: float = Field(description="Wind speed measurement")
    current: float = Field(description="Electrical current measurement")
    temperature: float = Field(description="Temperature measurement")
    vibration: float = Field(description="Vibration measurement")
    time_days: float = Field(ge=0, description="Elapsed time in days")


class ValidationResponse(BaseModel):
    valid: bool
    message: str
    data: SensorReading
    temperature_plus_rpm: float


def calculate_temperature_plus_rpm(reading: SensorReading) -> float:
    return reading.temperature + reading.rpm


def create_app() -> FastAPI:
    application = FastAPI(
        title="Integracao IM",
        description="Validates JSON containing IM sensor measurements.",
        version="0.2.0",
    )

    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "valid": False,
                "message": "JSON attributes are invalid",
                "errors": jsonable_encoder(exc.errors()),
            },
        )

    @application.get("/health", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post(
        "/api/v1/integrations/im_integration",
        response_model=ValidationResponse,
        tags=["integration"],
    )
    async def validate_sensor_reading(payload: SensorReading) -> ValidationResponse:
        temperature_plus_rpm = calculate_temperature_plus_rpm(payload)

        return ValidationResponse(
            valid=True,
            message="JSON attributes are valid",
            data=payload,
            temperature_plus_rpm=temperature_plus_rpm,
        )

    return application


app = create_app()


def main() -> None:
    host = os.getenv("SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("SERVICE_PORT", "8000"))
    uvicorn.run("integracao_im.app:app", host=host, port=port, reload=False)
