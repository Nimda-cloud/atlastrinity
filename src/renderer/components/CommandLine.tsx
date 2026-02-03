/**
 * CommandLine - Bottom command input with integrated controls
 * Smart STT with speech type analysis
 */

import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';

// Speech types from backend
type SpeechType = 'same_user' | 'new_phrase' | 'noise' | 'other_voice' | 'silence' | 'off_topic';

interface SmartSTTResponse {
  text: string;
  speech_type: SpeechType;
  confidence: number;
  combined_text: string;
  should_send: boolean;
  is_continuation: boolean;
}

interface CommandLineProps {
  onCommand: (command: string, files?: File[]) => void;
  isVoiceEnabled?: boolean;
  onToggleVoice?: () => void;
  isProcessing?: boolean;
  onFocusChange?: (focused: boolean) => void;
}

declare global {
  interface Window {
    volumeChecker: NodeJS.Timeout | number | null;
  }
}

const CommandLine: React.FC<CommandLineProps> = ({
  onCommand,
  isVoiceEnabled = true,
  onToggleVoice,
  isProcessing,
  onFocusChange,
}) => {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [sttStatus, setSttStatus] = useState<string>(''); // For STT status display
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]); // New file state

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null); // Ref for hidden file input
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const silenceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pendingTextRef = useRef<string>(''); // Accumulated text
  const isListeningRef = useRef<boolean>(false);
  const streamRef = useRef<MediaStream | null>(null);
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const maxVolumeRef = useRef<number>(0); // For simple VAD
  const audioContextRef = useRef<AudioContext | null>(null);
  const lastSkippedChunkRef = useRef<Blob | null>(null); // Pre-buffer for context

  // auto-shrink
  useEffect(() => {
    // Reading input to ensure it's used as a trigger for linter
    if (textareaRef.current) {
      if (input.length >= 0) {
        // Trigger height check
        textareaRef.current.style.height = 'auto'; // Temporarily reset height to get accurate scrollHeight
        const scrollHeight = textareaRef.current.scrollHeight;
        const newHeight = Math.min(scrollHeight, 200);
        textareaRef.current.style.height = `${newHeight}px`;
      }
    }
  }, [input]);

  // Stop listening
  const stopListening = useCallback(() => {
    isListeningRef.current = false;
    setIsListening(false);
    setSttStatus('');

    if (window.volumeChecker) {
      clearInterval(window.volumeChecker as number);
      window.volumeChecker = null;
    }

    if (recordingIntervalRef.current) {
      clearTimeout(recordingIntervalRef.current);
      recordingIntervalRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }

    if (streamRef.current) {
      for (const track of streamRef.current.getTracks()) {
        track.stop();
      }
      streamRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close().catch(console.error);
      audioContextRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopListening();
    };
  }, [stopListening]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (input.trim() || selectedFiles.length > 0) {
      onCommand(input.trim(), selectedFiles);
      setInput('');
      setSelectedFiles([]); // Clear files after send
      if (fileInputRef.current) fileInputRef.current.value = ''; // Reset input
      pendingTextRef.current = '';
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Schedule auto-send after silence
  // IMPORTANT: This function must be defined BEFORE handleSTTResponse
  const scheduleSend = useCallback(() => {
    // Reset previous timer
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
    }

    silenceTimeoutRef.current = setTimeout(() => {
      const textToSend = pendingTextRef.current.trim();
      const filesToSend = selectedFiles;

      if (textToSend || filesToSend.length > 0) {
        setSttStatus('🚀 Sending...');
        onCommand(textToSend, filesToSend);
        setInput('');
        setSelectedFiles([]);
        if (fileInputRef.current) fileInputRef.current.value = '';
        pendingTextRef.current = '';

        // Instant resume of "Listening" status since Full Duplex works
        if (isListeningRef.current) {
          setSttStatus('🎙️ Listening...');
        } else {
          setSttStatus('');
        }

        if (textareaRef.current) textareaRef.current.style.height = 'auto';
      }
    }, 8000); // 8 seconds of silence before sending (aligned with backend)
  }, [onCommand, selectedFiles]); // Added selectedFiles dependency

  // Handle Smart STT response
  const handleSTTResponse = useCallback(
    (data: SmartSTTResponse) => {
      const { speech_type, combined_text, text, should_send } = data;

      // If server explicitly says to send (e.g. long pause on server)
      if (should_send && combined_text.trim()) {
        pendingTextRef.current = combined_text;
        // Actually better to just force timer expiration
        if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
        const textToSend = combined_text.trim();
        setSttStatus('🚀 Sending (Server Trigger)...');
        onCommand(textToSend, selectedFiles);
        setInput('');
        setSelectedFiles([]);
        if (fileInputRef.current) fileInputRef.current.value = '';
        pendingTextRef.current = '';
        if (textareaRef.current) textareaRef.current.style.height = 'auto';
        if (isListeningRef.current) {
          setSttStatus('🎙️ Listening...');
        }
        return;
      }

      switch (speech_type) {
        case 'silence':
          if (isListeningRef.current) {
            setSttStatus('Mw... (Silence)');
          }
          // On silence send accumulated text
          if (pendingTextRef.current.trim()) {
            scheduleSend();
          }
          break;

        case 'noise':
          // setSttStatus('🔊 ...'); // Less intrusive status for noise
          break;

        case 'other_voice':
          setSttStatus('👤 Other Voice');
          break;

        case 'off_topic':
          setSttStatus('💬 ...');
          break;

        case 'same_user':
        case 'new_phrase':
          // Update text
          if (text?.trim()) {
            pendingTextRef.current = combined_text;
            setInput(combined_text);
            setSttStatus(`✅ ${text.slice(0, 30)}...`);

            // Restart send timer
            scheduleSend();
          } else {
            setSttStatus('✅ ...');
          }
          break;

        default:
          // console.warn('Unknown speech type:', speech_type);
          break;
      }
    },
    [scheduleSend, onCommand, selectedFiles],
  );

  // Send audio to smart STT
  const processAudioChunk = useCallback(
    async (audioBlob: Blob) => {
      // Determine file extension
      let fileExtension = 'wav';
      if (audioBlob.type.includes('webm')) {
        fileExtension = 'webm';
      } else if (audioBlob.type.includes('ogg')) {
        fileExtension = 'ogg';
      }

      const formData = new FormData();
      formData.append('audio', audioBlob, `recording.${fileExtension}`);
      formData.append('previous_text', pendingTextRef.current);

      try {
        const response = await fetch('http://127.0.0.1:8000/api/stt/smart', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const data: SmartSTTResponse = await response.json();
          handleSTTResponse(data);
        } else {
          const errorText = await response.text();
          console.error('❌ STT server error:', response.status, response.statusText, errorText);
          setSttStatus('❌ STT Error');
        }
      } catch (error) {
        if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
          setSttStatus('🔌 Connecting...');
        } else {
          console.error('❌ Smart STT error:', error);
          setSttStatus('❌ Connection Error');
        }
      }
    },
    [handleSTTResponse],
  );

  // Recording cycle
  const startRecordingCycle = useCallback(() => {
    if (!streamRef.current?.active || !isListeningRef.current) return;

    // Force WAV
    let mimeType = 'audio/webm';
    if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
      mimeType = 'audio/webm;codecs=opus';
    } else if (MediaRecorder.isTypeSupported('audio/wav')) {
      mimeType = 'audio/wav';
    }

    const mediaRecorder = new MediaRecorder(streamRef.current, { mimeType });
    mediaRecorderRef.current = mediaRecorder;
    audioChunksRef.current = [];
    maxVolumeRef.current = 0; // Reset before new chunk

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunksRef.current.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      // Simple VAD: if too quiet, don't send
      if (maxVolumeRef.current < 12) {
        if (isListeningRef.current) {
          setSttStatus('🔇 Silence...');
        }
        // Save as context for next chunk if needed
        if (audioChunksRef.current.length > 0) {
          lastSkippedChunkRef.current = new Blob(audioChunksRef.current, { type: mimeType });
        }
      } else if (audioChunksRef.current.length > 0) {
        // Speech detected!
        if (lastSkippedChunkRef.current) {
          processAudioChunk(lastSkippedChunkRef.current).catch((err) =>
            console.error('Error sending pre-buffer:', err),
          );
          lastSkippedChunkRef.current = null;
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        processAudioChunk(audioBlob).catch(console.error);
      }

      if (isListeningRef.current && streamRef.current?.active) {
        startRecordingCycle();
      }
    };

    mediaRecorder.start();

    recordingIntervalRef.current = setTimeout(() => {
      if (mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
    }, 2000);
  }, [processAudioChunk]);

  // Handle mic errors
  const handleMicError = (error: unknown) => {
    if (error instanceof DOMException) {
      switch (error.name) {
        case 'NotFoundError':
        case 'DevicesNotFoundError':
          alert(
            '❌ Microphone not found\n\nCheck:\n• Microphone connected\n• Microphone enabled in system',
          );
          break;
        case 'NotAllowedError':
        case 'PermissionDeniedError':
          alert('❌ Access blocked\n\nAllow access to microphone');
          break;
        case 'NotReadableError':
        case 'TrackStartError':
          alert('❌ Microphone busy\n\nClose other apps');
          break;
        default:
          alert(`❌ Error: ${error.message}`);
      }
    }
  };

  // Start listening
  const startListening = async () => {
    isListeningRef.current = true;
    setIsListening(true);
    setSttStatus('⌛ Init...');

    try {
      if (!isVoiceEnabled && onToggleVoice) {
        onToggleVoice();
      }

      let stream = streamRef.current;
      if (!stream || !stream.active) {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: false,
            autoGainControl: true,
            sampleRate: 48000,
          },
        });

        if (!isListeningRef.current) {
          for (const track of stream.getTracks()) {
            track.stop();
          }
          return;
        }

        streamRef.current = stream;

        const audioContext = new AudioContext();
        audioContextRef.current = audioContext;
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        const checkVolume = () => {
          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          analyser.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
          if (average > maxVolumeRef.current) {
            maxVolumeRef.current = average;
          }
        };

        const volumeChecker = setInterval(checkVolume, 100);
        window.volumeChecker = volumeChecker;
      }

      setSttStatus('🎙️ Listening...');
      startRecordingCycle();
    } catch (error) {
      console.error('❌ Microphone access error:', error);
      isListeningRef.current = false;
      setIsListening(false);
      setSttStatus('');
      handleMicError(error);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  // File handling
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles((prev) => [...prev, ...filesArray]);
      e.target.value = ''; // Reset input to allow selecting same file again
      if (textareaRef.current) textareaRef.current.focus();
    }
  };

  const handleContainerDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files);
      setSelectedFiles((prev) => [...prev, ...filesArray]);
      if (textareaRef.current) textareaRef.current.focus();
    }
  }, []);

  const handleContainerDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <section
      className="command-line-container font-mono flex flex-col gap-1 w-full"
      onDrop={handleContainerDrop}
      onDragOver={handleContainerDragOver}
      aria-label="Command Input Area"
    >
      {/* File Preview Zone */}
      {selectedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 px-3 pb-1">
          {selectedFiles.map((file, idx) => (
            <div
              key={`${file.name}-${idx}`}
              className="flex items-center gap-2 bg-[#00f2ff]/10 border border-[#00f2ff]/30 rounded px-2 py-1 text-[10px]"
            >
              <span className="text-[#00f2ff] truncate max-w-[150px]">{file.name}</span>
              <button
                type="button"
                onClick={() => removeFile(idx)}
                className="text-[#00f2ff]/60 hover:text-[#00f2ff]"
                title="Remove file"
              >
                <svg
                  width="10"
                  height="10"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-start gap-2 pt-2 bg-transparent pb-0 w-full">
        {/* Input Field with STT Status in the bottom-left */}
        <div className="flex-1 relative min-w-0">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => onFocusChange?.(true)}
            onBlur={() => onFocusChange?.(false)}
            placeholder="ENTER_CORE_COMMAND..."
            className="command-textarea-extended"
            spellCheck={false}
            rows={1}
          />
          {/* Status Indicators - Bottom Left */}
          <div className="absolute left-3 bottom-2 flex items-center gap-2 pointer-events-none">
            {(isProcessing || sttStatus) && (
              <span
                className={`text-[9px] tracking-wider animate-pulse ${isProcessing ? 'text-amber-400' : 'text-cyan-400/70'}`}
              >
                {isProcessing ? '🤔 Thinking...' : sttStatus}
              </span>
            )}
            <span className="text-blue-500/20 text-[9px] tracking-widest">
              {input.length > 0 || selectedFiles.length > 0 ? 'ENTER ' : ''}⏎
            </span>
          </div>
        </div>

        {/* Right Controls - Vertical Stack */}
        <div className="flex flex-col gap-2 items-center">
          {/* Paperclip Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="control-btn"
            title="Attach File"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
            </svg>
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            multiple
          />

          {/* Voice Toggle */}
          <button
            type="button"
            onClick={onToggleVoice}
            className={`control-btn ${isVoiceEnabled ? 'active' : ''}`}
            title="Toggle Voice (TTS)"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              {isVoiceEnabled ? (
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
              ) : (
                <line x1="23" y1="9" x2="17" y2="15"></line>
              )}
            </svg>
          </button>

          {/* STT/Mic Button */}
          <button
            type="button"
            onClick={toggleListening}
            className={`control-btn ${isListening ? 'listening' : ''}`}
            title="Toggle Smart Mic (STT)"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {isListening ? (
                <>
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                  <line x1="12" y1="19" x2="12" y2="23"></line>
                  <line x1="8" y1="23" x2="16" y2="23"></line>
                </>
              ) : (
                <>
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                  <line x1="12" y1="19" x2="12" y2="23"></line>
                  <line x1="8" y1="23" x2="16" y2="23"></line>
                  <line x1="1" y1="1" x2="23" y2="23" strokeOpacity="1"></line>
                </>
              )}
            </svg>
          </button>

          {/* Send Button */}
          <button
            type="button"
            onClick={() => handleSubmit()}
            disabled={!input.trim() && selectedFiles.length === 0}
            className={`send-btn ${input.trim() || selectedFiles.length > 0 ? 'active' : ''}`}
            title="Send Command (Enter)"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ transform: 'rotate(45deg) translateY(-2px) translateX(2px)' }}
            >
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    </section>
  );
};

export default CommandLine;
