// Shared types for the Event page.

export type EventType = 'notification' | 'task' | 'system';
export type EventStatus = 'pending' | 'completed' | 'failed';

export interface Event {
  uuid: string;
  type: EventType;
  status: EventStatus;
  source: string;
  message: string;
  payload: Record<string, unknown>;
  timestamp: string; // ISO 8601
}
