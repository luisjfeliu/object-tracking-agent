from pathlib import Path

from src.tracking.offline_pipeline import replay_tracking


def test_offline_replay_with_sample_log(tmp_path: Path):
    sample_log = Path("data/sample_events.jsonl")
    out_path = tmp_path / "tracks.jsonl"

    track_events, summary = replay_tracking(sample_log, output_path=out_path, summary_window=120)

    assert track_events, "Expected tracker to emit events"
    assert out_path.exists()
    assert "Object detections" in summary or "Object detections by category" in summary
    assert any(ev["details"].get("category") == "bus" for ev in track_events)

