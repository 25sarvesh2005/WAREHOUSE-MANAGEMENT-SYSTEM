import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Mic,
  MicOff,
  RefreshCw,
  Send,
  ShieldCheck,
  Trash2,
  Volume2,
} from "lucide-react";
import {
  useVoiceDiscardDraftMutation,
  useVoiceParseTranscriptMutation,
  useVoiceSpeakMutation,
  useVoiceTranscribeMutation,
} from "@/hooks/use-api";
import type { VoiceParsedLine, VoiceReceivingDraft } from "@/lib/types";

interface ReceivingVoiceDraftPanelProps {
  warehouseId?: string | null;
  productId?: string | null;
  receiptId?: string | null;
  sellerId?: string | null;
  onApplyLines?: (lines: VoiceParsedLine[], notes?: string | null) => void;
  onApplyToReceiptDraft?: (lines: VoiceParsedLine[], notes?: string | null) => void;
  className?: string;
}

function draftSummary(lines: VoiceParsedLine[]): string {
  return lines
    .map(
      (line) =>
        `${line.quantity} ${line.inventory_state.toLowerCase()}${
          line.condition_note ? `, note ${line.condition_note}` : ""
        }`,
    )
    .join("; ");
}

function stateClass(state: string): string {
  if (state === "AVAILABLE") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (state === "DAMAGED") return "border-rose-200 bg-rose-50 text-rose-800";
  return "border-purple-200 bg-purple-50 text-purple-800";
}

export function ReceivingVoiceDraftPanel({
  warehouseId,
  productId,
  receiptId,
  onApplyLines,
  onApplyToReceiptDraft,
  className = "",
}: ReceivingVoiceDraftPanelProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [manualTranscript, setManualTranscript] = useState("");
  const [languageCode, setLanguageCode] = useState("en-IN");
  const [activeDraft, setActiveDraft] = useState<VoiceReceivingDraft | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const transcribeMutation = useVoiceTranscribeMutation();
  const parseTranscriptMutation = useVoiceParseTranscriptMutation();
  const speakMutation = useVoiceSpeakMutation();
  const discardDraftMutation = useVoiceDiscardDraftMutation();

  const isBusy =
    transcribeMutation.isPending ||
    parseTranscriptMutation.isPending ||
    speakMutation.isPending ||
    discardDraftMutation.isPending;

  useEffect(() => {
    const player = audioPlayerRef.current;
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      }
      player?.pause();
    };
  }, []);

  const startRecording = async () => {
    setErrorMsg(null);
    audioChunksRef.current = [];

    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMsg("Microphone is unavailable in this browser. Use the transcript box instead.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "audio/mp4";
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        if (timerRef.current) clearInterval(timerRef.current);
        setRecordingSeconds(0);
        setIsRecording(false);

        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        if (audioBlob.size === 0) {
          setErrorMsg("No audio was recorded. Try again or type the transcript manually.");
          return;
        }

        const formData = new FormData();
        formData.append(
          "file",
          audioBlob,
          `voice_receiving_${Date.now()}.${mimeType.includes("mp4") ? "mp4" : "webm"}`,
        );
        if (warehouseId) formData.append("warehouse_id", warehouseId);
        if (productId) formData.append("product_id", productId);
        if (receiptId) formData.append("receipt_id", receiptId);
        formData.append("language_code", languageCode);

        try {
          const draft = await transcribeMutation.mutateAsync(formData);
          setActiveDraft(draft);
          setManualTranscript(draft.transcript);
        } catch (error: unknown) {
          setErrorMsg(error instanceof Error ? error.message : "Voice transcription failed.");
        }
      };

      recorder.start(250);
      setIsRecording(true);
      setRecordingSeconds(0);
      timerRef.current = window.setInterval(() => {
        setRecordingSeconds((value) => value + 1);
      }, 1000);
    } catch (error: unknown) {
      setIsRecording(false);
      setErrorMsg(error instanceof Error ? error.message : "Could not open microphone.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  };

  const handleParseText = async (textToParse?: string) => {
    const transcript = (textToParse ?? manualTranscript).trim();
    if (!transcript) {
      setErrorMsg("Speak or type receiving quantities before parsing.");
      return;
    }

    setErrorMsg(null);
    try {
      const draft = await parseTranscriptMutation.mutateAsync({
        transcript,
        warehouse_id: warehouseId || null,
        product_id: productId || null,
        receipt_id: receiptId || null,
        language_code: languageCode,
      });
      setActiveDraft(draft);
      setManualTranscript(draft.transcript);
    } catch (error: unknown) {
      setErrorMsg(error instanceof Error ? error.message : "Could not parse transcript.");
    }
  };

  const handleReadBack = async () => {
    if (!activeDraft?.lines.length) return;
    const script = `Draft summary: ${draftSummary(activeDraft.lines)}`;
    setErrorMsg(null);
    setIsPlayingAudio(true);

    try {
      const response = await speakMutation.mutateAsync({
        text: script,
        language_code: languageCode,
      });
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = `data:${response.mime_type};base64,${response.audio_base64}`;
        await audioPlayerRef.current.play();
        audioPlayerRef.current.onended = () => setIsPlayingAudio(false);
      }
    } catch {
      if ("speechSynthesis" in window) {
        const utterance = new SpeechSynthesisUtterance(script);
        utterance.lang = languageCode;
        utterance.onend = () => setIsPlayingAudio(false);
        utterance.onerror = () => setIsPlayingAudio(false);
        window.speechSynthesis.speak(utterance);
      } else {
        setIsPlayingAudio(false);
        setErrorMsg("Read-back audio is unavailable. Review the draft visually.");
      }
    }
  };

  const handleDiscard = async () => {
    if (!activeDraft) return;
    setErrorMsg(null);
    try {
      await discardDraftMutation.mutateAsync({
        draftId: activeDraft.draft_id,
        reason: "Operator discarded voice receiving draft",
      });
      setActiveDraft(null);
      setManualTranscript("");
    } catch (error: unknown) {
      setErrorMsg(error instanceof Error ? error.message : "Could not discard draft.");
    }
  };

  const handleApply = () => {
    if (!activeDraft?.lines.length) return;
    const apply = onApplyToReceiptDraft || onApplyLines;
    apply?.(activeDraft.lines, activeDraft.general_notes);
    setActiveDraft(null);
    setManualTranscript("");
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <section className={`card-surface overflow-hidden ${className}`}>
      <audio ref={audioPlayerRef} className="hidden" />

      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border bg-white px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-xl bg-primary-tint text-primary">
              <Mic className="size-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">
                Voice-Assisted Receiving Intake
              </h3>
              <p className="text-xs text-muted-foreground">
                Powered by Sarvam AI Speech-to-Text & Bulbul Speech Synthesis
              </p>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={languageCode}
            onChange={(event) => setLanguageCode(event.target.value)}
            disabled={isRecording || isBusy}
            className="rounded-full border border-input bg-white px-3 py-1.5 text-xs font-semibold text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
          >
            <option value="en-IN">English (India - en-IN)</option>
            <option value="hi-IN">Hindi (India - hi-IN)</option>
            <option value="en-US">English (US - en-US)</option>
          </select>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-tint px-3 py-1.5 text-xs font-semibold text-primary">
            <ShieldCheck className="size-3.5" />
            Safe Draft Intake
          </span>
        </div>
      </div>

      <div className="grid gap-5 p-5 xl:grid-cols-[300px_1fr]">
        <div className="rounded-3xl bg-primary-tint/60 border border-primary/20 p-4">
          <button
            type="button"
            onClick={toggleRecording}
            disabled={isBusy}
            className={`flex h-24 w-full flex-col items-center justify-center gap-1.5 rounded-2xl text-sm font-bold shadow-md transition-all ${
              isRecording
                ? "bg-status-red text-white animate-pulse shadow-status-red/30"
                : "bg-primary text-white hover:bg-primary-dark shadow-primary/25"
            } disabled:opacity-60 cursor-pointer`}
          >
            <div className="flex items-center gap-2 text-base">
              {isRecording ? <MicOff className="size-5" /> : <Mic className="size-5" />}
              <span>{isRecording ? `Recording... (${recordingSeconds}s)` : "Click / Tap to Speak"}</span>
            </div>
            <span className="text-[11px] font-medium opacity-90">
              {isRecording ? "Click again to Stop & Parse" : "or Click an example phrase below"}
            </span>
          </button>

          <p className="mt-3 text-xs leading-5 text-muted-foreground">
            Say: <span className="font-semibold">12 available, 2 damaged, note box crushed.</span>
            Voice output becomes a reviewable draft, not a completed receipt.
          </p>

          <div className="mt-4 space-y-2 border-t border-primary/10 pt-4">
            <p className="text-[11px] font-bold uppercase tracking-wider text-primary">1-Click Test Phrases:</p>
            {[
              "received 12 available and 2 damaged note box crushed",
              "10 available, 5 quarantined note quality inspection",
              "50 sellable units in good condition",
              "20 available, 1 damaged note seal broken",
            ].map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => {
                  setManualTranscript(example);
                  handleParseText(example);
                }}
                className="block w-full rounded-xl bg-white px-3 py-2 text-left text-[11px] font-medium text-foreground transition hover:bg-primary-tint hover:text-primary border border-border shadow-xs cursor-pointer"
              >
                🎙️ "{example}"
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="relative">
            <textarea
              rows={3}
              value={manualTranscript}
              onChange={(event) => setManualTranscript(event.target.value)}
              placeholder="Type transcript fallback here if microphone or provider is unavailable..."
              className="w-full rounded-3xl border border-input bg-white p-3 pr-28 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
            />
            <button
              type="button"
              onClick={() => handleParseText()}
              disabled={isBusy || !manualTranscript.trim()}
              className="absolute bottom-3 right-3 inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-white hover:bg-primary-dark disabled:opacity-60"
            >
              {parseTranscriptMutation.isPending ? (
                <RefreshCw className="size-3.5 animate-spin" />
              ) : (
                <Send className="size-3.5" />
              )}
              Parse
            </button>
          </div>

          {errorMsg ? (
            <div className="flex items-start gap-2 rounded-2xl border border-status-red/30 bg-status-red/5 p-3 text-sm text-status-red">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          ) : null}

          {activeDraft ? (
            <div className="rounded-3xl border border-primary/20 bg-primary-tint">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-primary/10 px-4 py-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">Structured draft proposal</p>
                  <p className="text-xs text-muted-foreground">
                    Review before applying to the receipt line form.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleReadBack}
                  disabled={isBusy}
                  className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-white px-3 py-1.5 text-xs font-semibold text-primary hover:bg-blue-50"
                >
                  <Volume2 className="size-3.5" />
                  {isPlayingAudio ? "Reading..." : "Read back"}
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-primary/10 text-[11px] font-bold uppercase tracking-wider text-muted-foreground bg-white/50">
                      <th className="px-4 py-2.5 whitespace-nowrap">Quantity</th>
                      <th className="px-4 py-2.5 whitespace-nowrap">State</th>
                      <th className="px-4 py-2.5 whitespace-nowrap">Condition note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeDraft.lines.map((line, index) => (
                      <tr
                        key={`${line.inventory_state}-${index}`}
                        className="border-b border-primary/10 hover:bg-white/40 transition-colors"
                      >
                        <td className="px-4 py-3 font-mono font-bold text-foreground">
                          {line.quantity}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-bold whitespace-nowrap ${stateClass(
                              line.inventory_state,
                            )}`}
                          >
                            {line.inventory_state.replaceAll("_", " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-foreground font-medium">
                          {line.condition_note || (
                            <span className="text-muted-foreground font-normal italic">None</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {activeDraft.warnings.length > 0 ? (
                <div className="mx-4 mt-3 rounded-2xl border border-primary/20 bg-white p-3 text-xs text-primary">
                  {activeDraft.warnings.join(" ")}
                </div>
              ) : null}

              <div className="flex flex-wrap justify-end gap-2 border-t border-primary/10 px-4 py-3">
                <button
                  type="button"
                  onClick={handleDiscard}
                  disabled={isBusy}
                  className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-white px-3 py-1.5 text-xs font-semibold text-primary hover:bg-blue-50 disabled:opacity-60"
                >
                  <Trash2 className="size-3.5" />
                  Discard
                </button>
                <button
                  type="button"
                  onClick={handleApply}
                  disabled={isBusy || activeDraft.lines.length === 0}
                  className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-1.5 text-xs font-semibold text-white hover:bg-primary-dark disabled:opacity-60"
                >
                  <CheckCircle2 className="size-3.5" />
                  Apply to receipt draft
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2 rounded-2xl bg-primary-tint p-3 text-xs leading-5 text-muted-foreground">
              <HelpCircle className="mt-0.5 size-4 shrink-0 text-primary" />
              <span>
                Manual entry stays available. Voice AI cannot complete receipts, adjust inventory,
                ship orders, or bypass barcode/UPC product identity.
              </span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
