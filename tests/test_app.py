import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx

from integracao_im.app import SensorReading, calculate_temperature_plus_rpm, create_app


class ApiTests(unittest.IsolatedAsyncioTestCase):
    sample_payload = {
        "rpm": 61.0928882027,
        "wind_speed": 14.8490478216,
        "current": 12.2994975525,
        "temperature": 53.8296539588,
        "vibration": 1.0957122047,
        "time_days": 0,
    }

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
        self.assertEqual(response.json()["data"], self.sample_payload)
        self.assertAlmostEqual(response.json()["temperature_plus_rpm"], 114.9225421615)

    def test_temperature_plus_rpm_calculation(self) -> None:
        reading = SensorReading.model_validate(self.sample_payload)

        result = calculate_temperature_plus_rpm(reading)

        self.assertAlmostEqual(result, 114.9225421615)

    async def test_missing_attribute_is_invalid(self) -> None:
        response = await self.request(
            "POST",
            "/api/v1/integrations/im_integration",
            json={"rpm": 61.09},
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["valid"])
        self.assertEqual(response.json()["message"], "JSON attributes are invalid")

    async def test_unknown_attribute_is_invalid(self) -> None:
        payload = {**self.sample_payload, "unknown": 123}

        response = await self.request(
            "POST",
            "/api/v1/integrations/im_integration",
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["valid"])

    async def test_wrong_attribute_type_is_invalid(self) -> None:
        payload = {**self.sample_payload, "rpm": "not-a-number"}

        response = await self.request(
            "POST",
            "/api/v1/integrations/im_integration",
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.json()["valid"])


if __name__ == "__main__":
    unittest.main()
