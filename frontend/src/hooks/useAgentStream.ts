import { useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface AgentEvent {
  event_type: string;
  agent_name: string;
  payload: string;
  timestamp: string;
  incident_id: string;
}

export const useAgentStream = () => {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [currentIncidentId, setCurrentIncidentId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  const clearTrace = useCallback(() => {
    setEvents([]);
    setActiveAgent(null);
    setCurrentIncidentId(null);
  }, []);

  useEffect(() => {
    const eventSource = new EventSource(`${API_URL}/events`);

    eventSource.onopen = () => {
      setIsConnected(true);
      console.log('SSE connection opened to Aegis backend');
    };

    eventSource.onerror = (err) => {
      setIsConnected(false);
      console.error('SSE error:', err);
    };

    const handleEvent = (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data);
        const type = event.type;
        
        const sseEvent: AgentEvent = {
          event_type: type,
          agent_name: type === 'complete' ? 'orchestrator' : type,
          payload: typeof parsed === 'string' ? parsed : JSON.stringify(parsed, null, 2),
          timestamp: new Date().toISOString(),
          incident_id: parsed.incident_id || parsed.id || '',
        };

        setEvents((prev) => {
          // Avoid duplicate events if any
          if (prev.some(e => e.event_type === sseEvent.event_type && e.payload === sseEvent.payload)) {
            return prev;
          }
          return [...prev, sseEvent];
        });

        if (sseEvent.incident_id) {
          setCurrentIncidentId(sseEvent.incident_id);
        }

        if (type === 'complete') {
          setActiveAgent(null);
        } else {
          setActiveAgent(type);
        }
      } catch (e) {
        console.error('Error parsing SSE event:', e);
      }
    };

    // Register event listeners for each agent step
    eventSource.addEventListener('sentry', handleEvent);
    eventSource.addEventListener('sleuth', handleEvent);
    eventSource.addEventListener('medic', handleEvent);
    eventSource.addEventListener('scribe', handleEvent);
    eventSource.addEventListener('complete', handleEvent);

    return () => {
      eventSource.close();
    };
  }, []);

  return {
    events,
    activeAgent,
    currentIncidentId,
    isConnected,
    clearTrace,
  };
};
