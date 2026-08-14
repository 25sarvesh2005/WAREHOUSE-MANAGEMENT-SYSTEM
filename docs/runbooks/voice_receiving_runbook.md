# Voice-Assisted Receiving Operations Runbook (AI Release C Slice 1)

## 1. Purpose & Architecture Overview
This runbook guides warehouse operators, warehouse managers, and system administrators in operating, troubleshooting, and verifying **AI Release C Slice 1: Voice-Assisted Receiving Drafts** using **Deepgram**, **Sarvam AI**, and a **Pipecat-ready service architecture**.

```
                           +--------------------------------------------+
                           |  Frontend Push-to-Talk / Web Audio Record  |
                           +--------------------------------------------+
                                                 |
                                                 v
                           +--------------------------------------------+
                           |  POST /api/v1/voice/receiving/transcribe   |
                           +--------------------------------------------+
                                                 |
                   +-----------------------------+-----------------------------+
                   |                                                           |
                   v                                                           v
  [ Deepgram Nova STT Adapter ]                              [ Sarvam Saaras STT (Fallback) ]
                   |                                                           |
                   +-----------------------------+-----------------------------+
                                                 |
                                                 v
                           +--------------------------------------------+
                           |  Voice Safety Boundary Guard               |
                           |  (Rejects mutation & bypass commands)      |
                           +--------------------------------------------+
                                                 |
                                                 v
                           +--------------------------------------------+
                           |  Transcript Parser                         |
                           |  (Gemini LLM -> Deterministic Rules)       |
                           +--------------------------------------------+
                                                 |
                                                 v
                           +--------------------------------------------+
                           |  VoiceReceivingDraft Proposal (DRAFTED)    |
                           +--------------------------------------------+
                                                 |
                   +-----------------------------+-----------------------------+
                   |                                                           |
                   v                                                           v
  [ Visual Confirmation in UI ]                                [ Sarvam Bulbul TTS Read-Back ]
                   |
                   v
  [ Apply Lines to Active Receipt ]
```

---

## 2. Non-Negotiable Safety Protocols
1. **Strictly Draft-Only**: Voice AI **never** directly mutates ledger balances, approves transfers, dispatches shipments, or completes receipts.
2. **Barcode Scan & Manual Confirmation Authoritative**: Product identity is bound by barcode scan or manual lookup—never guessed or invented from speech alone.
3. **Refusal Rules**: Spoken commands attempting mutation (`"complete receipt"`, `"adjust stock"`, `"bypass scan"`, `"switch tenant"`, `"show secret"`) are refused with explicit refusal reasons.
4. **No Secrets in Frontend**: Deepgram and Sarvam API credentials reside strictly in backend environment variables.
5. **Full Auditability**: Every speech transcription, parsed payload, and safety flag is recorded in `voice_interactions` and `voice_receiving_drafts`.

---

## 3. Operator Workflow Guide

### Step 1: Open Inbound Receipt
1. Navigate to `/receipts` and open a draft receipt (or click **Create Inbound Receipt**).
2. Select the intended seller and warehouse dock.

### Step 2: Push-to-Talk Recording
1. In the **Voice-Assisted Receiving Drafts** panel, click and hold the microphone button (or click once to toggle recording).
2. Clearly speak the received breakdown.
   - *Example 1:* `"Received 12 available and 2 damaged note box crushed"`
   - *Example 2:* `"Twenty available, five quarantined note missing certification"`
3. Release the microphone button. Deepgram Nova will transcribe the audio through the backend voice provider.

### Step 3: Text Transcript Fallback (Noisy Floor Mode)
1. If ambient warehouse noise is high, or if microphone permissions are restricted, type or paste the spoken description directly into the transcript box and click **Parse**.

### Step 4: Review Parsed Proposal & Read-Back Summary
1. Inspect the parsed lines in the table:
   - **Quantity** (e.g. `12.00`)
   - **Inventory State** (Available, Damaged, Quarantined)
   - **Condition Notes** (e.g. `"box crushed"`)
2. Click **Read Back Summary** to have Sarvam AI Bulbul TTS vocalize the drafted lines over headphones or dock speakers.

### Step 5: Apply or Discard
1. Click **Apply Lines to Receipt Draft** to transfer the parsed numbers directly into the receipt form.
2. If incorrect, click **Discard Voice Draft** to discard the proposal and try again.
3. Visually verify the final counts and click **Complete Receipt** to commit inventory movements atomically.

---

## 4. Configuration & Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DEEPGRAM_API_KEY` | Deepgram REST STT API key | *Optional / placeholder* |
| `SARVAM_API_KEY` | Sarvam AI REST TTS/STT API key | *Optional / placeholder* |
| `VOICE_STT_PROVIDER` | Primary speech-to-text engine (`deepgram` or `sarvam`) | `deepgram` |
| `VOICE_TTS_PROVIDER` | Primary text-to-speech engine (`sarvam`) | `sarvam` |
| `VOICE_MAX_AUDIO_BYTES` | Maximum audio payload size in bytes | `5242880` (5MB) |
| `VOICE_MAX_AUDIO_SECONDS`| Maximum audio duration | `30` |
| `VOICE_ALLOWED_MIME_TYPES`| Allowed MIME types | `audio/webm,audio/wav,audio/mp4,audio/ogg` |
| `VOICE_DEFAULT_LANGUAGE` | Default BCP-47 language tag | `en-IN` |

---

## 5. Verification Commands

### Automated Test Suite
```bash
# Run voice unit test suite
python -m pytest tests/unit/test_voice_receiving_flows.py

# Run all 105 backend unit tests
python -m pytest tests/unit/

# Run frontend lint, typecheck, and build
cd frontend
npm run lint
npx tsc --noEmit
npm run build

# Run frontend secret audit
python tools/audit_frontend_secrets.py

# Run live E2E smoke test (with running backend API)
python -m tests.e2e.ai_voice_receiving_e2e_test
```

---

## 6. Troubleshooting Guide

### 1. `503 Service Unavailable` on Voice STT or TTS
- **Cause**: `DEEPGRAM_API_KEY` or `SARVAM_API_KEY` is empty or unconfigured.
- **Resolution**: Provide valid provider credentials in `.env`, or use the **Manual Transcript Input** fallback which uses local deterministic parsing and requires zero external provider keys.

### 2. `400 Bad Request: Voice AI is strictly draft-only`
- **Cause**: Spoken transcript contained prohibited action keywords (`"complete receipt"`, `"adjust stock"`, `"ship order"`).
- **Resolution**: Instruct operators to speak only quantities, states, and condition notes.

### 3. Microphone Access Blocked in Browser
- **Cause**: Browser permissions denied for `navigator.mediaDevices.getUserMedia`.
- **Resolution**: Allow microphone in browser site settings, or utilize the manual transcript text box.
