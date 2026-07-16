// Mock data for the Database page.
// Only business tables are exposed. Internal SQLite tables
// (e.g. sqlite_master, sqlite_sequence) are NOT included.

import type { TableData, DatabaseMock } from '@/types/database';

export const DATABASE_WHITELIST: readonly string[] = [
  'entities',
  'entity_definitions',
  'long_term_memory',
  'life_state_daily',
  'creative_projects',
] as const;

const entities: TableData = {
  name: 'entities',
  info: {
    rowCount: 6,
    columnCount: 5,
    sizeKB: 12,
  },
  columns: [
    { key: 'uuid', label: 'UUID', type: 'string' },
    { key: 'name', label: 'Name', type: 'string' },
    { key: 'entity_type', label: 'Type', type: 'string' },
    { key: 'created_at', label: 'Created At', type: 'datetime' },
    { key: 'metadata', label: 'Metadata', type: 'json' },
  ],
  rows: [
    {
      uuid: 'ent-001',
      name: 'Neo',
      entity_type: 'agent',
      created_at: '2026-01-04 09:12:33',
      metadata: { version: '3.0.0', active: true },
    },
    {
      uuid: 'ent-002',
      name: 'Alice',
      entity_type: 'user',
      created_at: '2026-01-05 11:20:10',
      metadata: { tier: 'pro', joined_via: 'web' },
    },
    {
      uuid: 'ent-003',
      name: 'Project Atlas',
      entity_type: 'project',
      created_at: '2026-01-08 14:45:00',
      metadata: { tags: ['research', 'priority'], owner: 'Alice' },
    },
    {
      uuid: 'ent-004',
      name: 'Bob',
      entity_type: 'user',
      created_at: '2026-01-12 08:03:11',
      metadata: { tier: 'free' },
    },
    {
      uuid: 'ent-005',
      name: 'DailySummaryJob',
      entity_type: 'scheduler',
      created_at: '2026-01-15 22:30:00',
      metadata: { cron: '0 2 * * *', enabled: true },
    },
    {
      uuid: 'ent-006',
      name: 'Trinity',
      entity_type: 'agent',
      created_at: '2026-02-01 10:00:00',
      metadata: { role: 'analyst' },
    },
  ],
};

const entityDefinitions: TableData = {
  name: 'entity_definitions',
  info: {
    rowCount: 5,
    columnCount: 4,
    sizeKB: 4,
  },
  columns: [
    { key: 'uuid', label: 'UUID', type: 'string' },
    { key: 'entity_uuid', label: 'Entity UUID', type: 'string' },
    { key: 'definition_key', label: 'Key', type: 'string' },
    { key: 'definition_value', label: 'Value', type: 'string' },
  ],
  rows: [
    {
      uuid: 'ed-001',
      entity_uuid: 'ent-001',
      definition_key: 'persona',
      definition_value: 'Helpful, concise, technically rigorous.',
    },
    {
      uuid: 'ed-002',
      entity_uuid: 'ent-002',
      definition_key: 'timezone',
      definition_value: 'Asia/Shanghai',
    },
    {
      uuid: 'ed-003',
      entity_uuid: 'ent-003',
      definition_key: 'goal',
      definition_value: 'Build an autonomous long-running agent.',
    },
    {
      uuid: 'ed-004',
      entity_uuid: 'ent-005',
      definition_key: 'handler',
      definition_value: 'src.jobs.daily_summary',
    },
    {
      uuid: 'ed-005',
      entity_uuid: 'ent-006',
      definition_key: 'capabilities',
      definition_value: 'analysis, summarization, classification',
    },
  ],
};

const longTermMemory: TableData = {
  name: 'long_term_memory',
  info: {
    rowCount: 7,
    columnCount: 5,
    sizeKB: 28,
  },
  columns: [
    { key: 'uuid', label: 'UUID', type: 'string' },
    { key: 'agent_uuid', label: 'Agent', type: 'string' },
    { key: 'summary', label: 'Summary', type: 'string' },
    { key: 'importance', label: 'Importance', type: 'number' },
    { key: 'created_at', label: 'Created At', type: 'datetime' },
  ],
  rows: [
    {
      uuid: 'mem-001',
      agent_uuid: 'ent-001',
      summary: 'Alice prefers concise technical answers.',
      importance: 7,
      created_at: '2026-02-01 09:00:00',
    },
    {
      uuid: 'mem-002',
      agent_uuid: 'ent-001',
      summary: 'Project Atlas deadline: 2026-09-30.',
      importance: 9,
      created_at: '2026-02-05 14:21:08',
    },
    {
      uuid: 'mem-003',
      agent_uuid: 'ent-006',
      summary: 'Trinity should default to JSON output for analyses.',
      importance: 5,
      created_at: '2026-02-10 18:11:42',
    },
    {
      uuid: 'mem-004',
      agent_uuid: 'ent-001',
      summary: 'User dislikes emoji in formal responses.',
      importance: 6,
      created_at: '2026-02-15 11:02:30',
    },
    {
      uuid: 'mem-005',
      agent_uuid: 'ent-001',
      summary: 'Daily standup runs at 09:30 Asia/Shanghai.',
      importance: 8,
      created_at: '2026-03-01 08:45:00',
    },
    {
      uuid: 'mem-006',
      agent_uuid: 'ent-006',
      summary: 'Analyses should always include confidence scores.',
      importance: 7,
      created_at: '2026-03-12 10:33:17',
    },
    {
      uuid: 'mem-007',
      agent_uuid: 'ent-001',
      summary: 'User often works late; defer non-urgent notifications.',
      importance: 4,
      created_at: '2026-03-20 23:14:00',
    },
  ],
};

const lifeStateDaily: TableData = {
  name: 'life_state_daily',
  info: {
    rowCount: 5,
    columnCount: 4,
    sizeKB: 3,
  },
  columns: [
    { key: 'uuid', label: 'UUID', type: 'string' },
    { key: 'date', label: 'Date', type: 'string' },
    { key: 'mood_score', label: 'Mood', type: 'number' },
    { key: 'notes', label: 'Notes', type: 'string' },
  ],
  rows: [
    {
      uuid: 'lsd-001',
      date: '2026-06-29',
      mood_score: 7,
      notes: 'Productive morning, deep work on Atlas architecture.',
    },
    {
      uuid: 'lsd-002',
      date: '2026-06-30',
      mood_score: 5,
      notes: 'Tired. Skipped the gym.',
    },
    {
      uuid: 'lsd-003',
      date: '2026-07-01',
      mood_score: 8,
      notes: 'Long run, felt great. Shipped a hotfix.',
    },
    {
      uuid: 'lsd-004',
      date: '2026-07-02',
      mood_score: 6,
      notes: 'Meetings all day. Need focus time.',
    },
    {
      uuid: 'lsd-005',
      date: '2026-07-03',
      mood_score: 9,
      notes: 'Best writing session in weeks. Drafted chapter 12.',
    },
  ],
};

const creativeProjects: TableData = {
  name: 'creative_projects',
  info: {
    rowCount: 3,
    columnCount: 5,
    sizeKB: 6,
  },
  columns: [
    { key: 'uuid', label: 'UUID', type: 'string' },
    { key: 'title', label: 'Title', type: 'string' },
    { key: 'status', label: 'Status', type: 'string' },
    { key: 'word_count', label: 'Words', type: 'number' },
    { key: 'updated_at', label: 'Updated At', type: 'datetime' },
  ],
  rows: [
    {
      uuid: 'cp-001',
      title: 'The Last Lighthouse Keeper',
      status: 'active',
      word_count: 32450,
      updated_at: '2026-07-12 22:01:00',
    },
    {
      uuid: 'cp-002',
      title: 'A Brief History of Carbon',
      status: 'completed',
      word_count: 18200,
      updated_at: '2026-05-20 14:42:00',
    },
    {
      uuid: 'cp-003',
      title: 'Garden of Static',
      status: 'paused',
      word_count: 7820,
      updated_at: '2026-04-02 09:15:00',
    },
  ],
};

export const databaseMock: DatabaseMock = {
  tables: [entities, entityDefinitions, longTermMemory, lifeStateDaily, creativeProjects],
};

export const getTableByName = (name: string): TableData | undefined =>
  databaseMock.tables.find((t) => t.name === name);
