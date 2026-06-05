export interface LogEntry {
  timestamp: string;
  status: string;
}

export interface Member {
  id: number;
  name: string;
  status: string;
  updated_at: string;
  weekly_minutes?: number;
  recent_logs?: LogEntry[];
}

export interface Settings {
  show_duration: boolean;
  status_list: string;
}

export interface UpdateRequest {
  id: number;
  status: string;
}