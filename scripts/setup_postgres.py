import os
import sys
import urllib.request
import zipfile
import subprocess
import shutil

PORT = 5432
VERSION = "16.3-1"
URL = f"https://get.enterprisedb.com/postgresql/postgresql-{VERSION}-windows-x64-binaries.zip"
ZIP_FILE = "postgresql_binaries.zip"
TARGET_DIR = ".postgres"
DATA_DIR = os.path.join(TARGET_DIR, "data")
BIN_DIR = os.path.join(TARGET_DIR, "bin")

def progress_hook(count, block_size, total_size):
    total_mb = total_size / (1024 * 1024)
    downloaded_mb = (count * block_size) / (1024 * 1024)
    percent = min(100, int(count * block_size * 100 / total_size))
    sys.stdout.write(f"\rDownloading PostgreSQL binaries: {percent}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)")
    sys.stdout.flush()

def download_and_extract():
    if os.path.exists(TARGET_DIR):
        print(f"PostgreSQL folder '{TARGET_DIR}' already exists. Skipping download.")
        return

    print(f"Downloading PostgreSQL from: {URL}")
    try:
        urllib.request.urlretrieve(URL, ZIP_FILE, reporthook=progress_hook)
        print("\nDownload complete. Extracting archive...")
    except Exception as e:
        print(f"\nError downloading binaries: {e}")
        sys.exit(1)
    
    temp_extract = ".postgres_temp"
    os.makedirs(temp_extract, exist_ok=True)
    try:
        with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
            zip_ref.extractall(temp_extract)
        print("Extraction complete. Moving binaries...")
        shutil.move(os.path.join(temp_extract, "pgsql"), TARGET_DIR)
    except Exception as e:
        print(f"Error extracting ZIP: {e}")
        sys.exit(1)
    finally:
        # Clean up temp files
        try:
            if os.path.exists(temp_extract):
                shutil.rmtree(temp_extract)
            if os.path.exists(ZIP_FILE):
                os.remove(ZIP_FILE)
        except Exception as e:
            print(f"Warning: Failed to clean up temp files: {e}")

def init_db():
    if os.path.exists(DATA_DIR):
        print(f"Data directory '{DATA_DIR}' already exists. Skipping initialization.")
        return

    initdb_path = os.path.join(BIN_DIR, "initdb.exe")
    print(f"Initializing database at: {DATA_DIR} ...")
    cmd = [
        initdb_path,
        "-D", DATA_DIR,
        "-U", "postgres",
        "--auth-local=trust",
        "--auth-host=trust"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"initdb failed:\nStdout: {result.stdout}\nStderr: {result.stderr}")
        sys.exit(1)
    print("Database initialized successfully.")

def create_helper_scripts():
    print("Creating start/stop helper scripts...")
    
    start_ps1 = """# PowerShell script to start local PostgreSQL
$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$PgCtl = Join-Path $PSScriptRoot ".postgres\\bin\\pg_ctl.exe"
$DataDir = Join-Path $PSScriptRoot ".postgres\\data"
$LogFile = Join-Path $PSScriptRoot ".postgres\\postgres.log"

Write-Host "Starting PostgreSQL on localhost..." -ForegroundColor Green
& $PgCtl -D $DataDir -l $LogFile start
"""
    
    stop_ps1 = """# PowerShell script to stop local PostgreSQL
$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
$PgCtl = Join-Path $PSScriptRoot ".postgres\\bin\\pg_ctl.exe"
$DataDir = Join-Path $PSScriptRoot ".postgres\\data"

Write-Host "Stopping PostgreSQL..." -ForegroundColor Yellow
& $PgCtl -D $DataDir stop
"""

    with open("start_postgres.ps1", "w", encoding="utf-8") as f:
        f.write(start_ps1)
        
    with open("stop_postgres.ps1", "w", encoding="utf-8") as f:
        f.write(stop_ps1)
        
    print("Helper scripts 'start_postgres.ps1' and 'stop_postgres.ps1' created in root folder.")

def start_db():
    print("Starting database server...")
    pg_ctl = os.path.join(BIN_DIR, "pg_ctl.exe")
    log_file = os.path.join(TARGET_DIR, "postgres.log")
    cmd = [pg_ctl, "-D", DATA_DIR, "-l", log_file, "start"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to start PostgreSQL:\nStdout: {result.stdout}\nStderr: {result.stderr}")
        sys.exit(1)
    print("Database server started.")

def create_yace_db():
    print("Creating 'yace' database...")
    createdb = os.path.join(BIN_DIR, "createdb.exe")
    cmd = [createdb, "-h", "localhost", "-p", str(PORT), "-U", "postgres", "yace"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"createdb failed:\nStdout: {result.stdout}\nStderr: {result.stderr}")
    else:
        print("Database 'yace' created or already exists.")

def main():
    download_and_extract()
    init_db()
    create_helper_scripts()
    start_db()
    # Wait a brief moment to ensure startup
    import time
    time.sleep(2)
    create_yace_db()
    print("PostgreSQL portable setup is complete and running!")

if __name__ == "__main__":
    main()
