/**
 * Schedule mock data (Stage C.2)
 *
 * 与 Python 后端 `models.Schedule` 字段保持一致:
 *   uuid / title / description / start_time / end_time
 *   priority (low|normal|high)
 *   schedule_type (personal|work|family)
 *   status (pending|confirmed|done)
 *   is_collaborative / collaborator_status
 */

export type SchedulePriority = 'low' | 'normal' | 'high';
export type ScheduleType = 'personal' | 'work' | 'family';
export type ScheduleStatus = 'pending' | 'confirmed' | 'done';
export type CollaboratorStatus = 'confirmed' | 'pending' | 'declined';

export interface Schedule {
  uuid: string;
  title: string;
  description: string;
  /** ISO 字符串 */
  start_time: string;
  end_time: string;
  priority: SchedulePriority;
  schedule_type: ScheduleType;
  status: ScheduleStatus;
  /** 是否为协作日程 (需要对方确认) */
  is_collaborative: boolean;
  /** 当 is_collaborative=true 时,对方的确认状态 */
  collaborator_status?: CollaboratorStatus;
  /** 协作人名称,仅 is_collaborative=true 时有值 */
  collaborator_name?: string;
}

/**
 * 辅助函数:返回 2026 年某月某日 ISO 字符串 (本地 09:00 / 10:30 等固定时间)。
 * 这样在 Calendar 视图中能保证 mock 数据落在可见的月份。
 */
function at(month: number, day: number, hour: number, minute = 0): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `2026-${pad(month)}-${pad(day)}T${pad(hour)}:${pad(minute)}:00.000Z`;
}

export const mockSchedules: Schedule[] = [
  {
    uuid: 'sch-001',
    title: 'Stage C.1 评审会议',
    description: '评审 Knowledge 页面 (列表 + 详情 + 图谱) 的实现。\n负责人:王晓',
    start_time: at(7, 13, 10, 0),
    end_time: at(7, 13, 11, 0),
    priority: 'high',
    schedule_type: 'work',
    status: 'confirmed',
    is_collaborative: true,
    collaborator_status: 'confirmed',
    collaborator_name: '王晓',
  },
  {
    uuid: 'sch-002',
    title: '周会 (团队)',
    description: '本周各模块进度同步,风险项对齐。',
    start_time: at(7, 14, 9, 30),
    end_time: at(7, 14, 10, 30),
    priority: 'normal',
    schedule_type: 'work',
    status: 'confirmed',
    is_collaborative: true,
    collaborator_status: 'confirmed',
    collaborator_name: 'Neo_Agent 全员',
  },
  {
    uuid: 'sch-003',
    title: '陪孩子打疫苗',
    description: '上午 9 点社区医院,记得带预防接种本。',
    start_time: at(7, 15, 9, 0),
    end_time: at(7, 15, 11, 0),
    priority: 'high',
    schedule_type: 'family',
    status: 'pending',
    is_collaborative: false,
  },
  {
    uuid: 'sch-004',
    title: '健身 (有氧)',
    description: '跑步 5km + 拉伸。',
    start_time: at(7, 13, 19, 0),
    end_time: at(7, 13, 20, 0),
    priority: 'low',
    schedule_type: 'personal',
    status: 'pending',
    is_collaborative: false,
  },
  {
    uuid: 'sch-005',
    title: 'CPRS 2026 论文初稿 deadline',
    description: 'Industrial Track demo 论文初稿提交。',
    start_time: at(7, 20, 23, 59),
    end_time: at(7, 21, 23, 59),
    priority: 'high',
    schedule_type: 'work',
    status: 'pending',
    is_collaborative: true,
    collaborator_status: 'pending',
    collaborator_name: '张明',
  },
  {
    uuid: 'sch-006',
    title: '读书时间 — 《Designing Data-Intensive Applications》',
    description: '第 7 章:事务。',
    start_time: at(7, 16, 21, 0),
    end_time: at(7, 16, 22, 30),
    priority: 'low',
    schedule_type: 'personal',
    status: 'confirmed',
    is_collaborative: false,
  },
  {
    uuid: 'sch-007',
    title: '客户需求对接 — NeoAI Co.',
    description: '与 NeoAI 沟通 Neo_Agent v0.5 的排期。',
    start_time: at(7, 17, 14, 0),
    end_time: at(7, 17, 15, 30),
    priority: 'high',
    schedule_type: 'work',
    status: 'pending',
    is_collaborative: true,
    collaborator_status: 'pending',
    collaborator_name: 'NeoAI 商务',
  },
  {
    uuid: 'sch-008',
    title: '家庭聚餐',
    description: '爸妈家,晚上 6 点。',
    start_time: at(7, 18, 18, 0),
    end_time: at(7, 18, 20, 0),
    priority: 'normal',
    schedule_type: 'family',
    status: 'confirmed',
    is_collaborative: false,
  },
];
