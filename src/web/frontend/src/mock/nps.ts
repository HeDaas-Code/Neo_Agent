import type { NPS } from '../types/nps';

const ts = (offsetMs: number): string => new Date(Date.now() + offsetMs).toISOString();

export const mockNPSList: NPS[] = [
  {
    uuid: 'nps-001',
    name: 'web_search',
    description: '调用外部搜索引擎，返回 Top 10 结果的标题/链接/摘要。',
    nps_type: 'tool',
    params: [
      { key: 'query', value: '' },
      { key: 'top_k', value: '10' },
    ],
    enabled: true,
    call_count: 1287,
    last_called_at: ts(-1000 * 60 * 4),
    created_at: ts(-1000 * 60 * 60 * 24 * 30),
  },
  {
    uuid: 'nps-002',
    name: 'code_interpreter',
    description: '在沙箱中执行 Python 代码片段并返回 stdout/stderr。',
    nps_type: 'function',
    params: [
      { key: 'language', value: 'python' },
      { key: 'code', value: '' },
    ],
    enabled: true,
    call_count: 642,
    last_called_at: ts(-1000 * 60 * 12),
    created_at: ts(-1000 * 60 * 60 * 24 * 25),
  },
  {
    uuid: 'nps-003',
    name: 'knowledge_query',
    description: '查询本地知识库，返回相关文档片段及相似度分数。',
    nps_type: 'function',
    params: [
      { key: 'query', value: '' },
      { key: 'top_k', value: '5' },
    ],
    enabled: true,
    call_count: 318,
    last_called_at: ts(-1000 * 60 * 60 * 2),
    created_at: ts(-1000 * 60 * 60 * 24 * 20),
  },
  {
    uuid: 'nps-004',
    name: 'daily_report_workflow',
    description: '工作流：拉取昨日对话 -> 总结 -> 推送邮件。',
    nps_type: 'workflow',
    params: [
      { key: 'date', value: 'YYYY-MM-DD' },
      { key: 'mail_to', value: 'team@example.com' },
    ],
    enabled: false,
    call_count: 27,
    last_called_at: ts(-1000 * 60 * 60 * 24 * 5),
    created_at: ts(-1000 * 60 * 60 * 24 * 60),
  },
  {
    uuid: 'nps-005',
    name: 'image_generator',
    description: '调用图像生成模型，返回图片 URL。',
    nps_type: 'tool',
    params: [
      { key: 'prompt', value: '' },
      { key: 'size', value: '1024x1024' },
    ],
    enabled: true,
    call_count: 94,
    last_called_at: ts(-1000 * 60 * 60 * 8),
    created_at: ts(-1000 * 60 * 60 * 24 * 15),
  },
  {
    uuid: 'nps-006',
    name: 'sql_executor',
    description: '在只读账号下执行 SELECT 语句并返回结果集。',
    nps_type: 'function',
    params: [
      { key: 'sql', value: '' },
      { key: 'max_rows', value: '100' },
    ],
    enabled: false,
    call_count: 11,
    last_called_at: null,
    created_at: ts(-1000 * 60 * 60 * 24 * 3),
  },
];
