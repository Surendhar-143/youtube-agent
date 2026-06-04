import os
import tempfile
import wave
import struct
import unittest
from services.audio_validator import AudioValidator, AudioValidationError

class TestAudioValidator(unittest.TestCase):
    def setUp(self):
        self.validator = AudioValidator(min_duration=10.0, max_duration=60.0)
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            if os.path.exists(f):
                try:
                    os.unlink(f)
                except Exception:
                    pass

    def _create_temp_file(self) -> str:
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        self.temp_files.append(path)
        return path

    def _write_dummy_wav(self, path: str, duration: float, sample_rate: int = 16000):
        with wave.open(path, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            n_frames = int(duration * sample_rate)
            data = struct.pack('<h', 0) * n_frames
            w.writeframes(data)

    def test_file_not_found(self):
        with self.assertRaises(AudioValidationError) as ctx:
            self.validator.validate("non_existent_file_xyz.wav")
        self.assertIn("does not exist", str(ctx.exception))

    def test_empty_file(self):
        path = self._create_temp_file()
        # file size is 0
        with self.assertRaises(AudioValidationError) as ctx:
            self.validator.validate(path)
        self.assertIn("empty", str(ctx.exception))

    def test_invalid_wav_header(self):
        path = self._create_temp_file()
        with open(path, 'wb') as f:
            f.write(b"THIS IS NOT A WAV FILE")
        
        with self.assertRaises(AudioValidationError) as ctx:
            self.validator.validate(path)
        self.assertIn("Invalid or corrupted WAV file", str(ctx.exception))

    def test_duration_too_short(self):
        path = self._create_temp_file()
        self._write_dummy_wav(path, duration=5.0)  # 5 seconds, min is 10.0
        
        with self.assertRaises(AudioValidationError) as ctx:
            self.validator.validate(path)
        self.assertIn("shorter than minimum limit", str(ctx.exception))

    def test_duration_too_long(self):
        path = self._create_temp_file()
        self._write_dummy_wav(path, duration=65.0)  # 65 seconds, max is 60.0
        
        with self.assertRaises(AudioValidationError) as ctx:
            self.validator.validate(path)
        self.assertIn("exceeds maximum limit", str(ctx.exception))

    def test_validation_success(self):
        path = self._create_temp_file()
        self._write_dummy_wav(path, duration=15.0)  # 15 seconds, within range [10, 60]
        
        result = self.validator.validate(path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["duration"], 15.0)
        self.assertGreater(result["size_bytes"], 0)

if __name__ == "__main__":
    unittest.main()
