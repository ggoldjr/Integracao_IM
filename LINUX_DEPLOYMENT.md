# Linux Deployment Guide

This guide deploys Integracao IM as a systemd service on a Linux server. The
examples target Debian or Ubuntu and use port `8181`.

## 1. Server requirements

Use a 64-bit Linux server with:

- Python 3.11 or newer (Python 3.12 or newer is recommended)
- Git
- Internet access to PyPI during installation, unless using an offline wheelhouse
- `libgomp`, required by the XGBoost runtime

Install the required OS packages:

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv libgomp1
python3 --version
```

## 2. Download the application

Create an application directory owned by your Linux user, then clone the GitHub
repository:

```bash
sudo mkdir -p /opt/integracao-im
sudo chown "$USER":"$USER" /opt/integracao-im
git clone https://github.com/ggoldjr/Integracao_IM.git /opt/integracao-im
cd /opt/integracao-im
```

Confirm that the model files are present:

```bash
ls -lh src/integracao_im/pkls/
```

The directory must contain:

```text
label_encoder.pkl
model_xgb_cls.pkl
model_xgb_reg.pkl
```

Only load model files produced by a trusted source. Python pickle files can
execute code while they are loaded.

## 3. Create the Python environment

Do not copy the Windows `.venv` directory to Linux. Create a new virtual
environment on the server:

```bash
cd /opt/integracao-im
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

For a deployment verification that includes the test dependency:

```bash
python -m pip install ".[dev]"
python -m unittest discover -s tests -v
```

## 4. Test it manually

Start the application in the foreground:

```bash
cd /opt/integracao-im
SERVICE_HOST=0.0.0.0 SERVICE_PORT=8181 .venv/bin/integracao-im
```

From another terminal on the server:

```bash
curl http://127.0.0.1:8181/health
```

Expected response:

```json
{"status":"ok"}
```

Stop the foreground process with `Ctrl+C` after this test.

## 5. Run it with systemd

Replace `LINUX_USER` below with the account that owns `/opt/integracao-im`.
Create `/etc/systemd/system/integracao-im.service`:

```ini
[Unit]
Description=Integracao IM REST service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=LINUX_USER
WorkingDirectory=/opt/integracao-im
Environment=SERVICE_HOST=0.0.0.0
Environment=SERVICE_PORT=8181
ExecStart=/opt/integracao-im/.venv/bin/integracao-im
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Load, enable, and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now integracao-im
sudo systemctl status integracao-im
```

View application logs:

```bash
sudo journalctl -u integracao-im -f
```

Restart or stop the service:

```bash
sudo systemctl restart integracao-im
sudo systemctl stop integracao-im
```

## 6. Network access

Find the server IP address:

```bash
hostname -I
```

From a permitted computer on the same network, use:

```text
http://SERVER_IP:8181/docs
http://SERVER_IP:8181/health
http://SERVER_IP:8181/api/v1/integrations/im_integration
```

If UFW is active, allow only the trusted network. Replace the example subnet
with the real client subnet:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8181 proto tcp
sudo ufw status
```

The API currently has no authentication or TLS. Do not expose port `8181`
directly to the public Internet. Use a reverse proxy with HTTPS and add
authentication before providing public access.

## 7. Verify the REST endpoint

Send a valid request from the Linux server:

```bash
curl --request POST \
  --url http://127.0.0.1:8181/api/v1/integrations/im_integration \
  --header 'Content-Type: application/json' \
  --data '{
    "registros": [
      {
        "rpm": 59.972562,
        "wind_speed": 24.520905,
        "current": 12.901479,
        "temperature": 57.242364,
        "vibration": 1.1922,
        "time_days": 1318240
      }
    ]
  }'
```

A successful response has HTTP status `200`, `valid: true`, and a
`mesg_resposta` object containing `situac` and `rul`.

## 8. Deploy an update

```bash
cd /opt/integracao-im
git pull --ff-only
source .venv/bin/activate
python -m pip install --upgrade .
python -m unittest discover -s tests -v
sudo systemctl restart integracao-im
sudo systemctl status integracao-im
```

## 9. Wheel deployment

The application can also be distributed as a wheel. Build it from the project
directory:

```bash
python -m pip install build
python -m build --wheel
```

The generated file is placed in `dist/` and includes the three model files.
Copy the wheel to the Linux server and install it in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install integracao_im-0.3.0-py3-none-any.whl
SERVICE_HOST=0.0.0.0 SERVICE_PORT=8181 integracao-im
```

The application wheel is platform-independent, but dependencies such as
Pandas, SciPy, scikit-learn, and XGBoost have platform-specific binaries. For
an offline deployment, create the dependency wheelhouse on a Linux system with
the same CPU architecture and compatible Linux version as the target server.

