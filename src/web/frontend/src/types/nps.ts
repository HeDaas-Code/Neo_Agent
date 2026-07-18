// Shared types for the NPS page.

export type NPSType = 'function' | 'tool' | 'workflow';

export interface NPSParam {
  key: string;
  value: string;
}

export interface NPS {
  uuid: string;
  name: string;
  description: string;
  nps_type: NPSType;
  params: NPSParam[];
  enabled: boolean;
  call_count: number;
  last_called_at: string | null; // ISO 8601 or null if never called
  created_at: string;
}

export interface NPSConfigFormValues {
  name: string;
  description: string;
  nps_type: NPSType;
  params: NPSParam[];
  enabled: boolean;
}
