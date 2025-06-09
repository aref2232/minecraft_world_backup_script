import argparse
import subprocess
import os
import logging

def setup_logging(logfile):
    logging.basicConfig(filename=logfile, level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

def run_restic_restore(restic_repo, password, target_path, snapshot_id=None, logfile=None):
    env = os.environ.copy()
    env['RESTIC_PASSWORD'] = password
    # Prepare the restore command
    cmd = [
        "restic", "-r", restic_repo, "restore"
    ]
    if snapshot_id:
        cmd.append(snapshot_id)
    else:
        cmd.append("latest")
    cmd.extend(["--target", target_path])
    with open(logfile, 'a') if logfile else open(os.devnull, 'w') as lf:
        subprocess.run(cmd, env=env, check=True, stdout=lf, stderr=lf)
    logging.info(f"Restic restore complete to {target_path}")

def run_restic_snapshots(restic_repo, password):
    env = os.environ.copy()
    env['RESTIC_PASSWORD'] = password
    subprocess.run(["restic", "-r", restic_repo, "snapshots"], env=env, check=True)

def main():
    parser = argparse.ArgumentParser(description="Minecraft World Restore Script with Restic")
    parser.add_argument("--server-name", required=True, help="Server name (restic repo subdir)")
    parser.add_argument("--restic-root", required=True, help="Root directory for restic repositories")
    parser.add_argument("--restic-password", required=True, help="Password for restic repo")
    parser.add_argument("--restore-path", required=True, help="Where to restore the world")
    parser.add_argument("--snapshot-id", default=None, help="Restic snapshot ID or latest")
    parser.add_argument("--logfile", default="restore_log.txt", help="Log file path")
    parser.add_argument("--list-snapshots", action="store_true", help="List snapshots instead of restoring")
    args = parser.parse_args()

    setup_logging(args.logfile)

    restic_repo = os.path.join(args.restic_root, args.server_name)

    try:
        if args.list_snapshots:
            run_restic_snapshots(restic_repo, args.restic_password)
        else:
            run_restic_restore(
                restic_repo, args.restic_password, args.restore_path,
                snapshot_id=args.snapshot_id, logfile=args.logfile
            )
        print(f"Restore operation finished for {restic_repo}")
    except Exception as e:
        logging.error(f"Restore script failed: {e}")
        print(f"Restore script failed: {e}")

if __name__ == "__main__":
    main()
