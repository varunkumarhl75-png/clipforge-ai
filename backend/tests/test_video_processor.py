import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
from app.services.video_processor.ffmpeg_service import (
    FFmpegService,
    FFmpegNotFoundError,
    InvalidVideoError,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def ffmpeg_service():
    """Create FFmpegService instance."""
    return FFmpegService()


class TestFFmpegService:
    """Test FFmpeg service."""

    def test_check_ffmpeg_available_found(self, ffmpeg_service):
        """Test ffmpeg availability check when installed."""
        with patch("app.services.video_processor.ffmpeg_service.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            assert ffmpeg_service.check_ffmpeg_available() is True

    def test_check_ffmpeg_available_not_found(self, ffmpeg_service):
        """Test ffmpeg availability check when not installed."""
        with patch(
            "app.services.video_processor.ffmpeg_service.subprocess.run"
        ) as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert ffmpeg_service.check_ffmpeg_available() is False

    def test_validate_video_file_valid(self, ffmpeg_service, temp_dir):
        """Test video file validation with valid video."""
        # Create a mock video file
        video_file = temp_dir / "test.mp4"
        video_file.write_text("mock video")

        mock_ffprobe_output = {
            "streams": [{"codec_type": "video"}],
            "format": {"duration": "10.5"},
        }

        with patch(
            "app.services.video_processor.ffmpeg_service.subprocess.run"
        ) as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(mock_ffprobe_output)
            )
            assert ffmpeg_service.validate_video_file(str(video_file)) is True

    def test_validate_video_file_invalid(self, ffmpeg_service, temp_dir):
        """Test video file validation with invalid video."""
        video_file = temp_dir / "test.mp4"
        video_file.write_text("mock video")

        with patch(
            "app.services.video_processor.ffmpeg_service.subprocess.run"
        ) as mock_run:
            mock_run.side_effect = Exception("Invalid video")
            with pytest.raises(InvalidVideoError):
                ffmpeg_service.validate_video_file(str(video_file))

    def test_extract_metadata(self, ffmpeg_service, temp_dir):
        """Test metadata extraction."""
        video_file = temp_dir / "test.mp4"
        video_file.write_text("mock video")

        mock_ffprobe_output = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                    "bit_rate": "5000000",
                },
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"duration": "120.5", "size": "1000000"},
        }

        with patch(
            "app.services.video_processor.ffmpeg_service.subprocess.run"
        ) as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(mock_ffprobe_output)
            )
            metadata = ffmpeg_service.extract_metadata(str(video_file))

            assert metadata["duration"] == 120.5
            assert metadata["width"] == 1920
            assert metadata["height"] == 1080
            assert metadata["fps"] == 30.0
            assert metadata["video_codec"] == "h264"
            assert metadata["audio_codec"] == "aac"
            assert metadata["bitrate"] == "5000000"
            assert metadata["file_size"] == 1000000
            assert metadata["has_audio"] is True

    def test_extract_metadata_no_audio(self, ffmpeg_service, temp_dir):
        """Test metadata extraction without audio."""
        video_file = temp_dir / "test.mp4"
        video_file.write_text("mock video")

        mock_ffprobe_output = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                }
            ],
            "format": {"duration": "120.5"},
        }

        with patch(
            "app.services.video_processor.ffmpeg_service.subprocess.run"
        ) as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(mock_ffprobe_output)
            )
            metadata = ffmpeg_service.extract_metadata(str(video_file))

            assert metadata["has_audio"] is False
            assert metadata["audio_codec"] is None

    def test_generate_thumbnail(self, ffmpeg_service, temp_dir):
        """Test thumbnail generation."""
        video_file = temp_dir / "test.mp4"
        output_file = temp_dir / "thumbnail.jpg"
        video_file.write_text("mock video")

        with patch(
            "app.services.video_processor.ffmpeg_service.subprocess.run"
        ) as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = ffmpeg_service.generate_thumbnail(
                str(video_file), str(output_file)
            )

            assert result is True
            # Verify subprocess was called with correct args
            call_args = mock_run.call_args[1]
            assert call_args["check"] is True

    def test_generate_thumbnail_with_timestamp(self, ffmpeg_service, temp_dir):
        """Test thumbnail generation with specific timestamp."""
        video_file = temp_dir / "test.mp4"
        output_file = temp_dir / "thumbnail.jpg"
        video_file.write_text("mock video")

        with patch(
            "app.services.video_processor.ffmpeg_service.subprocess.run"
        ) as mock_run:
            mock_run.return_value = Mock(returncode=0)
            ffmpeg_service.generate_thumbnail(
                str(video_file), str(output_file), timestamp=5.5
            )

            # Verify subprocess was called with timestamp
            call_args = mock_run.call_args[0][0]
            assert "-ss" in call_args
            assert "5.5" in call_args

    def test_extract_audio(self, ffmpeg_service, temp_dir):
        """Test audio extraction."""
        video_file = temp_dir / "test.mp4"
        output_file = temp_dir / "audio.wav"
        video_file.write_text("mock video")

        with patch(
            "app.services.video_processor.ffmpeg_service.subprocess.run"
        ) as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = ffmpeg_service.extract_audio(str(video_file), str(output_file))

            assert result is True

    def test_cleanup_temp_files(self, ffmpeg_service, temp_dir):
        """Test temporary file cleanup."""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        file1.write_text("test")
        file2.write_text("test")

        assert file1.exists()
        assert file2.exists()

        ffmpeg_service.cleanup_temp_files(str(file1), str(file2))

        assert not file1.exists()
        assert not file2.exists()

    def test_cleanup_temp_files_nonexistent(self, ffmpeg_service):
        """Test cleanup with non-existent files."""
        # Should not raise exception
        ffmpeg_service.cleanup_temp_files("/nonexistent/file1.txt")
