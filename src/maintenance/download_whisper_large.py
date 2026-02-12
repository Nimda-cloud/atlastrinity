from pathlib import Path

from faster_whisper import WhisperModel


def download():
    model_name = "large-v3"
    download_root = Path.home() / ".config" / "atlastrinity" / "models" / "faster-whisper"

    # This will trigger the download and conversion/verification
    WhisperModel(model_name, device="cpu", compute_type="int8", download_root=str(download_root))


if __name__ == "__main__":
    download()
