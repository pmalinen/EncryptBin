# Systemd cleanup timer
Create `/etc/systemd/system/encryptbin-cleanup.service`:
```
[Unit]
Description=EncryptBin cleanup

[Service]
Type=oneshot
WorkingDirectory=/opt/encryptbin
EnvironmentFile=/opt/encryptbin/.env
ExecStart=/usr/bin/docker compose run --rm encryptbin-cleanup
```
Create `/etc/systemd/system/encryptbin-cleanup.timer`:
```
[Unit]
Description=Run EncryptBin cleanup daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```
Enable:
```
systemctl daemon-reload
systemctl enable --now encryptbin-cleanup.timer
```
