import json
import threading
from typing import Sequence

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

class FileSpanExporter(SpanExporter):
    """A simple OpenTelemetry span exporter that writes spans to a file as JSON lines.

    This exporter performs a best-effort conversion of span objects to JSON-serializable
    dictionaries and appends them to the configured file. It is intended for local
    debugging or CI use where an OTLP backend is not available.
    """
    def __init__(self, file_path: str = "trace.ndjson"):
        self._file_path = file_path
        self._lock = threading.Lock()

    def export(self, spans: Sequence[object]) -> "SpanExportResult":
        records = []
        for span in spans:
            try:
                rec = self._span_to_dict(span)
            except Exception:
                # fallback to a minimal representation
                rec = {"name": getattr(span, "name", str(span)), "error": "serialization_failed"}
            records.append(rec)

        # append JSON lines
        try:
            with self._lock:
                with open(self._file_path, "a", encoding="utf-8") as fh:
                    for r in records:
                        fh.write(json.dumps(r, default=str))
                        fh.write("\n")
            return SpanExportResult.SUCCESS
        except Exception:
            return SpanExportResult.FAILURE if hasattr(SpanExportResult, 'FAILURE') else SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        # nothing to clean up for file exporter
        return None

    def _span_to_dict(self, span: object) -> dict:
        # span is typically an opentelemetry.sdk.trace._Span
        d = {
            "name": getattr(span, "name", None),
            "context": {
                "span_id": getattr(getattr(span, "context", None), "span_id", None),
                "trace_id": getattr(getattr(span, "context", None), "trace_id", None),
            },
            "parent_span_id": getattr(getattr(span, "parent", None), "span_id", None) or getattr(span, "parent_span_id", None),
            "start_time": getattr(span, "start_time", None),
            "end_time": getattr(span, "end_time", None),
            "attributes": {},
            "events": [],
            "status": None,
        }

        # attributes
        attrs = getattr(span, "attributes", None)
        if attrs:
            try:
                for k, v in attrs.items():
                    d["attributes"][k] = v
            except Exception:
                d["attributes"] = {str(k): str(v) for k, v in attrs.items()}

        # events
        events = getattr(span, "events", None)
        if events:
            try:
                for ev in events:
                    evdict = {
                        "name": getattr(ev, "name", None),
                        "attributes": getattr(ev, "attributes", None),
                        "timestamp": getattr(ev, "timestamp", None),
                    }
                    d["events"].append(evdict)
            except Exception:
                pass

        # status
        st = getattr(span, "status", None)
        if st is not None:
            try:
                d["status"] = {"status_code": getattr(st, "status_code", None), "description": getattr(st, "description", None)}
            except Exception:
                d["status"] = str(st)

        return d
