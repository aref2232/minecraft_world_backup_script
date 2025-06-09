# Restic Minecraft Backup & Restore Setup

This guide will help you set up automated and manual Minecraft (Java/Bedrock) server backups using [restic](https://restic.net/), with robust retention, parallel backups, and easy restore.

---

## 1. Install restic

### Ubuntu/Debian
```sh
sudo apt update
sudo apt install restic
```

### Fedora
```sh
sudo dnf install restic
```

### macOS (Homebrew)
```sh
brew install restic
```

For Windows, download from https://restic.net/.

---

## 2. Install Python dependencies

You need Python 3 and the following libraries:
```sh
pip install -r requirements.txt
```

---

## 3. Directory Structure

Each server gets its own restic repository (avoids interference):

```
/backup_root/
   server1/
      (restic repo files)
   server2/
      (restic repo files)
```

---

## 4. Initialize a restic repo for each server

Pick a strong password for each server's repo.

```sh
export RESTIC_PASSWORD="your_strong_password"
restic -r /backup_root/server1 init
restic -r /backup_root/server2 init
```

You can store this password in a file and use `source /path/to/envfile` in your scripts/crontab.

---

## 5. Backup to Cloud/Network (optional)

You can back up to SMB/CIFS, SFTP, or cloud storage via rclone.

#### Example: Onedrive via rclone
- Install and configure [rclone](https://rclone.org/onedrive/).
- Create a remote called `onedrive`.
- Use restic repo URL like:  
  ```
  restic -r rclone:onedrive:server1 init
  ```
- Update your backup scripts to use the rclone repo URL.

#### Example: SMB/NAS
- Mount your SMB share to `/mnt/nas` (see `mount.cifs` docs).
- Use `/mnt/nas/server1` as the restic repo path.

---

## 6. Automated and Manual Backups

### **Automated Parallel Backups (Multiple Servers/Worlds)**

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

Run backups in parallel:
```sh
python3 minecraft_backup_restic.py \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --retention-policy "--keep-daily 7 --keep-weekly 8 --keep-monthly 12" \
  --parallel-config backups.json \
  --ntfy-topic "mc-backups"
```

Schedule in crontab for hourly backups:
```
0 * * * * /usr/bin/python3 /path/to/minecraft_backup_restic.py \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --parallel-config /path/to/backups.json \
  --ntfy-topic "mc-backups"
```

---

### **Manual Backup (Single Server/World, All Options via Switches)**

Manually run a backup for testing or intervention with explicit options:
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
You can use any combination of the script's switches for manual backup and testing.

---

## 7. Restore

To list available snapshots:
```sh
python3 restore_minecraft_restic.py \
  --server-name myserver \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --list-snapshots
```

To restore a snapshot (replace `snapshot_id` with the one from listing):
```sh
python3 restore_minecraft_restic.py \
  --server-name myserver \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --restore-path "/path/to/restore/world" \
  --snapshot-id "d8e7633c"
```

To restore the latest:
```sh
python3 restore_minecraft_restic.py \
  --server-name myserver \
  --restic-root "/backup_root" \
  --restic-password "your_strong_password" \
  --restore-path "/path/to/restore/world"
```

---

## 8. Alerts and Notifications

- To use ntfy.sh add `--ntfy-topic "yourtopic"` to your backup command.
- To use Telegram, add `--telegram-token` and `--telegram-chat-id`.

---

## 9. Security and Best Practices

- Protect your restic passwords.
- For cloud/remote storage, encrypt traffic and use strong credentials.
- Test restoring from backups before relying on them.
- Use separate restic repos per world/server to avoid snapshot/collision issues.

---

## 10. Troubleshooting

- If a backup fails, check the log file for details.
- If you get "wrong password or no key found", double check your RESTIC_PASSWORD and repo path.
- Always ensure the world/server is stopped or properly flushed before backup/restore for data safety.
