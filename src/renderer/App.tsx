/**
 * AtlasTrinity - Main App Component
 * Premium Design System Integration
 */

import type * as React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AgentStatus from './components/AgentStatus.tsx';
import ChatPanel from './components/ChatPanel.tsx';
import CommandLine from './components/CommandLine.tsx';
import ExecutionLog from './components/ExecutionLog.tsx';
import MapView from './components/MapView';
import NeuralCore from './components/NeuralCore';

// Agent types
type AgentName = 'ATLAS' | 'TETYANA' | 'GRISHA' | 'SYSTEM' | 'USER';
type SystemState = 'IDLE' | 'PROCESSING' | 'EXECUTING' | 'VERIFYING' | 'ERROR';

interface LogEntry {
  id: string;
  timestamp: Date;
  agent: AgentName;
  message: string;
  type: 'info' | 'action' | 'success' | 'error' | 'voice';
}

interface ChatMessage {
  agent: AgentName;
  text: string;
  timestamp: Date;
  type?: 'text' | 'voice';
}

interface SystemMetrics {
  cpu: string;
  memory: string;
  net_up_val: string;
  net_up_unit: string;
  net_down_val: string;
  net_down_unit: string;
}

const API_BASE = 'http://127.0.0.1:8000';
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';

const RE_SAVED_TO_PNG = /Saved to: (.+\.png)/;
const RE_LOCATION = /Location: ([^\n]+)/;
const RE_CENTER = /Center: ([^\n]+)/;

const App: React.FC = () => {
  const [systemState, setSystemState] = useState<SystemState>('IDLE');
  const [activeAgent, setActiveAgent] = useState<AgentName>('ATLAS');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isVoiceEnabled, setIsVoiceEnabled] = useState(true);
  const [activeMode, setActiveMode] = useState<'STANDARD' | 'LIVE'>('STANDARD');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<Array<{ id: string; theme: string; saved_at: string }>>(
    [],
  );
  const [currentSessionId, setCurrentSessionId] = useState<string>('current_session');
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [metrics, setMetrics] = useState<SystemMetrics>({
    cpu: '0%',
    memory: '0.0GB',
    net_up_val: '0.0',
    net_up_unit: 'K/S',
    net_down_val: '0.0',
    net_down_unit: 'K/S',
  });
  const [isConnected, setIsConnected] = useState(false);

  // Map state
  const [viewMode, setViewMode] = useState<'NEURAL' | 'MAP'>('NEURAL');
  const [mapData, setMapData] = useState<{
    url?: string;
    type: 'STREET' | 'STATIC' | 'INTERACTIVE';
    location?: string;
    agentView?: {
      heading: number;
      pitch: number;
      fov: number;
      timestamp: string;
      lat?: number;
      lng?: number;
    } | null;
    distanceInfo?: {
      distance?: string;
      duration?: string;
      origin?: string;
      destination?: string;
    } | null;
  }>({ type: 'STATIC' });

  // Command dock auto-hide state
  const [isDockVisible, setIsDockVisible] = useState(true);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const showTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-hide timers: 1 second delay for both show and hide
  const DOCK_DELAY_MS = 1000;

  // Handle hover zone enter - schedule showing dock
  const handleHoverZoneEnter = useCallback(() => {
    // Clear any pending hide timer
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    // Schedule showing the dock after delay
    if (!(isDockVisible || showTimerRef.current)) {
      showTimerRef.current = setTimeout(() => {
        setIsDockVisible(true);
        showTimerRef.current = null;
      }, DOCK_DELAY_MS);
    }
  }, [isDockVisible]);

  // Handle hover zone leave - schedule hiding dock if not focused
  const handleHoverZoneLeave = useCallback(() => {
    // Clear any pending show timer
    if (showTimerRef.current) {
      clearTimeout(showTimerRef.current);
      showTimerRef.current = null;
    }
    // Schedule hiding the dock after delay (only if input is not focused)
    if (isDockVisible && !isInputFocused && !hideTimerRef.current) {
      hideTimerRef.current = setTimeout(() => {
        setIsDockVisible(false);
        hideTimerRef.current = null;
      }, DOCK_DELAY_MS);
    }
  }, [isDockVisible, isInputFocused]);

  // When input gets focused, cancel hide timer and ensure dock stays visible
  useEffect(() => {
    if (isInputFocused) {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
        hideTimerRef.current = null;
      }
      setIsDockVisible(true);
    }
  }, [isInputFocused]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (showTimerRef.current) clearTimeout(showTimerRef.current);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, []);

  // Set 'key' attribute on gmpx-api-loader via ref, as React consumes 'key' prop
  const loaderRef = useRef<HTMLElement>(null);
  useEffect(() => {
    if (loaderRef.current && GOOGLE_MAPS_API_KEY) {
      loaderRef.current.setAttribute('key', GOOGLE_MAPS_API_KEY);
    }
  }, []);

  // Add log entry
  const addLog = useCallback(
    (agent: AgentName, message: string, type: LogEntry['type'] = 'info') => {
      const entry: LogEntry = {
        id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
        agent,
        message,
        type,
      };
      setLogs((prev) => [...prev.slice(-100), entry]); // Keep last 100 entries

      // Auto-detect map updates in logs
      if (message.includes('Saved to:') && message.includes('.png')) {
        const pathMatch = message.match(RE_SAVED_TO_PNG);
        if (pathMatch?.[1]) {
          const filePath = pathMatch[1];
          // Convert local path to file:// URL for Electron display
          // Note: In some Electron setups you might need a custom protocol or webSecurity: false
          const fileUrl = `file://${filePath}`;
          const isStreet = message.toLowerCase().includes('street');

          setMapData({
            url: fileUrl,
            type: isStreet ? 'STREET' : 'STATIC',
            location: message.match(RE_LOCATION)?.[1] || message.match(RE_CENTER)?.[1],
          });
          setViewMode('MAP');
        }
      }

      // Auto-detect interactive map signal
      if (message.includes('🌐 INTERACTIVE_MAP_OPEN:')) {
        const query = message.replace('🌐 INTERACTIVE_MAP_OPEN:', '').trim();
        setMapData((prev) => {
          const newData = {
            type: 'INTERACTIVE' as const,
            location: query || 'INTERACTIVE_FEED',
          };
          if (prev.type === newData.type && prev.location === newData.location) return prev;
          return newData;
        });
        setViewMode('MAP');
      }
    },
    [],
  );

  const [currentTask, setCurrentTask] = useState<string>('');

  const fetchSessions = useCallback(async (retryCount = 0) => {
    try {
      const response = await fetch(`${API_BASE}/api/sessions`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setSessions(data);
    } catch (err) {
      if (retryCount < 5) {
        // Retry with exponential backoff if server is still starting
        const delay = 2 ** retryCount * 1000;
        // Only warn after some retries or it gets annoying
        if (retryCount > 2) {
          console.warn(
            `[BRAIN] Session fetch still failing, retrying in ${delay}ms... (Attempt ${retryCount + 1}/5)`,
          );
        }
        setTimeout(() => {
          void fetchSessions(retryCount + 1);
        }, delay);
      } else {
        // Final retry failed, log but don't spam
        if (!(err instanceof TypeError && err.message.includes('Failed to fetch'))) {
          console.error('[BRAIN] Failed to fetch sessions after retries:', err);
        }
      }
    }
  }, []);

  const pollState = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/state`);
      if (response.ok) {
        setIsConnected(true);
        const data = await response.json();
        if (data) {
          // Sync system state
          setSystemState(data.system_state || 'IDLE');
          setActiveAgent(data.active_agent || 'ATLAS');
          if (data.session_id) setCurrentSessionId(data.session_id);
          setCurrentTask(data.current_task || '');
          setActiveMode(data.active_mode || 'STANDARD');
          if (data.metrics) setMetrics(data.metrics);

          if (data.map_state) {
            const ms = data.map_state;
            const av = ms.agent_view;

            setMapData((prev) => {
              const newState = { ...prev };
              let changed = false;

              // Handle Agent View (Street View)
              if (av?.image_path) {
                const fileUrl = `file://${av.image_path}`;
                if (
                  prev.url !== fileUrl ||
                  prev.type !== 'STREET' ||
                  prev.agentView?.timestamp !== av.timestamp
                ) {
                  newState.url = fileUrl;
                  newState.type = 'STREET';
                  newState.location = `AGENT_VIEW @ ${av.heading}°`;
                  newState.agentView = {
                    heading: av.heading,
                    pitch: av.pitch,
                    fov: av.fov,
                    timestamp: av.timestamp,
                    lat: av.lat,
                    lng: av.lng,
                  };
                  changed = true;
                  // Auto-switch to map if new street view frame arrives
                  if (viewMode !== 'MAP') setViewMode('MAP');
                }
              }

              // Handle Distance Info & Map Triggers
              if (JSON.stringify(prev.distanceInfo) !== JSON.stringify(ms.distance_info)) {
                newState.distanceInfo = ms.distance_info;
                changed = true;
              }

              // Handle explicit "show map" signal from backend (e.g. after routing)
              if (ms.show_map && viewMode !== 'MAP') {
                setViewMode('MAP');
                // Ensure we have interactive type if not street view
                if (newState.type !== 'STREET') {
                  newState.type = 'INTERACTIVE';
                  newState.location = newState.location || 'INTERACTIVE_FEED';
                  changed = true;
                }
              }

              return changed ? newState : prev;
            });
          }

          if (data.logs) {
            setLogs(
              data.logs.map((l: LogEntry) => {
                let ts: Date;
                if (typeof l.timestamp === 'number') {
                  ts = new Date(l.timestamp * 1000);
                } else if (typeof l.timestamp === 'string') {
                  ts = new Date(l.timestamp);
                } else {
                  ts = new Date();
                }
                return { ...l, timestamp: ts };
              }),
            );
          }

          if (data.messages && data.messages.length > 0) {
            // Only update if message count changed to avoid flickering
            setChatHistory((prev) => {
              if (prev.length !== data.messages.length) {
                return data.messages.map(
                  (m: {
                    agent: AgentName;
                    text: string;
                    timestamp: number | string;
                    type: 'text' | 'voice';
                  }) => {
                    let ts: Date;
                    if (typeof m.timestamp === 'number') {
                      ts = new Date(m.timestamp * 1000);
                    } else if (typeof m.timestamp === 'string') {
                      ts = new Date(m.timestamp);
                    } else {
                      ts = new Date();
                    }
                    return { ...m, timestamp: ts };
                  },
                );
              }
              return prev;
            });
          }
        }
      }
    } catch (err) {
      setIsConnected(false);
      // SILENT during connection refused to clean up console
      if (
        err instanceof TypeError &&
        (err.message === 'Failed to fetch' ||
          err.message.includes('Failed to fetch') ||
          err.message.includes('NetworkError'))
      ) {
        // Do nothing, silence the console spam for connection issues
      } else {
        console.error('[BRAIN] Polling error:', err);
      }
    }
  }, [viewMode]);

  // Initialize & Poll State with dynamic interval
  // Faster polling (1s) during active tours, slower (3s) otherwise
  const isTourActive = Boolean(mapData.agentView);
  const pollInterval = isTourActive ? 1000 : 3000;

  // Robust startup sequence
  useEffect(() => {
    let mounted = true;
    let interval: NodeJS.Timeout;

    const waitForBackend = async (retryCount = 0) => {
      if (!mounted) return;

      try {
        // Simple health check before aggressive polling
        const res = await fetch(`${API_BASE}/api/health`);
        if (res.ok) {
          if (mounted) {
            console.log('[BRAIN] Backend connected. Starting synchronization.');
            setIsConnected(true);
            void pollState();
            void fetchSessions();
            interval = setInterval(() => {
              void pollState();
            }, pollInterval);
          }
          return;
        }
        throw new Error('Backend not ready');
      } catch {
        if (!mounted) return;

        // Exponential backoff with cap
        const delay = Math.min(1000 * 1.5 ** retryCount, 5000);
        console.log(`[BRAIN] Waiting for backend... (Attempt ${retryCount + 1})`);

        setTimeout(() => {
          void waitForBackend(retryCount + 1);
        }, delay);
      }
    };

    // Start looking for the brain after a short delay to allow Python to spin up
    const initialTimer = setTimeout(() => {
      void waitForBackend();
    }, 3000);

    return () => {
      mounted = false;
      clearTimeout(initialTimer);
      if (interval) clearInterval(interval);
    };
  }, [fetchSessions, pollState, pollInterval]);

  // Handle file drops
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // We can't easily pass files to CommandLine state from here without a context or prop.
    // However, if we drop on the app, we likely want to add them to the command line input.
    // For now, let's just log it or maybe focus the input.
    // A better approach would be to have selectedFiles lifted to App state, but
    // to keep changes localized, we might rely on the CommandLine's own drop zone
    // or just the paperclip for now if global drag-n-drop is too complex to wire up
    // without refactoring state.

    // Actually, looking at the plan: "Modify chat input to allow file selection".
    // "Implement a drag-and-drop area in the chat UI".
    // CommandLine component is the natural place for this state.
    // If we want global drop, we need to lift state.
    // Let's stick to the plan: CommandLine handles it.
    // But wait, CommandLine is instantiated here.

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      // We'll leave global drop for a future refactor to lift state.
      // For now, users can drop directly onto the expanded command line or click paperclip.
      console.log('Files dropped on app container:', e.dataTransfer.files);
    }
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Reveal dock immediately on drag
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    setIsDockVisible(true);
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      // Keep dock visible during drag
      if (!isDockVisible) {
        setIsDockVisible(true);
      }
    },
    [isDockVisible],
  );

  const handleCommand = useCallback(
    async (cmd: string, files: File[] = []) => {
      // 1. Log user action
      const fileMsg = files.length > 0 ? ` [${files.length} files]` : '';
      addLog('ATLAS', `Command: ${cmd}${fileMsg}`, 'action');
      setSystemState('PROCESSING');
      try {
        // Use FormData if files exist or just always for consistency now
        const formData = new FormData();
        formData.append('request', cmd);
        files.forEach((file) => {
          formData.append('files', file);
        });

        const response = await fetch(`${API_BASE}/api/chat`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) throw new Error(`Server Error: ${response.status}`);

        const data = await response.json();

        // 3. Handle Result
        if (data.status === 'completed' || data.status === 'success') {
          const result = data.result || data.response;
          // Safely handle object results by stringifying them
          let message = '';
          if (typeof result === 'string') {
            message = result;
          } else if (typeof result === 'object') {
            // Check if it's the specific step results array and format it nicely
            if (Array.isArray(result)) {
              const steps = result.filter((r: { success: boolean }) => r.success).length;
              message = `Task completed successfully: ${steps} steps executed.`;
            } else if (result.result) {
              message =
                typeof result.result === 'string' ? result.result : JSON.stringify(result.result);
            } else {
              message = JSON.stringify(result);
            }
          } else {
            message = String(result);
          }

          addLog('ATLAS', message, 'success');
          setSystemState('IDLE');
        } else {
          addLog('TETYANA', 'Task execution finished', 'info');
          setSystemState('IDLE');
        }
      } catch (error) {
        console.error(error);
        addLog('ATLAS', 'Failed to reach Neural Core. Is Python server running?', 'error');
        setSystemState('ERROR');
      }
    },
    [addLog],
  );

  const handleToggleVoice = useCallback(() => {
    setIsVoiceEnabled((prev) => !prev);
  }, []);

  const handleCloseMap = useCallback(() => setViewMode('NEURAL'), []);

  const handleNewSession = async () => {
    console.log('Starting new session...');
    try {
      const response = await fetch(`${API_BASE}/api/session/reset`, {
        method: 'POST',
      });
      if (response.ok) {
        const result = await response.json();
        // Clear local state
        setLogs([]);
        setChatHistory([]);
        if (result.session_id) setCurrentSessionId(result.session_id);
        void fetchSessions();
      }
    } catch (err) {
      console.error('Failed to reset session:', err);
    }
  };

  const handleRestoreSession = async (sessionId: string) => {
    console.log(`Restoring session: ${sessionId}`);
    try {
      const response = await fetch(`${API_BASE}/api/sessions/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (response.ok) {
        // Clear local state to force refresh from new session
        setLogs([]);
        setChatHistory([]);
        setCurrentSessionId(sessionId);
        setIsHistoryOpen(false);
        void pollState();
      }
    } catch (err) {
      console.error('Failed to restore session:', err);
    }
  };

  // Derived messages for ChatPanel - memoized to prevent unnecessary re-renders
  const chatMessages = useMemo(
    () =>
      chatHistory.map((m, idx) => ({
        id: `chat-${m.timestamp.getTime()}-${idx}`,
        agent: m.agent,
        text: m.text,
        timestamp: m.timestamp,
        type: m.type,
      })),
    [chatHistory],
  );

  return (
    <div
      className="app-container scanlines"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      role="application"
    >
      {/* Top Level Google Maps API Loader - Prevents 429 errors by staying mounted */}
      {GOOGLE_MAPS_API_KEY && (
        <div style={{ display: 'none' }}>
          <gmpx-api-loader
            // biome-ignore lint/suspicious/noExplicitAny: custom element ref needs any cast in some react versions
            ref={loaderRef as any}
            api-key={GOOGLE_MAPS_API_KEY}
            solution-channel="GMP_CDN_extended_v0.6.11"
            version="beta"
          ></gmpx-api-loader>
        </div>
      )}
      {/* Pulsing Borders */}
      <div className="pulsing-border top"></div>
      <div className="pulsing-border bottom"></div>
      <div className="pulsing-border left"></div>
      <div className="pulsing-border right"></div>

      {/* Starting Overlay */}
      {!isConnected && systemState === 'IDLE' && (
        <div className="fixed inset-0 z-[20000] flex items-center justify-center bg-black/80 backdrop-blur-md">
          <div className="flex flex-col items-center gap-6">
            <div className="w-16 h-16 border-t-2 border-r-2 border-[#00f2ff] rounded-full animate-spin"></div>
            <div className="flex flex-col items-center gap-2">
              <div className="text-[10px] tracking-[0.5em] uppercase text-[#00f2ff]/60 animate-pulse">
                Waiting for neural link...
              </div>
              <div className="text-[8px] tracking-[0.2em] uppercase text-[#00f2ff]/30 font-mono">
                Searching for Brain Core at {API_BASE}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Global Title Bar Controls (Positioned exactly near traffic lights) */}
      <div
        className="fixed flex items-center gap-2 pointer-events-auto"
        style={
          {
            top: '12px',
            left: '78px',
            WebkitAppRegion: 'no-drag',
            zIndex: 10001,
          } as React.CSSProperties
        }
      >
        <button
          onClick={() => {
            console.log('History clicked');
            setIsHistoryOpen(!isHistoryOpen);
          }}
          className={`titlebar-btn group ${isHistoryOpen ? 'active' : ''}`}
          title="Session History"
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="12 8 12 12 14 14"></polyline>
            <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"></path>
          </svg>
        </button>
        <button
          onClick={() => {
            console.log('New Session clicked');
            void handleNewSession();
          }}
          className="titlebar-btn group"
          title="New Session"
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
        <button
          onClick={() => {
            const nextMode = viewMode === 'NEURAL' ? 'MAP' : 'NEURAL';
            setViewMode(nextMode);
            // If switching to MAP and no specific feed is active, default to INTERACTIVE manual control
            if (nextMode === 'MAP' && !mapData.url && mapData.type !== 'INTERACTIVE') {
              setMapData({
                type: 'INTERACTIVE',
                location: 'INTERACTIVE_FEED',
              });
            }
          }}
          className={`titlebar-btn group ${viewMode === 'MAP' ? 'active' : ''}`}
          title="Toggle Map/Neural Core"
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
            <line x1="8" y1="2" x2="8" y2="18"></line>
            <line x1="16" y1="6" x2="16" y2="22"></line>
          </svg>
        </button>
      </div>

      {/* Left Panel - Execution Log */}
      <aside className="panel glass-panel left-panel relative">
        <ExecutionLog logs={logs} />

        {/* Session History Sidebar Overlay */}
        {isHistoryOpen && (
          <div
            className="absolute inset-0 z-50 backdrop-blur-xl border-r border-[#00e5ff]/20 animate-slide-in"
            style={{ backgroundColor: '#000000' }}
          >
            <div className="p-6 h-full flex flex-col">
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-[10px] tracking-[0.4em] uppercase font-bold text-[#00e5ff] drop-shadow-[0_0_5px_rgba(0,229,255,0.5)]">
                  Session History
                </h2>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      void handleNewSession();
                      setIsHistoryOpen(false);
                    }}
                    className="group flex items-center justify-center w-8 h-8 rounded-sm border transition-all duration-300 backdrop-blur-sm hover:scale-105 active:scale-95"
                    style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.6)',
                      borderColor: 'rgba(0, 229, 255, 0.4)',
                      boxShadow: '0 0 10px rgba(0, 229, 255, 0.1)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = '#00e5ff';
                      e.currentTarget.style.boxShadow = '0 0 15px rgba(0, 229, 255, 0.4)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(0, 229, 255, 0.4)';
                      e.currentTarget.style.boxShadow = '0 0 10px rgba(0, 229, 255, 0.1)';
                    }}
                    title="New Session"
                  >
                    <svg
                      width="10"
                      height="10"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#00e5ff"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="drop-shadow-[0_0_5px_rgba(0,229,255,0.8)]"
                    >
                      <line x1="12" y1="5" x2="12" y2="19"></line>
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                  </button>
                  <button
                    onClick={() => setIsHistoryOpen(false)}
                    className="group flex items-center justify-center w-8 h-8 rounded-sm border transition-all duration-300 backdrop-blur-sm hover:scale-105 active:scale-95"
                    style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.6)',
                      borderColor: 'rgba(0, 229, 255, 0.4)',
                      boxShadow: '0 0 10px rgba(0, 229, 255, 0.1)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = '#00e5ff';
                      e.currentTarget.style.boxShadow = '0 0 15px rgba(0, 229, 255, 0.4)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(0, 229, 255, 0.4)';
                      e.currentTarget.style.boxShadow = '0 0 10px rgba(0, 229, 255, 0.1)';
                    }}
                  >
                    <svg
                      width="10"
                      height="10"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#00e5ff"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="drop-shadow-[0_0_5px_rgba(0,229,255,0.8)]"
                    >
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </div>
              </div>

              <div
                className="flex-1 overflow-y-auto pr-2"
                style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
              >
                <style>{`
                  .no-scrollbar::-webkit-scrollbar {
                    display: none;
                  }
                `}</style>
                <div className="no-scrollbar h-full overflow-y-auto">
                  {sessions.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-[8px] uppercase tracking-widest text-[#00e5ff]/30 italic">
                      No history found
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3">
                      {sessions.map((s) => (
                        <button
                          key={s.id}
                          onClick={() => {
                            void handleRestoreSession(s.id);
                          }}
                          className="group p-3 border text-left transition-all duration-300 backdrop-blur-sm w-full relative overflow-hidden mb-3"
                          style={{
                            backgroundColor:
                              currentSessionId === s.id
                                ? 'rgba(0, 0, 0, 0.7)'
                                : 'rgba(0, 0, 0, 0.4)',
                            borderColor:
                              currentSessionId === s.id ? '#00e5ff' : 'rgba(0, 229, 255, 0.3)',
                            boxShadow:
                              currentSessionId === s.id
                                ? '0 0 15px rgba(0, 229, 255, 0.25)'
                                : 'none',
                          }}
                          onMouseEnter={(e) => {
                            if (currentSessionId !== s.id) {
                              e.currentTarget.style.borderColor = '#00e5ff';
                              e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
                              e.currentTarget.style.boxShadow = '0 0 10px rgba(0, 229, 255, 0.2)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (currentSessionId !== s.id) {
                              e.currentTarget.style.borderColor = 'rgba(0, 229, 255, 0.3)';
                              e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.4)';
                              e.currentTarget.style.boxShadow = 'none';
                            }
                          }}
                        >
                          <div
                            className="text-[9px] font-medium mb-1 truncate"
                            style={{
                              color: '#00e5ff',
                              textShadow: '0 0 5px rgba(0, 229, 255, 0.5)',
                            }}
                          >
                            {s.theme}
                          </div>
                          <div
                            className="text-[7px] truncate font-mono"
                            style={{ color: 'rgba(0, 229, 255, 0.6)' }}
                          >
                            {new Date(s.saved_at).toLocaleString()}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Center Panel: Neural Core / Map View */}
      <main
        className="panel center-panel relative overflow-hidden"
        style={{ pointerEvents: viewMode === 'MAP' ? 'none' : 'auto' }}
      >
        {/* Neural Core is always present, but minimized when map is active */}
        <NeuralCore state={systemState} activeAgent={activeAgent} minimized={viewMode === 'MAP'} />
      </main>

      {/* Right Panel: Chat Panel */}
      <aside className="panel glass-panel right-panel">
        <ChatPanel messages={chatMessages} />
      </aside>

      {/* Map View - Fixed overlay above all panels */}
      {viewMode === 'MAP' && (
        <div
          className="fixed z-[1000] animate-fade-in"
          style={{
            top: '32px',
            bottom: '24px',
            left: '129px' /* 2/3 overlap on left panel (388px - 388*2/3) */,
            right: '129px' /* 2/3 overlap on right panel */,
          }}
        >
          <MapView
            imageUrl={mapData.url}
            type={mapData.type}
            location={mapData.location}
            agentView={mapData.agentView}
            distanceInfo={mapData.distanceInfo}
            onClose={handleCloseMap}
          />
        </div>
      )}

      {/* Hover zone for auto-revealing command dock */}
      {/* biome-ignore lint/a11y/noStaticElementInteractions: Hover zone for dock */}
      <div
        className="command-dock-hover-zone"
        onMouseEnter={handleHoverZoneEnter}
        onMouseLeave={handleHoverZoneLeave}
      />

      {/* biome-ignore lint/a11y/noStaticElementInteractions: Command dock container */}
      <div
        className={`command-dock command-dock-floating ${isDockVisible ? 'visible' : 'hidden'}`}
        onMouseEnter={handleHoverZoneEnter}
        onMouseLeave={handleHoverZoneLeave}
      >
        <CommandLine
          onCommand={(cmd, files) => {
            void handleCommand(cmd, files);
          }}
          isVoiceEnabled={isVoiceEnabled}
          onToggleVoice={handleToggleVoice}
          isProcessing={['PLANNING', 'EXECUTING', 'VERIFYING', 'CHAT'].includes(systemState)}
          onFocusChange={setIsInputFocused}
        />
      </div>

      {/* Bottom Status Bar - Integrated with AgentStatus */}
      <div className="status-bar !p-0 !bg-transparent !border-none">
        <AgentStatus
          activeAgent={activeAgent}
          systemState={systemState}
          currentTask={currentTask}
          activeMode={activeMode}
          isConnected={isConnected}
          metrics={metrics}
        />
      </div>
    </div>
  );
};

export default App;

// Add global declarations for Google Maps Web Components to satisfy TypeScript
declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      'gmp-map': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        center?: string;
        zoom?: string;
        'rendering-type'?: string;
      };

      'gmpx-api-loader': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        key?: string;
        'solution-channel'?: string;
        version?: string;
      };

      'gmpx-place-picker': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement>,
        HTMLElement
      > & {
        placeholder?: string;
      };

      'gmp-advanced-marker': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement>,
        HTMLElement
      >;
    }
  }
}
