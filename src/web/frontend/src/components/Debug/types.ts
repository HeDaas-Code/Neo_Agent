/**
 * Shared types for the Debug page and its sub-components.
 *
 * Kept in a leaf file (no React imports) so both the page and the
 * extracted components can import it without risking circular deps.
 */

export type LogLevel = 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | string;

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  module: string;
  message: string;
}
