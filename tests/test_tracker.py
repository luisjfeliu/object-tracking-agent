from src.tracking.tracker import MultiObjectTracker, iou


def test_iou_basic():
    box_a = [0, 0, 2, 2]
    box_b = [1, 1, 3, 3]
    assert round(iou(box_a, box_b), 3) == 0.143


def test_tracker_persists_id_across_frames():
    tracker = MultiObjectTracker(iou_threshold=0.2, max_missed=2)
    frame0 = [{"category": "car", "bbox": [0, 0, 2, 2], "score": 0.9}]
    frame1 = [{"category": "car", "bbox": [0.1, 0.0, 2.1, 2.0], "score": 0.88}]

    tracks_frame0 = tracker.update(frame0, frame_id=0)
    tracks_frame1 = tracker.update(frame1, frame_id=1)

    assert len(tracks_frame0) == 1
    assert len(tracks_frame1) == 1
    assert tracks_frame0[0]["track_id"] == tracks_frame1[0]["track_id"]
    assert tracks_frame1[0]["last_frame"] == 1


def test_tracker_drops_stale_tracks():
    tracker = MultiObjectTracker(iou_threshold=0.3, max_missed=1)
    tracker.update([{"category": "person", "bbox": [0, 0, 1, 1], "score": 0.95}], frame_id=0)

    # Two empty frames -> track should be removed
    tracker.update([], frame_id=1)
    remaining = tracker.update([], frame_id=2)
    assert remaining == []

