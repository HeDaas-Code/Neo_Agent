/**
 * LogExporter - export log entries as TXT or NDJSON via Blob download.
 *
 * The component is purely presentational + serialization; it does not
 * know how the log list was filtered. The parent passes the array it
 * wants exported (typically the filtered view, so "what you see is
 * what you export").
 *
 * Output formats:
 *   - TXT:  one entry per line, "[timestamp] [level] [module] message"
 *   - JSON: NDJSON, `logs.map(JSON.stringify).join('\n')` — one JSON
 *           object per line, friendly to `jq` and log-shippers.
 *
 * antd 5 removed `Button.Group` in favor of `Space.Compact`; we use the
 * latter to match the recommended antd v5 idiom and stay consistent
 * with the rest of the codebase (NPSConfigDrawer).
 */

import React, { useCallback } from 'react';
import { Button, Space, message as antdMessage } from 'antd';
import { DownloadOutlined, CodeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { LogEntry } from './types';

export interface LogExporterProps {
  logs: LogEntry[];
  /** Filename prefix; default "debug". Final name is `${prefix}-YYYYMMDD-HHmmss.{txt,json}`. */
  filenamePrefix?: string;
  /** Optional click hook, fired after a successful export. */
  onExported?: (format: 'txt' | 'json', count: number) => void;
}

function downloadFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Defer revoke so Safari has a chance to start the download.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function formatLogLine(l: LogEntry): string {
  return `[${l.timestamp}] [${l.level}] [${l.module}] ${l.message}`;
}

function buildFilename(prefix: string, ext: 'txt' | 'json'): string {
  return `${prefix}-${dayjs().format('YYYYMMDD-HHmmss')}.${ext}`;
}

const LogExporter: React.FC<LogExporterProps> = ({
  logs,
  filenamePrefix = 'debug',
  onExported,
}) => {
  const guardEmpty = useCallback((): boolean => {
    if (logs.length === 0) {
      antdMessage.warning('没有可导出的日志');
      return false;
    }
    return true;
  }, [logs.length]);

  const onExportTxt = useCallback(() => {
    if (!guardEmpty()) return;
    const text = logs.map(formatLogLine).join('\n');
    downloadFile(
      buildFilename(filenamePrefix, 'txt'),
      text,
      'text/plain;charset=utf-8'
    );
    onExported?.('txt', logs.length);
  }, [logs, filenamePrefix, onExported, guardEmpty]);

  const onExportJson = useCallback(() => {
    if (!guardEmpty()) return;
    // NDJSON: one JSON object per line. Use plain JSON.stringify (no indent)
    // so each line is a single compact record, easy to stream / grep.
    const ndjson = logs.map((l) => JSON.stringify(l)).join('\n');
    downloadFile(
      buildFilename(filenamePrefix, 'json'),
      ndjson,
      'application/x-ndjson;charset=utf-8'
    );
    onExported?.('json', logs.length);
  }, [logs, filenamePrefix, onExported, guardEmpty]);

  return (
    <Space.Compact>
      <Button
        size="small"
        icon={<DownloadOutlined />}
        onClick={onExportTxt}
      >
        导出 TXT
      </Button>
      <Button
        size="small"
        icon={<CodeOutlined />}
        onClick={onExportJson}
      >
        导出 JSON
      </Button>
    </Space.Compact>
  );
};

export default LogExporter;
