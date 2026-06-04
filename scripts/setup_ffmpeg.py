import os
import sys
import urllib.request
import zipfile
import shutil

TARGET_DIR = ".ffmpeg"
ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
ZIP_FILE = "ffmpeg.zip"

def progress_hook(count, block_size, total_size):
    total_mb = total_size / (1024 * 1024)
    downloaded_mb = (count * block_size) / (1024 * 1024)
    percent = min(100, int(count * block_size * 100 / total_size))
    sys.stdout.write(f"\rDownloading FFmpeg: {percent}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)")
    sys.stdout.flush()

def main():
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    ffmpeg_exe = os.path.join(TARGET_DIR, "ffmpeg.exe")
    ffprobe_exe = os.path.join(TARGET_DIR, "ffprobe.exe")
    
    if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
        print("FFmpeg and FFprobe already exist. Skipping download.")
        return

    print(f"Downloading FFmpeg from {ZIP_URL}...")
    try:
        # Request with a standard User-Agent headers to avoid HTTP 403 Forbidden issues
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
        urllib.request.install_opener(opener)
        
        urllib.request.urlretrieve(ZIP_URL, ZIP_FILE, reporthook=progress_hook)
        print("\nExtracting FFmpeg...")
        
        # Extract to a temporary directory inside TARGET_DIR
        extract_temp = os.path.join(TARGET_DIR, "temp_extract")
        os.makedirs(extract_temp, exist_ok=True)
        
        with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
            zip_ref.extractall(extract_temp)
            
        # Search recursively for ffmpeg.exe and ffprobe.exe
        found_ffmpeg = None
        found_ffprobe = None
        for root, dirs, files in os.walk(extract_temp):
            for file in files:
                if file.lower() == "ffmpeg.exe":
                    found_ffmpeg = os.path.join(root, file)
                elif file.lower() == "ffprobe.exe":
                    found_ffprobe = os.path.join(root, file)
                    
        if found_ffmpeg and found_ffprobe:
            # Overwrite if exists, but we checked earlier
            shutil.move(found_ffmpeg, ffmpeg_exe)
            shutil.move(found_ffprobe, ffprobe_exe)
            print("Successfully moved ffmpeg.exe and ffprobe.exe to .ffmpeg/")
        else:
            print("\nError: could not find ffmpeg.exe and ffprobe.exe inside the downloaded archive.")
            sys.exit(1)
            
        # Clean up temporary extract folder
        shutil.rmtree(extract_temp)
        print("Cleaned up extraction files.")
        
    except Exception as e:
        print(f"\nError setting up FFmpeg: {e}")
        sys.exit(1)
    finally:
        if os.path.exists(ZIP_FILE):
            try:
                os.remove(ZIP_FILE)
            except Exception:
                pass
                
    print("FFmpeg and FFprobe setup completed successfully!")

if __name__ == "__main__":
    main()
