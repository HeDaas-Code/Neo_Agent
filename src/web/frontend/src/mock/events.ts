import type { Event } from '../types/event';

// Helper: build an ISO timestamp relative to `now` (ms offset, optionally negative for past)
const ts = (offsetMs: number): string => new Date(Date.now() + offsetMs).toISOString();

export const mockEvents: Event[] = [
  {
    uuid: 'evt-0001',
    type: 'notification',
    status: 'completed',
    source: 'chat.service',
    message: '用户发起了新的对话',
    payload: { user_id: 'u-1001', session_id: 's-abc', content_preview: '你好，帮我总结一下...' },
    timestamp: ts(-1000 * 60 * 30), // 30 min ago
  },
  {
    uuid: 'evt-0002',
    type: 'task',
    status: 'completed',
    source: 'scheduler.worker',
    message: '定时任务执行成功: daily_report',
    payload: { task_id: 't-201', duration_ms: 1832, items_processed: 42 },
    timestamp: ts(-1000 * 60 * 22),
  },
  {
    uuid: 'evt-0003',
    type: 'system',
    status: 'failed',
    source: 'knowledge.ingest',
    message: '知识库索引失败: 文件格式不支持',
    payload: { file: 'manual.pdf', error_code: 'E_FORMAT', stack: 'UnsupportedFormatError at line 12' },
    timestamp: ts(-1000 * 60 * 15),
  },
  {
    uuid: 'evt-0004',
    type: 'task',
    status: 'pending',
    source: 'nps.executor',
    message: '等待调用 NPS: web_search',
    payload: { nps_uuid: 'nps-007', args: { query: 'Neo_Agent 文档' }, queued_at: ts(-1000 * 60 * 10) },
    timestamp: ts(-1000 * 60 * 10),
  },
  {
    uuid: 'evt-0005',
    type: 'notification',
    status: 'completed',
    source: 'chat.service',
    message: '工具调用: code_interpreter',
    payload: { tool: 'code_interpreter', args: { language: 'python', code: 'print(1+1)' }, result: 2 },
    timestamp: ts(-1000 * 60 * 7),
  },
  {
    uuid: 'evt-0006',
    type: 'system',
    status: 'completed',
    source: 'system.health',
    message: '健康检查通过',
    payload: { cpu: 0.23, memory: 0.41, disk: 0.55, uptime_s: 86421 },
    timestamp: ts(-1000 * 60 * 5),
  },
  {
    uuid: 'evt-0007',
    type: 'task',
    status: 'failed',
    source: 'creative.generator',
    message: '创意生成超时 (>30s)',
    payload: { prompt_id: 'p-991', timeout_ms: 30000, partial_result: '已生成 3/5 张图片' },
    timestamp: ts(-1000 * 60 * 3),
  },
  {
    uuid: 'evt-0008',
    type: 'notification',
    status: 'pending',
    source: 'chat.service',
    message: '用户上传了新文件',
    payload: { user_id: 'u-1042', filename: 'data.csv', size_bytes: 102400 },
    timestamp: ts(-1000 * 60 * 2),
  },
  {
    uuid: 'evt-0009',
    type: 'system',
    status: 'completed',
    source: 'database.backup',
    message: '数据库备份完成',
    payload: { backup_id: 'b-2026-07-13', size_mb: 312, duration_s: 47 },
    timestamp: ts(-1000 * 60 * 1),
  },
  {
    uuid: 'evt-0010',
    type: 'task',
    status: 'completed',
    source: 'debug.runner',
    message: '调试任务完成: 修复了循环引用问题',
    payload: { bug_id: 'bug-3301', fix_commit: 'abc1234', tests_passed: 12 },
    timestamp: ts(-1000 * 30), // 30s ago
  },
];

// Pool used to fabricate a new mock event every 5s (simulating WS push)
export const mockEventPool: Omit<Event, 'uuid' | 'timestamp'>[] = [
  {
    type: 'notification',
    status: 'pending',
    source: 'chat.service',
    message: '新消息到达',
    payload: { user_id: 'u-1050', session_id: 's-xyz' },
  },
  {
    type: 'task',
    status: 'pending',
    source: 'scheduler.worker',
    message: '定时任务已派发',
    payload: { task_id: 't-202', job: 'hourly_sync' },
  },
  {
    type: 'system',
    status: 'completed',
    source: 'system.health',
    message: '心跳正常',
    payload: { ping_ms: 18 },
  },
  {
    type: 'notification',
    status: 'completed',
    source: 'nps.executor',
    message: 'NPS 调用成功',
    payload: { nps_uuid: 'nps-007', duration_ms: 213 },
  },
];
