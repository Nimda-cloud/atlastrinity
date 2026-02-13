import { useCallback, useState } from 'react';
import type {
  AgentName,
  ChatMessage,
  LogEntry,
  MapData,
  SystemMetrics,
  SystemState,
} from '../types';

const API_BASE = 'http://127.0.0.1:8000';

export const useBrainApi = () => {
  const [systemState, setSystemState] = useState<SystemState>('IDLE');
  const [activeAgent, setActiveAgent] = useState<AgentName>('ATLAS');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [metrics, setMetrics] = useState<SystemMetrics>({
    cpu: '0%',
    memory: '0.0GB',
    net_up_val: '0.0',
    net_up_unit: 'K/S',
    net_down_val: '0.0',
    net_down_unit: 'K/S',
  });
  const [isConnected, setIsConnected] = useState(false);
  const [mapData, setMapData] = useState<MapData>({ type: 'STATIC' });
  const [activeMode, setActiveMode] = useState<'STANDARD' | 'LIVE'>('STANDARD');
  const [currentTask, setCurrentTask] = useState<string>('');
  const [currentSessionId, setCurrentSessionId] = useState<string>('current_session');

  const addLog = useCallback(
    (agent: AgentName, message: string, type: LogEntry['type'] = 'info') => {
      const entry: LogEntry = {
        id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
        agent,
        message,
        type,
      };
      setLogs((prev) => [...prev.slice(-100), entry]);
    },
    [],
  );

  const pollState = useCallback(async (viewMode: 'NEURAL' | 'MAP') => {
    try {
      const response = await fetch(`${API_BASE}/api/state`);
      if (response.ok) {
        setIsConnected(true);
        const data = await response.json();
        if (data) {
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
                }
              }

              if (JSON.stringify(prev.distanceInfo) !== JSON.stringify(ms.distance_info)) {
                newState.distanceInfo = ms.distance_info;
                changed = true;
              }

              if (ms.show_map && viewMode !== 'MAP') {
                // This logic might need to be handled by the caller too
              }

              return changed ? newState : prev;
            });
          }

          if (data.logs) {
            setLogs(
              data.logs.map((l: { timestamp: string | number }) => ({
                ...l,
                timestamp:
                  typeof l.timestamp === 'number'
                    ? new Date(l.timestamp > 10000000000 ? l.timestamp : l.timestamp * 1000)
                    : new Date(l.timestamp),
              })),
            );
          }

          if (data.messages && data.messages.length > 0) {
            setChatHistory(
              data.messages.map((m: { timestamp: string | number }) => ({
                ...m,
                timestamp:
                  typeof m.timestamp === 'number'
                    ? new Date(m.timestamp > 10000000000 ? m.timestamp : m.timestamp * 1000)
                    : new Date(m.timestamp),
              })),
            );
          }
        }
      }
    } catch {
      setIsConnected(false);
    }
  }, []);

  const handleCommand = useCallback(
    async (cmd: string, files: File[] = []) => {
      addLog(
        'ATLAS',
        `Command: ${cmd}${files.length > 0 ? ` [${files.length} files]` : ''}`,
        'action',
      );
      setSystemState('PROCESSING');
      try {
        const formData = new FormData();
        formData.append('request', cmd);
        for (const file of files) {
          formData.append('files', file);
        }

        const response = await fetch(`${API_BASE}/api/chat`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) throw new Error(`Server Error: ${response.status}`);
        const data = await response.json();

        if (data.status === 'completed' || data.status === 'success') {
          const result = data.result || data.response;
          let message = '';
          if (typeof result === 'string') {
            message = result;
          } else if (typeof result === 'object') {
            if (Array.isArray(result)) {
              const steps = result.filter((r: { success?: boolean }) => r.success).length;
              message = `Task completed successfully: ${steps} steps executed.`;
            } else {
              message = result.result
                ? typeof result.result === 'string'
                  ? result.result
                  : JSON.stringify(result.result)
                : JSON.stringify(result);
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

  const handleNewSession = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/session/reset`, {
        method: 'POST',
      });
      if (response.ok) {
        const result = await response.json();
        setLogs([]);
        setChatHistory([]);
        if (result.session_id) setCurrentSessionId(result.session_id);
        return result.session_id;
      }
    } catch (err) {
      console.error('Failed to reset session:', err);
    }
    return null;
  };

  const handleRestoreSession = async (sessionId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/sessions/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (response.ok) {
        setLogs([]);
        setChatHistory([]);
        setCurrentSessionId(sessionId);
        await pollState('NEURAL'); // Refresh state after restore
        return true;
      }
    } catch (err) {
      console.error('Failed to restore session:', err);
    }
    return false;
  };

  return {
    systemState,
    setSystemState,
    activeAgent,
    logs,
    setLogs,
    chatHistory,
    setChatHistory,
    metrics,
    isConnected,
    setIsConnected,
    mapData,
    setMapData,
    currentTask,
    activeMode,
    currentSessionId,
    pollState,
    handleCommand,
    addLog,
    handleNewSession,
    handleRestoreSession,
  };
};
