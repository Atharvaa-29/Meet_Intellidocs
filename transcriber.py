import os
import subprocess
import assemblyai as aai
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TRANSCRIPTS_DIR = Path("data/transcripts")
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")


def extract_audio_from_video(video_path: str) -> str:
    """Extract and compress audio from video file using ffmpeg."""
    video_path = Path(video_path)
    audio_path = str(TRANSCRIPTS_DIR / (video_path.stem + "_audio.mp3"))

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "64k",
        "-f", "mp3",
        audio_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed.\nError: {result.stderr[-600:]}")

    size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"[Transcriber] Audio extracted: {audio_path} ({size_mb:.1f} MB)")
    return audio_path


def transcribe_audio(audio_path: str, num_speakers: int = 2) -> str:
    """Send audio to AssemblyAI and get transcript with speaker labels."""
    print(f"[AssemblyAI] Transcribing with {num_speakers} expected speakers...")

    config = aai.TranscriptionConfig(
        speaker_labels=True,
        punctuate=True,
        format_text=True,
        speech_models=["universal-2"],
        speakers_expected=num_speakers
    )

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_path, config=config)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI error: {transcript.error}")

    if transcript.utterances:
        lines = []
        for utterance in transcript.utterances:
            lines.append(f"[Speaker {utterance.speaker}]: {utterance.text}")
        full_transcript = "\n".join(lines)
    else:
        full_transcript = transcript.text or ""

    print(f"[AssemblyAI] Transcription complete. {len(full_transcript)} chars.")
    return full_transcript.strip()


def transcribe_video(video_path: str, num_speakers: int = 2, model_size: str = "base") -> str:
    """Full pipeline: video -> audio -> AssemblyAI -> transcript."""
    audio_path = extract_audio_from_video(video_path)
    transcript = transcribe_audio(audio_path, num_speakers=num_speakers)

    transcript_file = TRANSCRIPTS_DIR / (Path(video_path).stem + "_transcript.txt")
    transcript_file.write_text(transcript, encoding="utf-8")
    print(f"[Transcriber] Transcript saved: {transcript_file}")

    return transcript
