import os
import sys
import urllib.request
import zipfile

TARGET_DIR = ".piper"
ZIP_URL = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
ZIP_FILE = "piper_windows.zip"

MODEL_ONNX_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
MODEL_JSON_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"

ONNX_FILE = os.path.join(TARGET_DIR, "en_US-lessac-medium.onnx")
JSON_FILE = os.path.join(TARGET_DIR, "en_US-lessac-medium.onnx.json")

def progress_hook(count, block_size, total_size):
    total_mb = total_size / (1024 * 1024)
    downloaded_mb = (count * block_size) / (1024 * 1024)
    percent = min(100, int(count * block_size * 100 / total_size))
    sys.stdout.write(f"\rDownloading: {percent}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)")
    sys.stdout.flush()

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # 1. Download Piper engine
    exe_path = os.path.join(TARGET_DIR, "piper", "piper.exe")
    if not os.path.exists(exe_path):
        print(f"Downloading Piper engine from {ZIP_URL}...")
        try:
            urllib.request.urlretrieve(ZIP_URL, ZIP_FILE, reporthook=progress_hook)
            print("\nExtracting Piper engine...")
            with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
                zip_ref.extractall(TARGET_DIR)
        except Exception as e:
            print(f"\nError downloading/extracting Piper: {e}")
            sys.exit(1)
        finally:
            if os.path.exists(ZIP_FILE):
                try:
                    os.remove(ZIP_FILE)
                except Exception:
                    pass
    else:
        print("Piper engine already exists. Skipping download.")

    # 2. Download ONNX model
    if not os.path.exists(ONNX_FILE):
        print(f"Downloading ONNX voice model from {MODEL_ONNX_URL}...")
        try:
            urllib.request.urlretrieve(MODEL_ONNX_URL, ONNX_FILE, reporthook=progress_hook)
            print()
        except Exception as e:
            print(f"\nError downloading ONNX model: {e}")
            sys.exit(1)
    else:
        print("ONNX voice model already exists. Skipping download.")

    # 3. Download JSON model config
    if not os.path.exists(JSON_FILE):
        print(f"Downloading JSON voice model config from {MODEL_JSON_URL}...")
        try:
            urllib.request.urlretrieve(MODEL_JSON_URL, JSON_FILE, reporthook=progress_hook)
            print()
        except Exception as e:
            print(f"\nError downloading JSON config: {e}")
            sys.exit(1)
    else:
        print("JSON voice model config already exists. Skipping download.")

    print("Piper TTS setup completed successfully!")

if __name__ == "__main__":
    main()
