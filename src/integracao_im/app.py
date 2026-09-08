import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import joblib
import pandas as pd
import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

SECONDS_PER_DAY = 86_400
MODEL_FEATURES = [
    "rpm",
    "wind_speed",
    "current",
    "temperature",
    "vibration",
    "time_days",
]
MODEL_DIR = Path(__file__).resolve().parent / "pkls"


class SensorReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rpm: float = Field(description="Rotational speed measurement")
    wind_speed: float = Field(description="Wind speed measurement")
    current: float = Field(description="Electrical current measurement")
    temperature: float = Field(description="Temperature measurement")
    vibration: float = Field(description="Vibration measurement")
    time_days: int = Field(
        ge=0,
        strict=True,
        description="Unix timestamp in seconds",
    )


class SensorBatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "registros": [
                        {
                            "rpm": 59.972562,
                            "wind_speed": 24.520905,
                            "current": 12.901479,
                            "temperature": 57.242364,
                            "vibration": 1.1922,
                            "time_days": 1318240,
                        },
                        {
                            "rpm": 62.481234,
                            "wind_speed": 22.310456,
                            "current": 13.452789,
                            "temperature": 58.112345,
                            "vibration": 1.2543,
                            "time_days": 1018240,
                        },
                        {
                            "rpm": 58.762341,
                            "wind_speed": 25.678912,
                            "current": 12.543210,
                            "temperature": 56.987654,
                            "vibration": 1.1789,
                            "time_days": 1218230,
                        },
                    ]
                }
            ]
        },
    )

    registros: list[SensorReading] = Field(min_length=1)


class PreparedSensorReading(BaseModel):
    rpm: float
    wind_speed: float
    current: float
    temperature: float
    vibration: float
    time_days: float


class PreparedSensorBatch(BaseModel):
    registros: list[PreparedSensorReading]


class RulClassificationMessage(BaseModel):
    resultado: Literal["sucesso"]
    situac: list[str]
    rul: list[float]


class ValidationResponse(BaseModel):
    valid: bool
    message: str
    data: PreparedSensorBatch
    mesg_resposta: RulClassificationMessage


@lru_cache(maxsize=1)
def carregar_modelos() -> tuple[Any, Any, Any]:
    model_xgb_reg = joblib.load(MODEL_DIR / "model_xgb_reg.pkl")
    model_xgb_cls = joblib.load(MODEL_DIR / "model_xgb_cls.pkl")
    label_encoder = joblib.load(MODEL_DIR / "label_encoder.pkl")
    return model_xgb_reg, model_xgb_cls, label_encoder


def rul_classificacao(payload: PreparedSensorBatch) -> RulClassificationMessage:
    frame = pd.DataFrame(
        [reading.model_dump() for reading in payload.registros],
        columns=MODEL_FEATURES,
    )
    model_xgb_reg, model_xgb_cls, label_encoder = carregar_modelos()

    resp_data_rul = [round(float(value), 2) for value in model_xgb_reg.predict(frame)]
    coded_classification = model_xgb_cls.predict(frame).astype(int)
    resp_form = [
        str(value) for value in label_encoder.inverse_transform(coded_classification)
    ]

    return RulClassificationMessage(
        resultado="sucesso",
        situac=resp_form,
        rul=resp_data_rul,
    )


def preparar_dados(payload: SensorBatch) -> PreparedSensorBatch:
    registros = [
        PreparedSensorReading(
            **reading.model_dump(exclude={"time_days"}),
            time_days=round(reading.time_days / SECONDS_PER_DAY, 6),
        )
        for reading in payload.registros
    ]
    return PreparedSensorBatch(registros=registros)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Integracao IM",
        description="Validates JSON containing IM sensor measurements.",
        version="0.3.0",
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
    async def validate_sensor_reading(payload: SensorBatch) -> ValidationResponse:
        prepared_payload = preparar_dados(payload)
        mesg_resposta = rul_classificacao(prepared_payload)

        return ValidationResponse(
            valid=True,
            message="JSON attributes are valid",
            data=prepared_payload,
            mesg_resposta=mesg_resposta,
        )

    return application


app = create_app()


def main() -> None:
    host = os.getenv("SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("SERVICE_PORT", "8181"))
    uvicorn.run("integracao_im.app:app", host=host, port=port, reload=False)
