import os
import json
import re
from groq import Groq
from backend.vector_store import VectorStore, chunk_text
from dotenv import load_dotenv

load_dotenv(override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.1-8b-instant"

EXTRACTION_PROMPT = """You are an expert meeting analyst. Based on the following meeting transcript excerpts, extract structured information.

Transcript Context:
{context}

Extract and return ONLY a valid JSON object with this exact structure:
{{
  "summary": ["bullet point 1", "bullet point 2"],
  "action_items": [
    {{"assignee": "Name", "task": "task description", "deadline": "deadline or null"}}
  ],
  "decisions": ["decision 1", "decision 2"],
  "risks": ["risk 1", "risk 2"]
}}

Rules:
- summary: 3-6 key discussion points
- action_items: every task assigned to someone, extract name and deadline if mentioned
- decisions: concrete decisions made during the meeting
- risks: any risks, blockers, or concerns raised
- Return ONLY the JSON, no extra text
"""

SPEAKER_DETECTION_PROMPT = """You are analyzing a meeting or podcast transcript with speaker labels like [Speaker A], [Speaker B], [Speaker C] etc.

Transcript:
{transcript}

Your task: Find the REAL name of EVERY speaker in the transcript.

Search strategies:
1. Self introduction: "I am John", "My name is Sarah", "Hi I am Alex", "myself Prajakta"
2. Host introducing guest: "Welcome John", "Joining us today is Sarah", "our guest Priyanka"
3. People addressing each other: "Great point Sarah", "What do you think John?", "Thank you Prajakta"
4. Show/podcast title or opening lines often mention speaker names
5. Any name mentioned immediately before or after a speaker turn

Important rules:
- Read carefully — names may appear anywhere in the transcript
- If Speaker A says "I am Prajakta" or "myself Prajakta" then A = Prajakta
- If someone says "Welcome Priyanka" to Speaker B then B = Priyanka
- A speaker saying "I" or "my" refers to themselves
- Guest names are often mentioned in first few exchanges
- Consider ALL speaker letters found in transcript

Return ONLY a JSON object with ALL speaker letters as keys.
Example for 4 speakers:
{{
  "A": "John",
  "B": "Sarah",
  "C": "Mike",
  "D": null
}}

Use null if name truly cannot be found for that speaker.
Return ONLY the JSON, no extra text, no explanation.
"""


class RAGService:
    def __init__(self):
        self.store = VectorStore()
        self.transcript = ""
        self.speaker_map = {}
        self.store.load()

    def ingest(self, text: str):
        """Chunk and index the transcript."""
        self.transcript = text
        self.speaker_map = {}
        chunks = chunk_text(text, chunk_size=300, overlap=50)
        self.store.build(chunks)
        self.store.save()
        print(f"[RAGService] Ingested {len(chunks)} chunks.")

    def get_speaker_letters(self) -> list:
        """Extract all unique speaker letters from transcript."""
        letters = sorted(set(re.findall(r'\[Speaker ([A-Z])\]', self.transcript)))
        return letters if letters else ["A", "B"]

    def detect_speakers(self) -> dict:
        """Auto detect speaker names from transcript using LLaMA3."""
        letters = self.get_speaker_letters()
        print(f"[RAGService] Detecting names for speakers: {letters}")

        prompt = SPEAKER_DETECTION_PROMPT.format(
            transcript=self.transcript[:15000]
        )

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )

        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        try:
            result = json.loads(raw)
            # Ensure all detected letters are in result
            for letter in letters:
                if letter not in result:
                    result[letter] = None
            self.speaker_map = {k: v for k, v in result.items() if v}
            print(f"[RAGService] Detected speakers: {result}")
            return result
        except json.JSONDecodeError:
            print(f"[RAGService] Could not parse speaker detection result: {raw}")
            return {letter: None for letter in letters}

    def apply_speaker_map(self, speaker_map: dict):
        """Apply speaker name mapping to transcript and re-ingest."""
        updated = self.transcript
        for letter, name in speaker_map.items():
            if name:
                updated = updated.replace(f"[Speaker {letter}]", f"[{name}]")
        self.transcript = updated
        self.speaker_map = speaker_map
        # Re-ingest with updated transcript
        chunks = chunk_text(updated, chunk_size=300, overlap=50)
        self.store.build(chunks)
        self.store.save()
        print(f"[RAGService] Speaker map applied and re-ingested: {speaker_map}")

    def extract(self) -> dict:
        """Use RAG + Groq to extract structured meeting info."""
        queries = [
            "main topics discussed in the meeting",
            "action items tasks assigned to people with deadlines",
            "decisions made conclusions agreed upon",
            "risks blockers concerns raised"
        ]

        all_chunks = set()
        for q in queries:
            results = self.store.search(q, top_k=4)
            all_chunks.update(results)

        context = "\n\n".join(list(all_chunks)[:5])
        prompt = EXTRACTION_PROMPT.format(context=context)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024
        )

        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {
                "summary": ["Could not parse structured output."],
                "action_items": [],
                "decisions": [],
                "risks": [],
                "raw": raw
            }

        return result

    def ask(self, question: str) -> str:
        """Q&A on the meeting transcript."""
        chunks = self.store.search(question, top_k=5)
        context = "\n\n".join(chunks)

        prompt = f"""You are a helpful meeting assistant. Answer the question based only on the meeting transcript below.

Transcript Context:
{context}

Question: {question}

Answer concisely and clearly:"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()
