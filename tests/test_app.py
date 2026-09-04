import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx

from integracao_im.app import (
    SensorBatch,
    create_app,
    preparar_dados,
    rul_classificacao,
)


class ApiTests(unittest.IsolatedAsyncioTestCase):
    sample_records = [
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
            "current": 12.54321,
            "temperature": 56.987654,
            "vibration": 1.1789,
            "time_days": 1218230,
        },
    ]
    sample_payload = {"registros": sample_records}

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    async def test_health(self) -> None:
        response = await self.request("GET", "/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    async def test_valid_sensor_reading(self) -> None:
        response = await self.request(
            "POST",
            "/api/v1/integrations/im_integration",
            json=self.sample_payload,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(response.json()["message"], "JSON attributes are valid")
        prepared_records = response.json()["data"]["registros"]
        self.assertEqual(
            [record["time_days"] for record in prepared_records],
            [15.257407, 11.785185, 14.099884],
        )
        self.assertEqual(
            response.json()["mesg_resposta"],
            {
                "resultado": "sucesso",
                "situac": ["SAUDÁVEL", "SAUDÁVEL", "SAUDÁVEL"],
                "rul": [257.67, 264.06, 260.89],
            },
        )

    def test_rul_classificacao(self) -> None:
        payload = SensorBatch.model_validate(self.sample_payload)
        prepared_payload = preparar_dados(payload)

        result = rul_classificacao(prepared_payload)

        self.assertEqual(result.resultado, "sucesso")
        self.assertEqual(result.situac, ["SAUDÁVEL", "SAUDÁVEL", "SAUDÁVEL"])
        self.assertEqual(result.rul, [257.67, 264.06, 260.89])

    def test_preparar_dados_converts_seconds_to_days(self) -> None:
        payload = SensorBatch.model_validate(
            {
                "registros": [
                    {**self.sample_records[0], "time_days": 18_000},
                    {**self.sample_records[1], "time_days": 21_600},
                ]
            }
        )

        result = preparar_dados(payload)

        self.assertEqual(
            [record.time_days for record in result.registros],
            [0.208333, 0.25],
        )

    async def test_missing_attribute_is_invalid(self) -> None:
        response = await self.request(
            "POST",
            "/api/v1/integrations/im_integration",
            json={"registros": [{"rpm": 61.09}]},
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["valid"])
        self.assertEqual(response.json()["message"], "JSON attributes are invalid")

    async def test_unknown_attribute_is_invalid(self) -> None:
        payload = {
            "registros": [{**self.sample_records[0], "unknown": 123}],
        }

        response = await self.request(
            "POST",
            "/api/v1/integrations/im_integration",
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["valid"])

    async def test_wrong_attribute_type_is_invalid(self) -> None:
        payload = {
            "registros": [{**self.sample_records[0], "rpm": "not-a-number"}],
        }

        response = await self.request(
            "POST",
            "/api/v1/integrations/im_integration",
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["valid"])

    async def test_decimal_timestamp_is_invalid(self) -> None:
        payload = {
            "registros": [{**self.sample_records[0], "time_days": 0.208333}],
        }

        response = await self.request(
            "POST",
            "/api/v1/integrations/im_integration",
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["valid"])

    async def test_empty_records_list_is_invalid(self) -> None:
        response = await self.request(
            "POST",
            "/api/v1/integrations/im_integration",
            json={"registros": []},
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["valid"])


if __name__ == "__main__":
    unittest.main()
