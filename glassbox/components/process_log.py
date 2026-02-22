"""
process_log.py — TWFF ProcessLog

Core TWFF session recording logic, fully decoupled from NiceGUI / any UI framework.
This module can be imported by the browser extension, LMS plugin, CLI tools, etc.
"""
import datetime
import hashlib
import io
import json
import uuid
import zipfile

# Annotation type registry
# Drives: CSS class names, legend labels, log event types.
ANNOTATION_TYPES = {
    "ai_paraphrase": {
        "css_class":   "ann-paraphrase",
        "label":       "AI Paraphrase",
        "description": "Text rewritten by an AI assistant",
        "log_type":    "ai_interaction",
        "interaction": "paraphrase",
    },
    "ai_generated": {
        "css_class":   "ann-generated",
        "label":       "AI Generated",
        "description": "Text written entirely by an AI assistant",
        "log_type":    "ai_interaction",
        "interaction": "draft",
    },
    "external_paste": {
        "css_class":   "ann-external",
        "label":       "External Source",
        "description": "Text pasted from an external source",
        "log_type":    "paste",
        "interaction": "external",
    },
    "ai_completion": {
        "css_class":   "ann-completion",
        "label":       "AI Completion",
        "description": "Tab-completed by Glass Box",
        "log_type":    "ai_interaction",
        "interaction": "completion",
    },
}


class ProcessLog:
    """
    TWFF v0.1 process log.

    Instantiate once per writing session. Call log_event() as the user writes.
    Call export() to produce a .twff ZIP container as bytes.
    """

    SPEC_VERSION = "0.1.0"

    def __init__(self, user_id: str | None = None):
        self.session_id: str = str(uuid.uuid4())
        # Per spec: user_id is user-generated, anonymous, rotatable.
        # If none supplied, generate an ephemeral one for this session.
        self.user_id: str = user_id or self._generate_ephemeral_id()
        self.start_time: str = datetime.datetime.utcnow().isoformat() + "Z"
        self.events: list[dict] = []
        self._content_source = "content/document.xhtml"

        self.log_event("session_start")

    # Public API

    def log_event(self, event_type: str, meta: dict | None = None) -> dict:
        """
        Append a TWFF event to the log.

        Args:
            event_type: One of the TWFF event type strings (session_start, edit,
                        paste, ai_interaction, chat_interaction, focus_change,
                        checkpoint, session_end).
            meta:       Type-specific metadata dict per the spec schema.

        Returns:
            The event dict that was appended.
        """
        event = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            "meta": meta or {},
        }
        self.events.append(event)
        return event

    def log_checkpoint(self, char_count: int, word_count: int, cursor_position: int) -> dict:
        return self.log_event("checkpoint", {
            "char_count_total": char_count,
            "word_count_total": word_count,
            "position": cursor_position,
        })

    def log_edit(self, position_start: int, position_end: int, source: str = "human") -> dict:
        return self.log_event("edit", {
            "position_start": position_start,
            "position_end": position_end,
            "source": source,
        })

    def log_paste(self, char_count: int, position_start: int, position_end: int,
                  source: str = "external", preview: str = "") -> dict:
        return self.log_event("paste", {
            "char_count": char_count,
            "source": source,
            "position_start": position_start,
            "position_end": position_end,
            "output_preview": preview[:100],
        })

    def log_ai_interaction(self, interaction_type: str, model: str,
                           output_length: int, position_start: int, position_end: int,
                           output_preview: str = "", acceptance: str = "fully_accepted",
                           input_preview: str = "") -> dict:
        return self.log_event("ai_interaction", {
            "interaction_type": interaction_type,
            "model": model,
            "input_preview": input_preview[:100],
            "output_preview": output_preview[:50],
            "output_length": output_length,
            "position_start": position_start,
            "position_end": position_end,
            "acceptance": acceptance,
        })

    def log_focus_change(self, duration_ms: int) -> dict:
        return self.log_event("focus_change", {"duration_ms": duration_ms})

    def end_session(self) -> str:
        """Finalise the session. Returns end_time ISO string."""
        end_time = datetime.datetime.utcnow().isoformat() + "Z"
        self.log_event("session_end")
        return end_time

    def to_dict(self, end_time: str | None = None) -> dict:
        """Return the process log as a spec-compliant dict."""
        return {
            "version": self.SPEC_VERSION,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.start_time,
            "end_time": end_time or datetime.datetime.utcnow().isoformat() + "Z",
            "content_source": self._content_source,
            "events": self.events,
        }

    def export(self, xhtml_content: str) -> bytes:
        """
        Package content + process log into a TWFF ZIP container.

        Args:
            xhtml_content: The final document as XHTML string.

        Returns:
            Raw bytes of the .twff ZIP file.
        """
        end_time = self.end_session()
        process_log_dict = self.to_dict(end_time)

        # Compute integrity hash of the events array
        events_json = json.dumps(self.events, sort_keys=True)
        salt = self.session_id
        integrity_hash = hashlib.sha256((events_json + salt).encode()).hexdigest()
        process_log_dict["_integrity"] = {
            "algorithm": "SHA-256",
            "salt": "session_id",
            "hash": integrity_hash,
            "note": "Hash of events array concatenated with session_id salt."
        }

        manifest = self._build_manifest()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("content/document.xhtml", xhtml_content)
            zf.writestr("meta/process-log.json", json.dumps(process_log_dict, indent=2))
            zf.writestr("meta/manifest.xml", manifest)
        buf.seek(0)
        return buf.getvalue()

    # Private helpers

    @staticmethod
    def _generate_ephemeral_id() -> str:
        """
        Generate a short, anonymous, session-scoped user ID.
        Not stored anywhere — user can rotate by refreshing.
        """
        raw = str(uuid.uuid4())
        return "anon-" + hashlib.sha256(raw.encode()).hexdigest()[:12]

    def _build_manifest(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<manifest>\n"
            '  <item id="content" href="content/document.xhtml"'
            ' media-type="application/xhtml+xml"/>\n'
            '  <item id="log" href="meta/process-log.json"'
            ' media-type="application/json"/>\n'
            "</manifest>"
        )
