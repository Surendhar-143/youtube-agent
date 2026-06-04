# YouTube Autonomous Content Engine (YACE)

## Project Overview

YACE (YouTube Autonomous Content Engine) is a fully automated YouTube content production platform designed for personal use.

The primary goal is to create, manage, publish, and optimize YouTube videos while maintaining near-zero operating costs until channel monetization is achieved.

The platform follows a Local-First architecture and minimizes dependence on paid APIs.

---

# Core Objective

Automate the complete YouTube content lifecycle:

1. Discover content ideas
2. Generate scripts
3. Generate voiceovers
4. Create videos
5. Generate thumbnails
6. Upload to YouTube
7. Monitor analytics
8. Improve future content

Target operational cost before monetization:

₹0 – ₹500/month

---

# Design Principles

## Principle 1: Local First

Always prefer:

* Local AI Models
* Local Databases
* Local Media Processing

Before using any paid API.

---

## Principle 2: Human Approval

Before monetization:

Every video must pass through a human approval checkpoint.

Publishing must not be fully autonomous.

Workflow:

Research
→ Script
→ Voice
→ Video
→ Approval
→ Publish

---

## Principle 3: Modular Agents

Every capability must exist as an independent agent.

Agents must communicate through structured data.

Agents must be replaceable without affecting the entire system.

---

# Technology Stack

## Backend

Python 3.12+

FastAPI

Uvicorn

Pydantic

SQLAlchemy

Alembic

---

## Database

PostgreSQL

Purpose:

* Store topics
* Store scripts
* Store videos
* Store analytics
* Store publishing history

---

## Local AI

### LLM

Provider:

Ollama

Default Model:

Qwen3 14B

Fallback:

Qwen3 8B

Responsibilities:

* Topic generation
* Research analysis
* Script writing
* SEO generation
* Thumbnail prompts

---

## Voice Generation

Provider:

Piper TTS

Responsibilities:

* Voice synthesis
* Narration generation

Output:

WAV

---

## Video Rendering

Provider:

FFmpeg

Responsibilities:

* Image sequencing
* Caption generation
* Audio synchronization
* Final video export

Output:

MP4

---

## Thumbnail Generation

Phase 1:

Template-based thumbnails

Phase 2:

Local FLUX image generation

Output:

PNG

---

## Upload System

YouTube Data API v3

Responsibilities:

* Upload videos
* Set thumbnails
* Schedule publication
* Manage playlists

---

# Supported Niches

Initial niche configuration:

* AI and Automation
* Technology
* Business
* Startups
* Programming
* ERPNext
* Frappe
* Software Development

Future support:

Dynamic niche creation.

---

# High-Level Architecture

YouTube CEO Agent

├── Research Agent

├── Script Agent

├── Voice Agent

├── Scene Agent

├── Thumbnail Agent

├── Video Agent

├── Publisher Agent

└── Analytics Agent

---

# Agent Responsibilities

## Research Agent

Purpose:

Find high-potential content topics.

Inputs:

* Niche
* Previous performance
* Keywords

Outputs:

TopicCandidate

Schema:

```json
{
"topic": "",
"score": 0,
"reasoning": "",
"keywords": []
}
```

---

## Script Agent

Purpose:

Generate YouTube scripts.

Input:

TopicCandidate

Output:

ScriptDocument

Schema:

```json
{
"title": "",
"hook": "",
"script": "",
"cta": ""
}
```

Target duration:

8-12 minutes

---

## Voice Agent

Purpose:

Convert script into narration.

Input:

ScriptDocument

Output:

AudioFile

Formats:

* wav
* mp3

---

## Scene Agent

Purpose:

Break script into visual scenes.

Input:

ScriptDocument

Output:

ScenePlan

Schema:

```json
{
"scene_number": 1,
"description": "",
"duration": 10
}
```

---

## Thumbnail Agent

Purpose:

Generate thumbnail concepts.

Input:

ScriptDocument

Output:

ThumbnailPlan

Schema:

```json
{
"headline": "",
"prompt": ""
}
```

---

## Video Agent

Purpose:

Build final YouTube video.

Inputs:

* Audio
* ScenePlan
* Images
* Captions

Output:

video.mp4

---

## Publisher Agent

Purpose:

Publish approved videos.

Input:

VideoPackage

Output:

YouTube URL

Capabilities:

* Upload
* Schedule
* Playlist Assignment

---

## Analytics Agent

Purpose:

Track channel performance.

Metrics:

* Views
* CTR
* Retention
* Watch Time
* Subscribers

Purpose:

Generate recommendations for future content.

---

# Database Design

## topics

Columns:

id

topic

score

keywords

status

created_at

---

## scripts

Columns:

id

topic_id

title

script

created_at

---

## videos

Columns:

id

script_id

video_path

thumbnail_path

youtube_url

status

published_at

---

## analytics

Columns:

id

video_id

views

ctr

watch_time

retention

subscribers

captured_at

---

# Folder Structure

```
youtube-agent/
agents/
research_agent.py
script_agent.py
voice_agent.py
scene_agent.py
thumbnail_agent.py
video_agent.py
publish_agent.py
analytics_agent.py
database/
models.py
postgres.py
migrations/
generated/
scripts/
audio/
images/
videos/
thumbnails/
assets/
fonts/
music/
templates/
config/
settings.py
workflows/
production_pipeline.py
scheduler.py
tests/
logs/
main.py
requirements.txt
README.md
PROJECT_CONTEXT.md
```

---

# Workflow

Step 1

Research Agent generates topics.

Step 2

Script Agent creates script.

Step 3

Voice Agent generates narration.

Step 4

Scene Agent generates scene plan.

Step 5

Video Agent assembles video.

Step 6

Thumbnail Agent generates thumbnail.

Step 7

Human approves content.

Step 8

Publisher Agent uploads video.

Step 9

Analytics Agent monitors performance.

Step 10

Future topics are optimized using collected data.

---

# Phase 1 MVP

Features:

Topic Discovery

Script Generation

Voice Generation

Scene Planning

Video Generation

Manual Upload

Goal:

Publish first 20 videos.

---

# Phase 2

Features:

Thumbnail Generation

Auto Scheduling

Analytics Dashboard

Performance Tracking

Goal:

Reach monetization requirements.

---

# Phase 3

Features:

Multi-channel Support

Full Analytics Feedback Loop

Content Calendar

Auto Optimization

Goal:

Operate as a complete YouTube Content Operating System.

---

# Success Criteria

The platform succeeds when:

1. Generates videos automatically.

2. Produces consistent content.

3. Requires minimal manual effort.

4. Reaches monetization.

5. Operates below ₹500/month before monetization.

6. Supports future scaling without architecture changes.

---

# Non-Goals

Do not build:

* AI-generated deepfakes
* Spam channels
* Copyright-infringing content
* Fully autonomous publishing without approval
* Mass channel farming

The system is intended to create legitimate, original, monetizable YouTube content.
