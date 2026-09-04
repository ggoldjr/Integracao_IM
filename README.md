# Integracao IM REST Service

This service validates a `registros` list containing IM sensor measurements. It
does not call an external application. Valid JSON returns HTTP 200 with
`valid: true`; invalid JSON returns HTTP 422 with `valid: false` and details
about the incorrect fields. After validation, the service calculates
`time_days / 86,400`, rounded to six decimal places, and updates `time_days` in
every record. It then runs the XGBoost classification and RUL regression models.

The incoming `time_days` must be an integer timestamp in seconds (Python
`int`, equivalent to Java `long`). The prepared response contains the converted
floating-point value in days.

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
  registros = @(
    @{
      rpm = 59.972562
      wind_speed = 24.520905
      current = 12.901479
      temperature = 57.242364
      vibration = 1.1922
      time_days = 1318240
    },
    @{
      rpm = 62.481234
      wind_speed = 22.310456
      current = 13.452789
      temperature = 58.112345
      vibration = 1.2543
      time_days = 1018240
    }
  )
} | ConvertTo-Json -Depth 4
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
    "registros": [
      {
        "rpm": 59.972562,
        "wind_speed": 24.520905,
        "current": 12.901479,
        "temperature": 57.242364,
        "vibration": 1.1922,
        "time_days": 15.257407
      },
      {
        "rpm": 62.481234,
        "wind_speed": 22.310456,
        "current": 13.452789,
        "temperature": 58.112345,
        "vibration": 1.2543,
        "time_days": 11.785185
      }
    ]
  },
  "mesg_resposta": {
    "resultado": "sucesso",
    "situac": ["SAUDÁVEL", "SAUDÁVEL"],
    "rul": [257.67, 264.06]
  }
}
```

The model artifacts are packaged from `src/integracao_im/pkls`:

- `model_xgb_reg.pkl`
- `model_xgb_cls.pkl`
- `label_encoder.pkl`

## Test

```powershell
python -m unittest discover -s tests -v
```

When VS Code opens this folder, install the recommended extensions and select
`.venv\Scripts\python.exe` if the interpreter is not selected automatically.
