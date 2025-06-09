# Minecraft Server Backup & Restore with Restic

This system provides robust, efficient Minecraft world backups for **Java and Bedrock editions** using [restic](https://restic.net/).  
It supports deduplication, retention, cloud/network storage, backup alerts, and can perform parallel backups for multiple servers/worlds.

---

## Features

- **Safe, live backups** (auto-flushes world before backup).
- **Restic-based**: deduplication, snapshotting, efficient storage.
- **Manual and automated/parallel backups**: Use switches for manual runs or a config for parallel operation.
- **Retention policies**: Keep daily, weekly, monthly, or custom periods.
- **Cloud/remote support**: SMB, OneDrive, SFTP, rclone, etc.
- **Alerting**: Optional notifications via [ntfy.sh](https://ntfy.sh/) and/or Telegram.
- **Restore utility**: Restore to any snapshot.
- **Logging** and robust error handling.

---

## Directory Structure

```
/backup_root/
    server1/
        (restic repo files)
    server2/
        (restic repo files)
    ...
```

Each server/world has its own restic repository for safety/independence.

---

## Requirements

- [restic](https://restic.net/) (>=0.12 recommended)
- Python 3.7+
- [mcrcon](https://pypi.org/project/mcrcon/)
- [requests](https://pypi.org/project/requests/) (for alerting)
- For cloud/remote: [rclone](https://rclone.org/) or a mounted SMB/SFTP/cloud drive

Install dependencies:
```sh
pip install -r requirements.txt
```

---

## Setup Guide

See [RESTIC_SETUP.md](RESTIC_SETUP.md) for full setup instructions, including mounting cloud/NAS/SFTP destinations, initializing restic repos, and scheduling backups.

---

## Usage

### 1. **Backup Script**: `minecraft_backup_restic.py`

Supports both **single server/world** (manual, with all switches) and **parallel mode** for multiple worlds.

#### **Manual/Single World Example (All Options via Switches)**
```sh
python3 minecraft_backup_restic.py \
  --edition java \
  --server-name myserver \
  --world-path "/path/to/world" \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --start-script "./run.sh" \
  --rcon-ip "localhost" \
  --rcon-port 25575 \
  --rcon-password "YOUR_RCON_PASS" \
  --screen-name minecraft \
  --retention-policy "--keep-daily 14 --keep-weekly 8 --keep-monthly 12" \
  --tags manual-test \
  --ntfy-topic "mc-backups" \
  --telegram-token "123456:ABC-DEF" \
  --telegram-chat-id "987654321" \
  --logfile "/var/log/mc_backup_myserver.log" \
  --restic-args "--exclude '*.log' --exclude 'cache/'"
```
Every option can be set for manual runs and testing.

#### **Automated Parallel Backup Example**

Create a JSON config file, e.g. `backups.json`:
```json
[
  {
    "edition": "java",
    "server_name": "server1",
    "world_path": "/srv/server1/world",
    "start_script": "./server1_start.sh",
    "rcon_ip": "localhost",
    "rcon_port": 25575,
    "rcon_password": "password1",
    "screen_name": "server1"
  },
  {
    "edition": "bedrock",
    "server_name": "bedrock1",
    "world_path": "/srv/bedrock1/worlds",
    "start_script": "./bedrock1_start.sh",
    "screen_name": "bedrock1"
  }
]
```

Then run:
```sh
python3 minecraft_backup_restic.py \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --retention-policy "--keep-daily 7 --keep-weekly 8 --keep-monthly 12" \
  --parallel-config backups.json \
  --ntfy-topic "mc-backups"
```

---

### 2. **Restore Script**: `restore_minecraft_restic.py`

List snapshots:
```sh
python3 restore_minecraft_restic.py \
  --server-name myserver \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --list-snapshots
```

Restore latest:
```sh
python3 restore_minecraft_restic.py \
  --server-name myserver \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --restore-path "/path/to/restore/world"
```

Restore a specific snapshot:
```sh
python3 restore_minecraft_restic.py \
  --server-name myserver \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --restore-path "/path/to/restore/world" \
  --snapshot-id "d8e7633c"
```

---

## Backup Alerts

- **ntfy.sh**: Add `--ntfy-topic "mytopic"` (see [https://ntfy.sh/](https://ntfy.sh/)).
- **Telegram**: Add both `--telegram-token` and `--telegram-chat-id`.

Alerts are sent on backup success and failure.

---

## Parallel Backups

- Use `--parallel-config <json_file>` to run multiple backups at once.
- Each backup runs in its own process for speed.
- Logs for each backup are tagged and separated.

---

## FAQ

**Q: How do I keep my restic repositories from interfering?**  
A: Each server/world must have its own restic repo (separate folder or rclone remote).

**Q: How do I restore a specific day/month?**  
A: Use `--list-snapshots` to find the ID or timestamp, then restore with `--snapshot-id`.

**Q: Can I run this on Windows?**  
A: Yes, if you have Python, restic, and dependencies installed.

**Q: How do I exclude files from backup?**  
A: Add `--restic-args "--exclude '*.log' --exclude 'cache/'"` to the script.

---

## Troubleshooting

- Check the log files for errors.
- Test restoring a backup before relying on this system.
- If restic errors about password/repo, double-check your settings.
- For network/cloud backups, ensure you have network access and correct rclone/mount setup.

---

## License

MIT License

---

## See also

- [RESTIC_SETUP.md](RESTIC_SETUP.md) for step-by-step setup, cloud/NAS backup, and advanced usage.
