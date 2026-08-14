"""
--------------------------------------------------------------------------------
File        : core/services/voice/pipecat_pipeline.py
Purpose     : Define modular streaming pipeline architecture for future Pipecat / WebRTC integration.

Responsibilities:
    - Provide an extensible streaming abstraction for real-time bidirectional audio (AI Release C Slice 2).
    - Maintain strict safety boundaries: streaming sessions may draft, but never mutate ledger directly.
    - Remain completely import-safe without requiring optional streaming C-bindings during Slice 1.

Flow:
    WebRTC / WebSocket client
        ->
    VoiceStreamingSession (Slice 2 architecture)
        ->
    Pipecat Pipeline (VAD -> Deepgram STT -> Gemini/Parser -> Sarvam TTS)

Used By:
    - Future real-time streaming routes (Slice 2)

Returns:
    VoiceStreamingSession - Streaming state container.

Raises:
    NotImplementedError: If real-time streaming is invoked before Slice 2 implementation.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass
class VoiceStreamFrame:
    """Represents a discrete audio or text event in the streaming pipeline."""

    frame_id: str = field(default_factory=lambda: str(uuid4()))
    frame_type: str = "audio_chunk"  # audio_chunk, transcript_delta, interim_draft, eos
    payload_bytes: bytes = b""
    text_content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class VoiceStreamingSession:
    """
    Session container for real-time push-to-talk or continuous WebRTC streaming.

    Designed for upcoming Pipecat integration in AI Release C Slice 2.
    """

    def __init__(
        self,
        *,
        actor_user_id: UUID,
        warehouse_id: UUID | None = None,
        language_code: str = "en-IN",
    ) -> None:
        """
        Initialize a streaming session container.

        Args:
            actor_user_id: Authenticated user identity.
            warehouse_id: Scoped warehouse location.
            language_code: Target language code.

        Returns:
            None.
        """
        self.session_id: str = str(uuid4())
        self.actor_user_id: UUID = actor_user_id
        self.warehouse_id: UUID | None = warehouse_id
        self.language_code: str = language_code
        self.is_active: bool = False
        self.accumulated_frames: list[VoiceStreamFrame] = []
        self.interim_transcript: str = ""

    async def start(self) -> None:
        """Activate streaming session pipeline."""
        self.is_active = True

    async def push_frame(self, frame: VoiceStreamFrame) -> None:
        """Process an incoming audio frame or control event."""
        if not self.is_active:
            raise RuntimeError("Streaming session is not active.")
        self.accumulated_frames.append(frame)

    async def close(self) -> dict[str, Any]:
        """Close streaming session and return summary metadata."""
        self.is_active = False
        return {
            "session_id": self.session_id,
            "total_frames": len(self.accumulated_frames),
            "language_code": self.language_code,
        }
