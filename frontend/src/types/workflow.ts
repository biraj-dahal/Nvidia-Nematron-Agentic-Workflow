/**
 * Workflow and orchestrator types
 */

// Action type enumeration
export enum ActionType {
  ADD_NOTES = 'add_notes',
  CREATE_EVENT = 'create_event',
  FIND_SLOT = 'find_available_slot',
  UPDATE_EVENT = 'update_event',
}

// Meeting action to be executed
export interface MeetingAction {
  action_type: ActionType;
  calendar_event_id?: string;
  event_title?: string;
  event_date?: string; // ISO format YYYY-MM-DD
  notes?: string;
  duration_minutes: number;
  attendees?: string[];
  reasoning: string;
}

// Execution result
export interface ExecutionResult {
  timestamp: string; // ISO format
  status: 'success' | 'error' | 'warning';
  action_type: string;
  message: string;
  event_id?: string;
  technical_details?: string;
}

// Calendar event
export interface CalendarEvent {
  event_id: string;
  title: string;
  start: string; // ISO format
  end: string;
  description?: string;
  attendees?: string[];
}

// Orchestrator response
export interface OrchestratorResponse {
  planned_actions: MeetingAction[];
  execution_results: ExecutionResult[];
  summary: string;
  calendar_events_count: number;
  related_meetings_count: number;
}

// Log entry for execution details
export interface LogEntry {
  type: 'input' | 'processing' | 'api_call' | 'output' | 'timing' | 'error';
  timestamp: string; // ISO format or HH:MM:SS
  message: string;
  metadata?: {
    model?: string;
    tokens?: number;
    latency_ms?: number;
    duration_ms?: number;
    detail?: string;
    [key: string]: any;
  };
}

// Workflow SSE event types
export type WorkflowEventType = 'stage_start' | 'stage_complete' | 'connected' | 'heartbeat';

export interface WorkflowEvent {
  type: WorkflowEventType;
  agent?: string;
  timestamp?: string;
  description?: string;
  status?: string;
  message?: string;
  logs?: LogEntry[];
}

// Agent card state
export interface AgentCardState {
  agentName: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  description: string;
  logs: LogEntry[];
  startTime?: Date;
  endTime?: Date;
  expanded: boolean;
}

// Workflow visualization state
export interface WorkflowState {
  isRunning: boolean;
  currentAgent: string | null;
  completedAgents: string[];
  agentCards: AgentCardState[];
  progress: number; // 0-100
}

// Transcription result
export interface TranscriptionResult {
  transcription: string;
  error?: string;
}

// Recording state
export interface RecordingState {
  isRecording: boolean;
  audioUrl?: string;
  mimeType?: string;
  duration?: number;
  error?: string;
}

// Agent names in order of execution
export const AGENT_NAMES = [
  'Transcript Analyzer',
  'Research & Entity Extraction',
  'Calendar Context Fetch',
  'Related Meetings Finder',
  'Action Planner',
  'Decision Analyzer',
  'Risk Assessor',
  'Action Executor',
  'Summary Generator',
] as const;

export type AgentName = (typeof AGENT_NAMES)[number];

// API request/response types
export interface TranscribeRequest {
  audioFile: Blob;
}

export interface OrchestrateRequest {
  transcript: string;
  auto_execute: boolean;
}

// Settings
export interface AppSettings {
  autoExecute: boolean;
  theme: 'dark' | 'light';
  port?: number;
}
