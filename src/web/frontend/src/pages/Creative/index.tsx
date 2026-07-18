/**
 * Creative 页面 - 长期创作项目管理。
 *
 * 数据源：后端 /api/creative/* REST 端点（src/web/backend/api/creative.py）。
 * - 列表：GET  /api/creative/projects?status=&limit=50
 * - 详情：GET  /api/creative/projects/{uuid}
 * - 续写：POST /api/creative/projects/{uuid}/advance
 * 续写进度通过 /ws/events 上的 'creative_progress' 事件实时推送。
 *
 * UI 状态：
 * - listLoading：列表加载中
 * - detailLoading：详情加载中
 * - listError / detailError：分别为列表 / 详情加载失败
 * - isContinuing：续写提交中
 *
 * 字段映射（后端 → 前端 UI 期望）：
 *   current_chars      → word_count（后端已做派生；前端保留 word_count 字段以兼容 UI）
 *   chapter_count      → 由 story_bible.chapters.length 渲染
 *   status (drafting/finished) → 归一化为 UI 已知 active/completed/paused，未知状态按 'paused' 显示
 *   created_at / updated_at（ISO with T） → formatDateTime 转 'YYYY-MM-DD HH:mm'
 *   story_bible        → 详情接口填充；列表接口为 null，点击列表项时按需拉取
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Layout,
  List,
  Card,
  Input,
  Select,
  Space,
  Tag,
  Typography,
  Button,
  Empty,
  App as AntdApp,
  Popconfirm,
  Descriptions,
  Skeleton,
  Spin,
  Alert,
} from 'antd';
import {
  SearchOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  PlusOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import * as creativeApi from '../../api/creative';
import type { CreativeProject, CreativeProjectStatus } from '@/types/creative';
import { useWebSocket } from '../../hooks/useWebSocket';
import StoryBibleViewer from '@/components/StoryBibleViewer';

const { Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;

// UI 显式支持的状态；未知状态回落到 'paused'。
const STATUS_META: Record<CreativeProjectStatus, { color: string; label: string }> = {
  active: { color: 'green', label: 'Active' },
  completed: { color: 'blue', label: 'Completed' },
  paused: { color: 'orange', label: 'Paused' },
  drafting: { color: 'cyan', label: 'Drafting' },
  finished: { color: 'blue', label: 'Finished' },
};

// 归一化后端返回的 status 到前端展示。未知值降级为 'paused'。
const normalizeStatus = (s: string): CreativeProjectStatus => {
  if (s === 'active' || s === 'completed' || s === 'paused' || s === 'drafting' || s === 'finished') {
    return s;
  }
  return 'paused';
};

const getStatusMeta = (s: string) => STATUS_META[normalizeStatus(s)];

const formatDateTime = (s: string): string => {
  if (!s) return '-';
  // 后端返回 ISO 8601：'YYYY-MM-DDTHH:mm:ss[.ffffff]'
  // 前端期望：'YYYY-MM-DD HH:mm'。
  return s.replace('T', ' ').slice(0, 16);
};

const formatRelative = (s: string): string => {
  if (!s) return '-';
  // 既兼容 ISO 字符串（'T' 分隔）也兼容 'YYYY-MM-DD HH:mm:ss'（' ' 分隔）。
  const norm = s.includes('T') ? s : s.replace(' ', 'T');
  const then = new Date(norm).getTime();
  if (Number.isNaN(then)) return s;
  const diff = Date.now() - then;
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} mo ago`;
  return `${Math.floor(months / 12)} y ago`;
};

// /ws/events 端点 URL 解析（与 Debug 页保持一致策略）
const DEFAULT_EVENTS_URL = 'ws://localhost:8000/ws/events';
const resolveEventsUrl = (): string => {
  if (typeof window === 'undefined') return DEFAULT_EVENTS_URL;
  const isDev = Boolean((import.meta as any)?.env?.DEV);
  if (isDev) return DEFAULT_EVENTS_URL;
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/events`;
};

const CreativePage: React.FC = () => {
  const { message } = AntdApp.useApp();
  const [statusFilter, setStatusFilter] = useState<CreativeProjectStatus | 'all'>('all');
  const [search, setSearch] = useState('');
  const [projects, setProjects] = useState<CreativeProject[]>([]);
  const [selectedUuid, setSelectedUuid] = useState<string>('');

  const [listLoading, setListLoading] = useState<boolean>(true);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [isContinuing, setIsContinuing] = useState<boolean>(false);

  // 防止组件卸载后写状态
  const mountedRef = useRef<boolean>(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // ============== 列表加载 ==============
  const loadList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const resp = await creativeApi.listProjects(undefined, 50);
      if (!mountedRef.current) return;
      setProjects(resp.projects || []);
      // 默认选中第一条（如果当前没有选中项）
      setSelectedUuid((prev) => prev || resp.projects?.[0]?.uuid || '');
    } catch (err) {
      if (!mountedRef.current) return;
      const msg = err instanceof Error ? err.message : String(err);
      setListError(msg);
      message.error(`加载创作项目失败：${msg}`);
    } finally {
      if (mountedRef.current) setListLoading(false);
    }
  }, [message]);

  // 首次挂载：加载列表
  useEffect(() => {
    loadList();
  }, [loadList]);

  // ============== 详情加载 ==============
  const loadDetail = useCallback(
    async (uuid: string) => {
      if (!uuid) return;
      setDetailLoading(true);
      setDetailError(null);
      try {
        const detail = await creativeApi.getProject(uuid);
        if (!mountedRef.current) return;
        // 把详情合并进列表项（保留其他项）
        setProjects((prev) => prev.map((p) => (p.uuid === uuid ? detail : p)));
      } catch (err) {
        if (!mountedRef.current) return;
        const msg = err instanceof Error ? err.message : String(err);
        setDetailError(msg);
        // 404 不弹错误（详情仅是 Story Bible 缺失）
        if (!msg.includes('404') && !msg.toLowerCase().includes('not found')) {
          message.error(`加载项目详情失败：${msg}`);
        }
      } finally {
        if (mountedRef.current) setDetailLoading(false);
      }
    },
    [message],
  );

  // 选中项变化时：拉详情（仅当详情尚未就绪或与列表版本不同时）
  useEffect(() => {
    if (!selectedUuid) return;
    const existing = projects.find((p) => p.uuid === selectedUuid);
    // 列表接口不返回 story_bible，需要按需拉详情
    if (!existing || !existing.story_bible) {
      loadDetail(selectedUuid);
    }
  }, [selectedUuid, projects, loadDetail]);

  // ============== 实时事件：续写进度 ==============
  const handleWsMessage = useCallback(
    (data: any) => {
      // /ws/events 推过来的帧：
      //   { type: 'event', channel, event_type, payload }
      if (!data || typeof data !== 'object') return;
      const eventType = data.event_type;
      if (eventType !== 'creative_progress') return;
      const payload = data.payload || {};
      const projectUuid: string | undefined = payload.project_uuid;
      if (!projectUuid) return;

      const status = String(payload.status || '');
      // 队列开始 / 失败 / 异步进度，都触发一次详情刷新
      if (
        status === 'queued' ||
        status === 'advanced' ||
        status === 'created' ||
        status === 'deleted' ||
        status === 'failed' ||
        status === 'completed'
      ) {
        if (mountedRef.current) {
          // 静默刷新列表 + 详情（避免弹错）
          loadList();
          if (projectUuid === selectedUuid) {
            loadDetail(projectUuid);
          }
        }
        if (status === 'completed' && payload.message) {
          message.success(String(payload.message));
        } else if (status === 'failed') {
          message.error(`续写失败：${payload.message || '未知错误'}`);
        }
      }
    },
    [loadList, loadDetail, selectedUuid, message],
  );

  useWebSocket(resolveEventsUrl(), { onMessage: handleWsMessage });

  // ============== 过滤 ==============
  const filteredProjects = useMemo(() => {
    const q = search.trim().toLowerCase();
    return projects.filter((p) => {
      if (statusFilter !== 'all' && p.status !== statusFilter) return false;
      if (q && !p.title.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [projects, statusFilter, search]);

  // 当前选中项（可能尚未拉详情）
  const current = selectedUuid
    ? projects.find((p) => p.uuid === selectedUuid)
    : undefined;

  // ============== 行为 ==============

  /**
   * 续写：先调 POST /api/creative/projects/{uuid}/advance，
   * 异步模式下后端会通过 /ws/events 推送 creative_progress 事件。
   */
  const handleContinue = async () => {
    if (!current) return;
    setIsContinuing(true);
    try {
      const resp = await creativeApi.advanceProject(current.uuid, {
        advance_async: true,
        user: 'web-ui',
      });
      message.info(
        resp.status === 'queued'
          ? `续写任务已入队（task_id: ${resp.task_id.slice(0, 8)}…）`
          : `续写完成：${resp.message}`,
      );
      // 触发一次列表刷新，让列表项的 updated_at / last_advanced_at 及时反映
      // （后端在 enqueue 阶段也会写 last_advanced_at 时间戳）。
      loadList();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      message.error(`续写失败：${msg}`);
    } finally {
      if (mountedRef.current) setIsContinuing(false);
    }
  };

  // 暂停 / 完成 / 恢复：当前后端未提供对应的 PATCH/POST 端点，保留为本地乐观更新。
  // 如未来需要落库，可在此调用新增的 /api/creative/projects/{uuid}/status 接口。
  const updateProjectLocal = (uuid: string, patch: Partial<CreativeProject>) => {
    setProjects((prev) =>
      prev.map((p) => (p.uuid === uuid ? { ...p, ...patch } : p)),
    );
  };

  const handlePause = () => {
    if (!current) return;
    updateProjectLocal(current.uuid, { status: 'paused' });
    message.success(`${current.title} 已暂停`);
  };

  const handleComplete = () => {
    if (!current) return;
    updateProjectLocal(current.uuid, { status: 'completed' });
    message.success(`${current.title} 已标记为完成`);
  };

  const handleResume = () => {
    if (!current) return;
    updateProjectLocal(current.uuid, { status: 'active' });
    message.success(`${current.title} 已恢复`);
  };

  // ============== 渲染 ==============
  return (
    <Layout style={{ background: 'transparent', minHeight: 600 }}>
      <Sider
        width={320}
        theme="light"
        style={{
          background: '#fafafa',
          borderRight: '1px solid #f0f0f0',
          padding: 12,
        }}
      >
        <Title level={5} style={{ marginTop: 0 }}>
          创作项目
        </Title>
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="搜索项目"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select
            style={{ width: '100%' }}
            value={statusFilter}
            onChange={(v) => setStatusFilter(v as CreativeProjectStatus | 'all')}
            options={[
              { value: 'all', label: '全部状态' },
              { value: 'active', label: 'Active' },
              { value: 'completed', label: 'Completed' },
              { value: 'paused', label: 'Paused' },
              { value: 'drafting', label: 'Drafting' },
              { value: 'finished', label: 'Finished' },
            ]}
          />
        </Space>
        <div style={{ marginTop: 12 }}>
          {listLoading ? (
            <div style={{ textAlign: 'center', padding: 24 }}>
              <Spin />
            </div>
          ) : listError ? (
            <Alert
              type="error"
              message="列表加载失败"
              description={listError}
              action={
                <Button
                  size="small"
                  icon={<ReloadOutlined />}
                  onClick={loadList}
                >
                  重试
                </Button>
              }
            />
          ) : filteredProjects.length > 0 ? (
            <List
              size="small"
              dataSource={filteredProjects}
              rowKey={(p) => p.uuid}
              renderItem={(p) => {
                const meta = getStatusMeta(p.status);
                const isActive = p.uuid === selectedUuid;
                return (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      padding: 10,
                      borderRadius: 6,
                      background: isActive ? '#e6f4ff' : 'transparent',
                      border: isActive ? '1px solid #91caff' : '1px solid transparent',
                      marginBottom: 6,
                    }}
                    onClick={() => setSelectedUuid(p.uuid)}
                  >
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                        <Text strong>{p.title}</Text>
                        <Tag color={meta.color}>{meta.label}</Tag>
                      </Space>
                      <Space size={12}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {(p.word_count ?? 0).toLocaleString()} 字
                        </Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          <ClockCircleOutlined /> {formatRelative(p.updated_at)}
                        </Text>
                      </Space>
                    </Space>
                  </List.Item>
                );
              }}
            />
          ) : (
            <Empty description={projects.length === 0 ? '暂无创作项目' : '无匹配项目'} />
          )}
        </div>
      </Sider>
      <Content style={{ padding: '0 0 0 16px', background: 'transparent' }}>
        {!current ? (
          <Empty description="请从左侧选择一个创作项目" />
        ) : detailError ? (
          <Alert
            type="error"
            message="详情加载失败"
            description={detailError}
            action={
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => loadDetail(current.uuid)}
              >
                重试
              </Button>
            }
          />
        ) : !current.story_bible ? (
          // 列表接口不返回 story_bible；展示骨架屏直到详情拉取完成
          <Card title={current.title}>
            <Spin tip="正在加载 Story Bible...">
              <div style={{ minHeight: 240 }} />
            </Spin>
          </Card>
        ) : (
          <Card
            title={
              <Space>
                <span>{current.title}</span>
                <Tag color={getStatusMeta(current.status).color}>
                  {getStatusMeta(current.status).label}
                </Tag>
              </Space>
            }
            extra={
              <Space>
                {current.status === 'active' || current.status === 'drafting' ? (
                  <Popconfirm
                    title="暂停该项目？"
                    description="之后可以从同一视图恢复。"
                    okText="暂停"
                    onConfirm={handlePause}
                  >
                    <Button icon={<PauseCircleOutlined />}>暂停</Button>
                  </Popconfirm>
                ) : current.status === 'paused' ? (
                  <Button icon={<PlayCircleOutlined />} onClick={handleResume}>
                    恢复
                  </Button>
                ) : null}
                {current.status !== 'completed' && current.status !== 'finished' ? (
                  <Popconfirm
                    title="标记项目为已完成？"
                    description="完成后项目将关闭。"
                    okText="标记完成"
                    onConfirm={handleComplete}
                  >
                    <Button type="primary" icon={<CheckCircleOutlined />}>
                      标记完成
                    </Button>
                  </Popconfirm>
                ) : null}
                <Popconfirm
                  title="继续写作？"
                  description="将触发一次异步续写，进度会通过事件实时推送。"
                  okText="继续"
                  onConfirm={handleContinue}
                >
                  <Button
                    type="primary"
                    ghost
                    icon={<PlusOutlined />}
                    loading={isContinuing || detailLoading}
                    disabled={
                      current.status === 'completed' || current.status === 'finished'
                    }
                  >
                    续写
                  </Button>
                </Popconfirm>
              </Space>
            }
          >
            {detailLoading ? (
              <Skeleton active style={{ marginBottom: 16 }} />
            ) : null}

            <Descriptions size="small" column={2} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="UUID">{current.uuid}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={getStatusMeta(current.status).color}>
                  {getStatusMeta(current.status).label}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="字数">
                {(current.word_count ?? 0).toLocaleString()}
                {typeof current.target_chars === 'number' ? (
                  <Text type="secondary"> / {current.target_chars.toLocaleString()}</Text>
                ) : null}
              </Descriptions.Item>
              <Descriptions.Item label="章节">
                {current.story_bible.chapters.length}
              </Descriptions.Item>
              <Descriptions.Item label="体裁">
                {current.work_type || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="视角">
                {current.point_of_view || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {formatDateTime(current.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {formatDateTime(current.updated_at)}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5}>Story Bible</Title>
            <Paragraph type="secondary" style={{ marginBottom: 12 }}>
              {current.story_bible.chapters.length} 章 ·{' '}
              {current.story_bible.characters.length} 个角色
            </Paragraph>
            <StoryBibleViewer storyBible={current.story_bible} />
          </Card>
        )}
      </Content>
    </Layout>
  );
};

export default CreativePage;
