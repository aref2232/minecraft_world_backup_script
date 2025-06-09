import argparse
import mcrcon
import subprocess
import os
import logging
import time
import sys
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def setup_logging(logfile):
    logging.basicConfig(filename=logfile, level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

def send_ntfy_alert(topic, title, message, priority="default"):
    if not topic:
        return
    url = f"https://ntfy.sh/{topic}"
    data = message
    headers = {
        "Title": title,
        "Priority": priority
    }
    try:
        resp = requests.post(url, data=data.encode("utf-8"), headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logging.warning(f"Failed to send ntfy alert: {e}")

def send_telegram_alert(bot_token, chat_id, message):
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logging.warning(f"Failed to send Telegram alert: {e}")

def send_rcon_commands(ip, port, password, commands):
    try:
        with mcrcon.MCRcon(ip, password, port) as rcon:
            for cmd in commands:
                rcon.command(cmd)
    except Exception as e:
        logging.error(f"RCON error: {e}")
        raise

def java_pre_backup(world_path, ip, port, password):
    send_rcon_commands(ip, port, password, ["save-all", "save-off"])
    time.sleep(2)
    logging.info("Java server saved and autosave off for backup.")

def java_post_backup(ip, port, password):
    try:
        send_rcon_commands(ip, port, password, ["save-on"])
        logging.info("Java server autosave re-enabled after backup.")
    except Exception as e:
        logging.error(f"Failed to re-enable autosave: {e}")

def bedrock_pre_backup(screen_name):
    try:
        subprocess.run(['screen', '-S', screen_name, '-p', '0', '-X', 'stuff', 'save hold\n'], check=True)
        logging.info("Sent 'save hold' to Bedrock server.")
        time.sleep(5)
    except Exception as e:
        logging.warning(f"Could not send 'save hold': {e}")

def bedrock_post_backup(screen_name):
    try:
        subprocess.run(['screen', '-S', screen_name, '-p', '0', '-X', 'stuff', 'save resume\n'], check=True)
        logging.info("Sent 'save resume' to Bedrock server.")
    except Exception as e:
        logging.warning(f"Could not send 'save resume': {e}")

def run_restic_backup(restic_repo, world_path, password, retention_policy=None, tags=None, logfile=None, restic_args=None):
    env = os.environ.copy()
    env['RESTIC_PASSWORD'] = password
    cmd = [
        "restic", "-r", restic_repo, "backup", world_path
    ]
    if restic_args:
        cmd += restic_args.split()
    if tags:
        for tag in tags:
            cmd.extend(["--tag", tag])
    with open(logfile, 'a') if logfile else open(os.devnull, 'w') as lf:
        subprocess.run(cmd, env=env, check=True, stdout=lf, stderr=lf)
    logging.info(f"Restic backup complete for {world_path}")
    # Apply retention policy (prune snapshots)
    if retention_policy:
        prune_cmd = [
            "restic", "-r", restic_repo, "forget"
        ] + retention_policy.split() + ["--prune"]
        with open(logfile, 'a') if logfile else open(os.devnull, 'w') as lf:
            subprocess.run(prune_cmd, env=env, check=True, stdout=lf, stderr=lf)
        logging.info(f"Applied retention policy: {retention_policy}")

def start_server(start_script, screen_name):
    try:
        subprocess.run(["screen", "-dmS", screen_name, "bash", "-c", start_script], check=True)
        logging.info(f"Server started in screen session '{screen_name}'.")
    except Exception as e:
        logging.error(f"Failed to start server: {e}")

def backup_single_world(args, config, global_opts):
    server_name = config['server_name']
    logfile = global_opts['logfile'].replace("{server_name}", server_name)
    setup_logging(logfile)
    edition = config.get('edition')
    world_path = config.get('world_path')
    start_script = config.get('start_script')
    screen_name = config.get('screen_name', server_name)
    restic_root = global_opts['restic_root']
    restic_password = global_opts['restic_password']
    retention_policy = global_opts['retention_policy']
    tags = global_opts.get('tags', [])
    restic_args = global_opts.get('restic_args')
    ntfy_topic = global_opts.get('ntfy_topic')
    telegram_token = global_opts.get('telegram_token')
    telegram_chat_id = global_opts.get('telegram_chat_id')

    restic_repo = os.path.join(restic_root, server_name)
    # Initialize repo if needed
    if not os.path.exists(restic_repo):
        env = os.environ.copy()
        env['RESTIC_PASSWORD'] = restic_password
        subprocess.run(["restic", "-r", restic_repo, "init"], env=env, check=True)
        logging.info(f"Initialized restic repo at {restic_repo}")

    try:
        if edition == "java":
            rcon_ip = config.get("rcon_ip", "localhost")
            rcon_port = config.get("rcon_port", 25575)
            rcon_password = config.get("rcon_password")
            if not rcon_password:
                raise Exception("RCON password is required for Java edition.")
            java_pre_backup(world_path, rcon_ip, rcon_port, rcon_password)
            run_restic_backup(
                restic_repo, world_path, restic_password,
                retention_policy=retention_policy, tags=tags,
                logfile=logfile, restic_args=restic_args
            )
            java_post_backup(rcon_ip, rcon_port, rcon_password)
            start_server(start_script, screen_name)
        elif edition == "bedrock":
            bedrock_pre_backup(screen_name)
            run_restic_backup(
                restic_repo, world_path, restic_password,
                retention_policy=retention_policy, tags=tags,
                logfile=logfile, restic_args=restic_args
            )
            bedrock_post_backup(screen_name)
            start_server(start_script, screen_name)
        else:
            raise Exception(f"Unknown edition: {edition}")
        msg = f"Backup completed for {server_name} ({world_path}) in {restic_repo}"
        print(msg)
        send_ntfy_alert(ntfy_topic, f"{server_name} Backup Success", msg)
        send_telegram_alert(telegram_token, telegram_chat_id, f"✅ {msg}")
        return True, msg
    except Exception as e:
        logging.error(f"Backup failed: {e}")
        msg = f"Backup FAILED for {server_name}: {e}"
        print(msg)
        send_ntfy_alert(ntfy_topic, f"{server_name} Backup Failure", msg, priority="high")
        send_telegram_alert(telegram_token, telegram_chat_id, f"❌ {msg}")
        return False, msg

def main():
    parser = argparse.ArgumentParser(description="Minecraft World Backup Script with Restic (parallel capable)")
    parser.add_argument("--edition", choices=["java", "bedrock"], help="Edition of Minecraft server")
    parser.add_argument("--server-name", help="Unique server name for backup repo")
    parser.add_argument("--world-path", help="Path to world/server files")
    parser.add_argument("--restic-root", required=True, help="Root directory for restic repositories (each world/server gets its own subdir)")
    parser.add_argument("--restic-password", required=True, help="Password for restic repo")
    parser.add_argument("--start-script", help="Script or command to start the server")
    parser.add_argument("--logfile", default="logfile_{server_name}.txt", help="Log file path (can use {server_name})")
    parser.add_argument("--screen-name", help="Screen session name")
    parser.add_argument("--retention-policy", default="--keep-daily 14 --keep-weekly 8 --keep-monthly 12", help="Restic retention policy")
    parser.add_argument("--tags", nargs='*', default=[], help="Tags to add to restic snapshot")
    parser.add_argument("--restic-args", default=None, help="Additional arguments to pass to restic backup (e.g. --exclude '*.log')")
    parser.add_argument("--ntfy-topic", help="ntfy.sh topic for backup alerts")
    parser.add_argument("--telegram-token", help="Telegram bot token for alerts")
    parser.add_argument("--telegram-chat-id", help="Telegram chat ID for alerts")
    parser.add_argument("--rcon-ip", default="localhost", help="RCON IP address (Java only)")
    parser.add_argument("--rcon-port", type=int, default=25575, help="RCON port (Java only)")
    parser.add_argument("--rcon-password", default="", help="RCON password (Java only)")
    parser.add_argument("--parallel-config", help="JSON file listing worlds/servers to backup in parallel")
    parser.add_argument("--max-parallel", type=int, default=4, help="Maximum parallel backups")
    args = parser.parse_args()

    global_opts = {
        "restic_root": args.restic_root,
        "restic_password": args.restic_password,
        "retention_policy": args.retention_policy,
        "tags": args.tags,
        "logfile": args.logfile,
        "ntfy_topic": args.ntfy_topic,
        "telegram_token": args.telegram_token,
        "telegram_chat_id": args.telegram_chat_id,
        "restic_args": args.restic_args,
    }

    if args.parallel_config:
        # Parallel mode: run backups for each world/server in config file
        with open(args.parallel_config, 'r') as jf:
            configs = json.load(jf)
        results = []
        with ThreadPoolExecutor(max_workers=args.max_parallel) as executor:
            future_to_server = {
                executor.submit(backup_single_world, args, config, global_opts): config['server_name']
                for config in configs
            }
            for future in as_completed(future_to_server):
                server = future_to_server[future]
                try:
                    ok, msg = future.result()
                except Exception as exc:
                    ok = False
                    msg = f"Backup crashed for {server}: {exc}"
                    print(msg)
                results.append((server, ok, msg))
        for server, ok, msg in results:
            print(f"{server}: {'SUCCESS' if ok else 'FAILED'} - {msg}")
        sys.exit(0 if all(ok for _, ok, _ in results) else 1)

    # Single world/server mode
    config = {
        "edition": args.edition,
        "server_name": args.server_name,
        "world_path": args.world_path,
        "start_script": args.start_script,
        "screen_name": args.screen_name or args.server_name,
        "rcon_ip": args.rcon_ip,
        "rcon_port": args.rcon_port,
        "rcon_password": args.rcon_password,
    }
    ok, msg = backup_single_world(args, config, global_opts)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
