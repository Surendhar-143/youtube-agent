from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Text, Float, Integer, DateTime, func, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.postgres import Base

class Topic(Base):
    """
    Topic candidate table representation.
    """
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    keywords: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    scripts: Mapped[List["Script"]] = relationship(
        "Script", back_populates="topic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Topic id={self.id} topic={self.topic!r} score={self.score} status={self.status!r}>"


class Script(Base):
    """
    Generated script document representation.
    """
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    script: Mapped[str] = mapped_column(Text, nullable=False)
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    topic: Mapped["Topic"] = relationship("Topic", back_populates="scripts")
    seo_metadata: Mapped[Optional["SEOMetadata"]] = relationship(
        "SEOMetadata", back_populates="script", cascade="all, delete-orphan", uselist=False
    )
    audio_asset: Mapped[Optional["AudioAsset"]] = relationship(
        "AudioAsset", back_populates="script", cascade="all, delete-orphan", uselist=False
    )
    scene_plans: Mapped[List["ScenePlan"]] = relationship(
        "ScenePlan", back_populates="script", cascade="all, delete-orphan"
    )
    subtitle_asset: Mapped[Optional["SubtitleAsset"]] = relationship(
        "SubtitleAsset", back_populates="script", cascade="all, delete-orphan", uselist=False
    )
    video_assets: Mapped[List["VideoAsset"]] = relationship(
        "VideoAsset", back_populates="script", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Script id={self.id} title={self.title!r} topic_id={self.topic_id}>"


class Video(Base):
    """
    Video record representation.
    """
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Video id={self.id} video_path={self.video_path!r} status={self.status!r}>"


class Analytics(Base):
    """
    Video channel performance metrics representation.
    """
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    watch_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Analytics id={self.id} views={self.views} ctr={self.ctr} watch_time={self.watch_time}>"


class SEOMetadata(Base):
    """
    SEO metadata for a generated script.
    """
    __tablename__ = "seo_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    script_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    hashtags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    script: Mapped["Script"] = relationship("Script", back_populates="seo_metadata")

    def __repr__(self) -> str:
        return f"<SEOMetadata id={self.id} script_id={self.script_id} title={self.title!r}>"


class AudioAsset(Base):
    """
    Generated narration audio asset representation.
    """
    __tablename__ = "audio_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    script_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    audio_path: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    voice_model: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    script: Mapped["Script"] = relationship("Script", back_populates="audio_asset")

    def __repr__(self) -> str:
        return f"<AudioAsset id={self.id} script_id={self.script_id} audio_path={self.audio_path!r} duration_seconds={self.duration_seconds}>"


class ScenePlan(Base):
    """
    Scene plan segment representation.
    """
    __tablename__ = "scene_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    script_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    narration_text: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_duration: Mapped[float] = mapped_column(Float, nullable=False)
    visual_type: Mapped[str] = mapped_column(String(50), nullable=False)
    keywords: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    script: Mapped["Script"] = relationship("Script", back_populates="scene_plans")
    visual_assets: Mapped[List["VisualAsset"]] = relationship(
        "VisualAsset", back_populates="scene_plan", cascade="all, delete-orphan"
    )
    asset_downloads: Mapped[List["AssetDownload"]] = relationship(
        "AssetDownload", back_populates="scene_plan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ScenePlan id={self.id} script_id={self.script_id} scene_number={self.scene_number} title={self.title!r}>"


class VisualAsset(Base):
    """
    Visual asset metadata representation.
    """
    __tablename__ = "visual_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scene_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scene_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    search_keywords: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PLANNED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    scene_plan: Mapped["ScenePlan"] = relationship("ScenePlan", back_populates="visual_assets")

    def __repr__(self) -> str:
        return f"<VisualAsset id={self.id} scene_id={self.scene_id} asset_type={self.asset_type!r} status={self.status!r}>"


class SubtitleAsset(Base):
    """
    Generated subtitle asset representation.
    """
    __tablename__ = "subtitle_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    script_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    subtitle_path: Mapped[str] = mapped_column(String(512), nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    script: Mapped["Script"] = relationship("Script", back_populates="subtitle_asset")

    def __repr__(self) -> str:
        return f"<SubtitleAsset id={self.id} script_id={self.script_id} subtitle_path={self.subtitle_path!r} line_count={self.line_count}>"


class VideoAsset(Base):
    """
    Rendered video asset representation.
    """
    __tablename__ = "video_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    script_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    audio_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("audio_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_path: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    resolution: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="RENDERING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    script: Mapped["Script"] = relationship("Script", back_populates="video_assets")
    audio_asset: Mapped["AudioAsset"] = relationship("AudioAsset")

    def __repr__(self) -> str:
        return f"<VideoAsset id={self.id} script_id={self.script_id} video_path={self.video_path!r} status={self.status!r}>"


class AIGeneration(Base):
    """
    AI model generation audit log representation.
    """
    __tablename__ = "ai_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AIGeneration id={self.id} agent_name={self.agent_name!r} model={self.model!r} success={self.success}>"


class AssetDownload(Base):
    """
    Metadata representation of a downloaded visual asset file.
    """
    __tablename__ = "asset_downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scene_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scene_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    visual_asset_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("visual_assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "IMAGE", "VIDEO"
    source: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "wikimedia", "europeana", "met_museum", "pexels"
    search_query: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    local_path: Mapped[str] = mapped_column(String(512), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="DOWNLOADED", nullable=False) # e.g. "DOWNLOADED", "FAILED"

    # Relationships
    scene_plan: Mapped["ScenePlan"] = relationship("ScenePlan", back_populates="asset_downloads")
    visual_asset: Mapped[Optional["VisualAsset"]] = relationship("VisualAsset")

    def __repr__(self) -> str:
        return f"<AssetDownload id={self.id} scene_id={self.scene_id} source={self.source!r} local_path={self.local_path!r}>"

