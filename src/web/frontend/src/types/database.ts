// Shared types for the Database page.

export type ColumnType = 'string' | 'number' | 'datetime' | 'json' | 'boolean';

export interface Column {
  key: string;
  label: string;
  type: ColumnType;
  width?: number;
}

export type Row = Record<string, unknown> & { uuid?: string };

export interface TableInfo {
  rowCount: number;
  columnCount: number;
  sizeKB: number;
}

export interface TableData {
  name: string;
  info: TableInfo;
  columns: Column[];
  rows: Row[];
}

export interface DatabaseMock {
  tables: TableData[];
}
