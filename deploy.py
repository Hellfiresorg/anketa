import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import paramiko
import stat
from pathlib import Path

LOCAL_BASE = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(LOCAL_BASE / 'backend' / '.env')

HOST = os.environ['DEPLOY_HOST']
PORT = int(os.environ.get('DEPLOY_PORT', '22'))
USER = os.environ.get('DEPLOY_USER', 'root')
PASSWORD = os.environ['DEPLOY_PASSWORD']
LOCAL_BACKEND = LOCAL_BASE / "backend"
REMOTE_BASE = "/opt/services/anketa"

SKIP_DIRS = {'.venv', '__pycache__', 'audio', 'tests', '.pytest_cache', '.omc'}
SKIP_FILES = {'test.db', 'dump.rdb', '.env', '.env.production', '.env.example'}

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=30)
    print(f"[OK] Connected to {HOST}")
    return client

def run_cmd(client, cmd, timeout=60):
    print(f"[CMD] {cmd[:100]}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    exit_code = stdout.channel.recv_exit_status()
    if out.strip():
        print(f"[OUT] {out.strip()}")
    if err.strip():
        print(f"[ERR] {err.strip()}")
    print(f"[EXIT] {exit_code}")
    return out, err, exit_code

def sftp_mkdir_p(sftp, remote_path):
    parts = remote_path.split('/')
    current = ''
    for part in parts:
        if not part:
            current = '/'
            continue
        current = current.rstrip('/') + '/' + part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)
            print(f"[MKDIR] {current}")

def upload_file(sftp, local_path, remote_path):
    sftp.put(str(local_path), remote_path)
    print(f"[UP] {local_path.name} -> {remote_path}")

def upload_dir(sftp, local_dir, remote_dir, skip_dirs=None, skip_files=None):
    skip_dirs = skip_dirs or set()
    skip_files = skip_files or set()
    sftp_mkdir_p(sftp, remote_dir)
    for item in local_dir.iterdir():
        if item.is_dir():
            if item.name in skip_dirs:
                print(f"[SKIP] {item.name}/")
                continue
            upload_dir(sftp, item, remote_dir + '/' + item.name, skip_dirs, skip_files)
        else:
            if item.name in skip_files:
                print(f"[SKIP] {item.name}")
                continue
            upload_file(sftp, item, remote_dir + '/' + item.name)

def main():
    client = connect()
    sftp = client.open_sftp()

    # Create base dir
    run_cmd(client, f"mkdir -p {REMOTE_BASE}/backend")

    # Step 1a: Upload docker-compose.prod.yml -> docker-compose.yml
    print("\n--- Uploading docker-compose.yml ---")
    sftp_mkdir_p(sftp, REMOTE_BASE)
    upload_file(sftp, LOCAL_BASE / "docker-compose.prod.yml", f"{REMOTE_BASE}/docker-compose.yml")

    # Step 1b: Upload specific backend items
    print("\n--- Uploading backend files ---")
    backend_remote = f"{REMOTE_BASE}/backend"
    sftp_mkdir_p(sftp, backend_remote)

    # Individual files
    for fname in ['Dockerfile', 'pyproject.toml', 'alembic.ini']:
        fpath = LOCAL_BACKEND / fname
        if fpath.exists():
            upload_file(sftp, fpath, f"{backend_remote}/{fname}")
        else:
            print(f"[WARN] {fname} not found locally")

    # Directories: alembic, app, scripts
    for dname in ['alembic', 'app', 'scripts']:
        dpath = LOCAL_BACKEND / dname
        if dpath.exists():
            print(f"\n--- Uploading {dname}/ ---")
            upload_dir(sftp, dpath, f"{backend_remote}/{dname}", skip_dirs={'__pycache__'})
        else:
            print(f"[WARN] {dname}/ not found locally")

    # Step 1c: Upload .env.production as .env
    print("\n--- Uploading .env.production -> .env ---")
    env_prod = LOCAL_BACKEND / ".env.production"
    if env_prod.exists():
        upload_file(sftp, env_prod, f"{backend_remote}/.env")
    else:
        print("[WARN] .env.production not found!")

    sftp.close()

    # Step 2: Create systemd unit
    print("\n--- Creating systemd unit ---")
    service_content = """[Unit]
Description=anketa
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/services/anketa
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
"""
    # Write via heredoc
    cmd = f"cat > /etc/systemd/system/anketa.service << 'HEREDOC'\n{service_content}HEREDOC"
    run_cmd(client, cmd)
    run_cmd(client, "cat /etc/systemd/system/anketa.service")

    # Step 3: Update Caddyfile
    print("\n--- Updating Caddyfile ---")
    out, err, _ = run_cmd(client, "cat /etc/caddy/Caddyfile")
    caddy_block = """
api.n8nonline1.space {
    reverse_proxy 127.0.0.1:8002
}
"""
    if "api.n8nonline1.space" in out:
        print("[INFO] Caddyfile already contains api.n8nonline1.space block, skipping append")
    else:
        append_cmd = f"cat >> /etc/caddy/Caddyfile << 'HEREDOC'\n{caddy_block}HEREDOC"
        run_cmd(client, append_cmd)
        print("[OK] Appended Caddy block")

    # Step 4: Run commands
    print("\n--- systemctl daemon-reload && enable anketa ---")
    run_cmd(client, "systemctl daemon-reload && systemctl enable anketa")

    print("\n--- docker compose up -d --build ---")
    out_build, err_build, rc = run_cmd(client, "cd /opt/services/anketa && docker compose up -d --build 2>&1", timeout=300)
    build_output = (out_build + err_build).strip().splitlines()
    print(f"[BUILD] exit code: {rc}")

    print("\n--- systemctl reload caddy ---")
    _, _, caddy_rc = run_cmd(client, "systemctl reload caddy")
    caddy_ok = caddy_rc == 0

    print("\n--- docker logs anketa-api --tail 30 ---")
    out_logs, err_logs, _ = run_cmd(client, "sleep 10 && docker logs anketa-api --tail 30 2>&1")

    print("\n--- docker ps | grep anketa ---")
    out_ps, _, _ = run_cmd(client, "docker ps | grep anketa")

    client.close()

    # Summary
    print("\n" + "="*60)
    print("DEPLOYMENT SUMMARY")
    print("="*60)
    print("\n[BUILD OUTPUT - last 20 lines]")
    for line in build_output[-20:]:
        print(line)

    print("\n[DOCKER LOGS - last 30 lines]")
    for line in (out_logs + err_logs).strip().splitlines():
        print(line)

    print("\n[DOCKER PS - anketa containers]")
    print(out_ps.strip() if out_ps.strip() else "(no anketa containers running)")

    print(f"\n[CADDY RELOAD] {'OK' if caddy_ok else 'FAILED (exit code ' + str(caddy_rc) + ')'}")

if __name__ == "__main__":
    main()
