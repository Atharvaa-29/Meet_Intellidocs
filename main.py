import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.rag_service import RAGService
from backend.transcriber import transcribe_video
from backend.file_parser import parse_file

app = FastAPI(title="Meeting RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

rag = RAGService()

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
TEXT_EXTENSIONS  = {".txt", ".pdf", ".docx"}


class QuestionRequest(BaseModel):
    question: str


class SpeakerMapRequest(BaseModel):
    speaker_map: dict


class NumSpeakersRequest(BaseModel):
    num_speakers: int


@app.get("/")
def root():
    return {"status": "Meeting RAG API is running"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), num_speakers: int = 2):
    ext = Path(file.filename).suffix.lower()
    save_path = UPLOAD_DIR / file.filename

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        if ext in VIDEO_EXTENSIONS:
            transcript = transcribe_video(str(save_path), num_speakers=num_speakers)
        elif ext in TEXT_EXTENSIONS:
            transcript = parse_file(str(save_path))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

        rag.ingest(transcript)

        return {
            "status": "success",
            "filename": file.filename,
            "type": "video" if ext in VIDEO_EXTENSIONS else "document",
            "transcript_preview": transcript[:500] + "..." if len(transcript) > 500 else transcript,
            "transcript_length": len(transcript),
            "speakers_found": rag.get_speaker_letters()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect-speakers")
def detect_speakers():
    """Auto detect speaker names from transcript using LLaMA3."""
    try:
        result = rag.detect_speakers()
        return {
            "status": "success",
            "speaker_map": result,
            "speakers_found": rag.get_speaker_letters()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/map-speakers")
def map_speakers(request: SpeakerMapRequest):
    """Apply manual or confirmed speaker name mapping."""
    try:
        rag.apply_speaker_map(request.speaker_map)
        return {"status": "success", "message": "Speaker names applied successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract")
def extract():
    """Run RAG extraction and return structured meeting summary."""
    try:
        result = rag.extract()
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def ask_question(request: QuestionRequest):
    """Ask a follow-up question about the meeting."""
    try:
        answer = rag.ask(request.question)
        return {"status": "success", "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transcript")
def get_transcript():
    """Return full transcript."""
    return {"transcript": rag.transcript}
