🎙️ MeetingIntelliDocs

MeetingIntelliDocs is an end-to-end AI pipeline that transforms 
Microsoft Teams recordings into structured Minutes of Meeting (MoM) 
reports — automatically.

Upload a meeting recording and get:
✅ Summary of key discussion points
✅ Action Items with assignees and deadlines  
✅ Decisions made during the meeting
✅ Risks and blockers raised
✅ Speaker identification (who said what)
✅ Q&A — ask any question about the meeting
✅ Export report as TXT or PDF

🧠 How it works:
Video → ffmpeg (audio extraction) → AssemblyAI (transcription + 
speaker diarization) → HuggingFace MiniLM (vector embeddings) → 
FAISS (semantic search) → Groq LLaMA3 (structured extraction)

🛠️ Tech Stack:
- Transcription   — AssemblyAI Universal-2 (speaker diarization built-in)
- Embeddings      — HuggingFace all-MiniLM-L6-v2 (local)
- Vector DB       — FAISS (local)
- LLM             — Groq LLaMA3 (free tier)
- Backend         — FastAPI
- Frontend        — Streamlit
- Audio Extraction — ffmpeg

💡 Key Features:
- Auto speaker name detection using LLaMA3
- Manual speaker name mapping fallback
- Supports 1-6 speakers dynamically
- RAG pipeline for accurate context-aware extraction
- 100% free stack — no paid APIs required
- Privacy-first — embeddings and vector search run locally

📁 Supports:
- Video: .mp4, .mkv, .mov, .avi, .webm
- Documents: .txt, .pdf, .docx



MeetingIntelliDocs/
│
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── rag_service.py
│   ├── vector_store.py
│   ├── embedding.py
│   ├── transcriber.py
│   └── file_parser.py
│
├── frontend/
│   └── app.py
│
├── data/                        # auto created on first run
│   ├── uploads/                 # uploaded video/audio files
│   ├── transcripts/             # AssemblyAI transcript output
│   └── faiss_index/             # FAISS vector index storage
│
├── .env                        
└── requirements.txt
