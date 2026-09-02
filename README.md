# Integracao IM REST Service

This service validates JSON containing IM sensor measurements. It does not call
an external application. Valid JSON returns HTTP 200 with `valid: true`; invalid
JSON returns HTTP 422 with `valid: false` and details about the incorrect fields.
After validation, the service calculates `temperature + rpm` and includes the
result in the successful response.

## Setup

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

```powershell
integracao-im
```

Open these URLs after the server starts:

- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Send JSON to the integration endpoint:

```powershell
$body = @{
  rpm = 61.0928882027
  wind_speed = 14.8490478216
  current = 12.2994975525
  temperature = 53.8296539588
  vibration = 1.0957122047
  time_days = 0
} | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/integrations/im_integration `
  -ContentType "application/json" `
  -Body $body
```

A successful response looks like:

```json
{
  "valid": true,
  "message": "JSON attributes are valid",
  "data": {
    "rpm": 61.0928882027,
    "wind_speed": 14.8490478216,
    "current": 12.2994975525,
    "temperature": 53.8296539588,
    "vibration": 1.0957122047,
    "time_days": 0.0
  },
  "temperature_plus_rpm": 114.9225421615
}
```

## Test

```powershell
python -m unittest discover -s tests -v
```

When VS Code opens this folder, install the recommended extensions and select
`.venv\Scripts\python.exe` if the interpreter is not selected automatically.
