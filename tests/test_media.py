import pytest

from tastebench.tastegraph.assets.analyzer import MockAssetAnalyzer, VLMAssetAnalyzer
from tastebench.tastegraph.assets.media import MockMediaProbe
from tastebench.tastegraph.assets.schema import Asset


def test_mock_analyzer_fingerprints_audio_and_video():
    for t in ("audio", "video"):
        a = Asset(id=f"m_{t}", type=t, uri=f"clip.{t}", duration_s=12.0)
        fp = MockAssetAnalyzer().analyze(a)
        assert fp.asset_id == a.id
        assert fp.aesthetic.style  # populated deterministically
        assert len(fp.advanced.embedding) == 32


def test_mock_media_probe_frames_and_transcript():
    probe = MockMediaProbe()
    frames = probe.sample_frames("clip.mp4", n=3)
    assert len(frames) == 3
    assert all(f.startswith("data:image/png;base64,") for f in frames)
    assert probe.transcribe("clip.mp4").startswith("[mock transcript")


def test_vlm_video_message_uses_frames_and_transcript():
    analyzer = VLMAssetAnalyzer(model="gpt-4o", media_probe=MockMediaProbe())
    asset = Asset(id="v1", type="video", uri="clip.mp4")
    messages = analyzer._messages(asset)
    content = messages[0]["content"]
    kinds = [p["type"] for p in content]
    assert "image_url" in kinds  # frames attached
    assert any("Transcript" in p.get("text", "") for p in content if p["type"] == "text")


def test_vlm_audio_message_uses_transcript():
    analyzer = VLMAssetAnalyzer(model="gpt-4o", media_probe=MockMediaProbe())
    asset = Asset(id="a1", type="audio", uri="clip.mp3")
    messages = analyzer._messages(asset)
    assert "transcript" in messages[0]["content"].lower()


def test_real_av_probe_behind_extra():
    pytest.importorskip("av")
    from tastebench.tastegraph.assets.media import AVMediaProbe

    assert AVMediaProbe is not None  # smoke: import path works when extra present
