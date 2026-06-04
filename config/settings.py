from typing import Optional, Any
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application Settings configuration class.
    Loads settings from environment variables or a .env file.
    """
    # Core Application Settings
    APP_NAME: str = "YACE"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database Connections
    DATABASE_PROVIDER: str = "local"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/yace"
    TEST_DATABASE_URL: Optional[str] = "postgresql://postgres:postgres@localhost:5432/yace_test"
    SUPABASE_PROJECT_URL: Optional[str] = ""
    SUPABASE_ANON_KEY: Optional[str] = ""
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = ""

    # LLM Settings
    LLM_PROVIDER: str = "gemini"
    
    # Gemini Settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT: int = 120
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MAX_TOKENS: int = 4096

    # Ollama Settings
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"
    OLLAMA_POST_TIMEOUT: float = 120.0
    OLLAMA_GENERATE_TIMEOUT: float = 240.0
    OLLAMA_CHAT_TIMEOUT: float = 240.0
    OLLAMA_HEALTH_TIMEOUT: float = 5.0
    OLLAMA_TEMPERATURE: float = 0.7
    OLLAMA_TOP_P: float = 0.9
    OLLAMA_REPEAT_PENALTY: float = 1.1
    OLLAMA_MAX_TOKENS: int = 2048
    OLLAMA_NUM_CTX: int = 4096

    # Content Generation Bounds
    CONTENT_TOPICS_COUNT: int = 10
    CONTENT_MIN_TOPIC_SCORE: float = 70.0
    CONTENT_SCRIPT_MIN_WORDS: int = 1000
    CONTENT_SCRIPT_MAX_WORDS: int = 2500

    # SEO Bounds
    SEO_TITLE_MAX_LEN: int = 100
    SEO_DESCRIPTION_MAX_LEN: int = 5000
    SEO_MIN_TAGS_COUNT: int = 15
    SEO_MIN_HASHTAGS_COUNT: int = 10

    # Piper TTS Settings
    PIPER_EXECUTABLE: str = ".piper/piper/piper.exe"
    PIPER_MODEL: str = ".piper/en_US-lessac-medium.onnx"
    PIPER_SAMPLE_RATE: Optional[int] = 22050
    PIPER_SPEAKER_ID: Optional[int] = None

    # Audio Validation Bounds
    AUDIO_MIN_DURATION_SECONDS: float = 10.0
    AUDIO_MAX_DURATION_SECONDS: float = 1800.0

    # Visual Planning Configurations
    SPEECH_WORDS_PER_SECOND: float = 2.5
    SCENE_DURATION_TOLERANCE_BASE_SECONDS: float = 15.0
    SCENE_DURATION_TOLERANCE_FRACTION: float = 0.15
    SCENE_FALLBACK_KEYWORDS: str = "general visual"

    # FFmpeg & Media Processing Specs
    FFMPEG_PATH: str = ".ffmpeg/ffmpeg.exe"
    FFPROBE_PATH: str = ".ffmpeg/ffprobe.exe"
    FFMPEG_VIDEO_CODEC: str = "libx264"
    FFMPEG_AUDIO_CODEC: str = "aac"
    FFMPEG_FRAME_RATE: int = 30
    FFMPEG_PIXEL_FORMAT: str = "yuv420p"

    # Video Dimensions & Fallback
    VIDEO_RESOLUTION_WIDTH: int = 1920
    VIDEO_RESOLUTION_HEIGHT: int = 1080
    VIDEO_FALLBACK_COLOR: str = "black"

    # Subtitle Formatting & Styles
    SUBTITLE_CHARS_PER_LINE: int = 40
    SUBTITLE_MAX_LINES: int = 2
    SUBTITLE_FONT_NAME: str = "Arial"
    SUBTITLE_FONT_SIZE: int = 20
    SUBTITLE_PRIMARY_COLOR: str = "&H00FFFF"  # Yellow BGR/hex format for ASS
    SUBTITLE_ALIGNMENT: int = 2  # Bottom Center

    # Storage Paths
    PATH_SCRIPTS_DIR: str = "generated/scripts"
    PATH_AUDIO_DIR: str = "generated/audio"
    PATH_VIDEOS_DIR: str = "generated/videos"
    PATH_SUBTITLES_DIR: str = "generated/subtitles"
    PATH_ASSETS_DIR: str = "generated/assets"
    PATH_FONTS_DIR: str = "assets/fonts"
    PATH_MUSIC_DIR: str = "assets/music"
    PATH_TEMPLATES_DIR: str = "assets/templates"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_llm_and_db_settings(self) -> 'Settings':
        if self.LLM_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER is 'gemini'")
        if self.DATABASE_PROVIDER == "supabase" and not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required when DATABASE_PROVIDER is 'supabase'")
        return self

# Singleton instance for application-wide settings
settings = Settings()
