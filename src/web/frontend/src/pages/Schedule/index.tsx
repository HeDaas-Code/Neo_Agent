import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Calendar,
  Card,
  Col,
  Empty,
  List,
  Modal,
  Popconfirm,
  Radio,
  Row,
  Segmented,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CalendarOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import dayjs, { type Dayjs } from 'dayjs';
import ScheduleForm, {
  type ScheduleFormValues,
} from '../../components/ScheduleForm';
import * as scheduleApi from '../../api/schedule';
import type {
  Schedule,
  SchedulePriority,
  ScheduleStatus,
  ScheduleType,
} from '../../api/schedule';

const { Text, Title } = Typography;

type ViewMode = 'calendar' | 'list';
type ListFilter = 'all' | ScheduleType | 'pending' | 'collaborative';

const PRIORITY_LABEL: Record<SchedulePriority, string> = {
  low: '低',
  normal: '普通',
  high: '高',
};

const PRIORITY_COLOR: Record<SchedulePriority, string> = {
  low: 'default',
  normal: 'blue',
  high: 'red',
};

const TYPE_LABEL: Record<ScheduleType, string> = {
  personal: '个人',
  work: '工作',
  family: '家庭',
};

const TYPE_COLOR: Record<ScheduleType, string> = {
  personal: 'cyan',
  work: 'blue',
  family: 'magenta',
};

const STATUS_LABEL: Record<ScheduleStatus, string> = {
  pending: '待办',
  confirmed: '已确认',
  done: '已完成',
  cancelled: '已取消',
};

const STATUS_COLOR: Record<ScheduleStatus, string> = {
  pending: 'orange',
  confirmed: 'green',
  done: 'default',
  cancelled: 'red',
};

function formatTime(iso: string): string {
  return dayjs(iso).format('HH:mm');
}

function isSameDay(iso: string, target: Dayjs): boolean {
  const d = dayjs(iso);
  return (
    d.year() === target.year() &&
    d.month() === target.month() &&
    d.date() === target.date()
  );
}

export default function SchedulePage(): JSX.Element {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [view, setView] = useState<ViewMode>('calendar');
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  /** 已加载过的月份(YYYY-MM),避免重复请求 */
  const [loadedMonth, setLoadedMonth] = useState<string>('');
  const [listFilter, setListFilter] = useState<ListFilter>('all');
  const [loading, setLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Schedule | undefined>(undefined);
  const [detail, setDetail] = useState<Schedule | undefined>(undefined);
  const [confirmingId, setConfirmingId] = useState<string | undefined>(undefined);

  /**
   * 加载某个月份的日程(用于日历徽标和列表)。
   * 已加载过的月份不会重复请求,切换视图只更新本地状态。
   */
  const loadMonth = useCallback(async (anchor: Dayjs): Promise<void> => {
    const monthKey = anchor.format('YYYY-MM');
    if (monthKey === loadedMonth) return;
    setLoading(true);
    try {
      const from = anchor.startOf('month').format('YYYY-MM-DD');
      const to = anchor.endOf('month').format('YYYY-MM-DD');
      const items = await scheduleApi.listByRange(from, to);
      setSchedules(items);
      setLoadedMonth(monthKey);
    } catch (err) {
      message.error((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [loadedMonth]);

  /** 初始挂载:加载当前月 */
  useEffect(() => {
    void loadMonth(dayjs());
  }, [loadMonth]);

  /** 月份切换时,重新加载该月(后端按区间查) */
  const handlePanelChange = (d: Dayjs): void => {
    setSelectedDate(d);
    void loadMonth(d);
  };

  /** 日历单元格渲染:当日日程条数徽标 */
  const cellRender = (current: Dayjs, info: { type: string }): React.ReactNode => {
    if (info.type !== 'date') return null;
    const count = schedules.filter((s) => isSameDay(s.start_time, current))
      .length;
    if (count === 0) return null;
    return (
      <Badge
        count={count}
        style={{ backgroundColor: '#1677ff' }}
        title={`${count} 条日程`}
      />
    );
  };

  const schedulesOnSelectedDate = useMemo(
    () =>
      schedules
        .filter((s) => isSameDay(s.start_time, selectedDate))
        .sort((a, b) => a.start_time.localeCompare(b.start_time)),
    [schedules, selectedDate],
  );

  const filteredList = useMemo(() => {
    const arr = [...schedules].sort((a, b) =>
      a.start_time.localeCompare(b.start_time),
    );
    switch (listFilter) {
      case 'all':
        return arr;
      case 'collaborative':
        return arr.filter((s) => s.is_collaborative);
      case 'pending':
        return arr.filter((s) => s.status === 'pending');
      default:
        return arr.filter((s) => s.schedule_type === listFilter);
    }
  }, [schedules, listFilter]);

  const openCreate = (): void => {
    setEditing(undefined);
    setFormOpen(true);
  };

  const openEdit = (s: Schedule): void => {
    setEditing(s);
    setFormOpen(true);
  };

  /** 提交表单:新建或更新 */
  const handleSubmit = async (values: ScheduleFormValues): Promise<void> => {
    setSubmitting(true);
    try {
      const payload: scheduleApi.ScheduleCreatePayload = {
        title: values.title,
        description: values.description ?? '',
        start_time: values.start_time.toISOString(),
        end_time: values.end_time.toISOString(),
        priority: values.priority,
        schedule_type: values.schedule_type,
      };
      if (editing) {
        const id = editing.id ?? editing.uuid;
        const updatePayload: scheduleApi.ScheduleUpdatePayload = {
          title: payload.title,
          description: payload.description,
          start_time: payload.start_time,
          end_time: payload.end_time,
          priority: payload.priority,
        };
        await scheduleApi.update(id, updatePayload);
        message.success('已更新');
        // 本地乐观更新一条(避免再触发一次查询)
        setSchedules((prev) =>
          prev.map((s) =>
            (s.id ?? s.uuid) === id
              ? { ...s, ...updatePayload, status: s.status }
              : s,
          ),
        );
      } else {
        const created = await scheduleApi.create(payload);
        message.success('已新增');
        setSchedules((prev) => [created, ...prev]);
        // 若新建落在当前加载月之外,刷新月份缓存
        const createdMonth = dayjs(created.start_time).format('YYYY-MM');
        if (createdMonth !== loadedMonth) {
          setLoadedMonth(''); // 强制下次重新加载
        }
      }
      setFormOpen(false);
      setEditing(undefined);
    } catch (err) {
      message.error((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  /** 删除日程 */
  const handleDelete = async (uuid: string, id?: number): Promise<void> => {
    try {
      await scheduleApi.remove(id ?? uuid);
      setSchedules((prev) => prev.filter((s) => (s.id ?? s.uuid) !== (id ?? uuid)));
      if ((detail?.id ?? detail?.uuid) === (id ?? uuid)) setDetail(undefined);
      message.success('已删除');
    } catch (err) {
      message.error((err as Error).message);
    }
  };

  /** 协作日程确认 */
  const handleConfirm = async (s: Schedule): Promise<void> => {
    const id = s.id ?? s.uuid;
    setConfirmingId(s.uuid);
    try {
      const newStatus = await scheduleApi.confirmCollaboration(id, true);
      message.success('协作已确认');
      setSchedules((prev) =>
        prev.map((it) =>
          (it.id ?? it.uuid) === id
            ? { ...it, status: newStatus, collaborator_status: 'confirmed' }
            : it,
        ),
      );
      if ((detail?.id ?? detail?.uuid) === id) {
        setDetail((d) =>
          d ? { ...d, status: newStatus, collaborator_status: 'confirmed' } : d,
        );
      }
    } catch (err) {
      message.error((err as Error).message);
    } finally {
      setConfirmingId(undefined);
    }
  };

  const renderCard = (s: Schedule): JSX.Element => (
    <Card
      key={s.uuid}
      size="small"
      hoverable
      className="cursor-pointer"
      onClick={() => setDetail(s)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <Space wrap>
            <Text strong>{s.title}</Text>
            <Tag color={PRIORITY_COLOR[s.priority]}>
              {PRIORITY_LABEL[s.priority]}优先级
            </Tag>
            <Tag color={TYPE_COLOR[s.schedule_type]}>
              {TYPE_LABEL[s.schedule_type]}
            </Tag>
            <Tag color={STATUS_COLOR[s.status]}>{STATUS_LABEL[s.status]}</Tag>
            {s.is_collaborative && (
              <Tag
                color={
                  s.collaborator_status === 'confirmed'
                    ? 'green'
                    : s.collaborator_status === 'declined'
                    ? 'red'
                    : 'gold'
                }
              >
                {s.collaborator_status === 'confirmed'
                  ? '已确认'
                  : s.collaborator_status === 'declined'
                  ? '已拒绝'
                  : '待对方确认'}
                {s.collaborator_name ? ` · ${s.collaborator_name}` : ''}
              </Tag>
            )}
          </Space>
          <div className="mt-1 text-xs text-gray-500">
            {dayjs(s.start_time).format('YYYY-MM-DD')}{' '}
            {formatTime(s.start_time)} - {formatTime(s.end_time)}
          </div>
          {s.description && (
            <div className="mt-1 text-xs text-gray-600 line-clamp-2 whitespace-pre-wrap">
              {s.description}
            </div>
          )}
        </div>
        <Space onClick={(e) => e.stopPropagation()}>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(s)}
          />
          {s.is_collaborative && s.collaborator_status !== 'confirmed' && (
            <Button
              type="text"
              size="small"
              icon={<CheckCircleOutlined />}
              loading={confirmingId === s.uuid}
              onClick={() => void handleConfirm(s)}
            />
          )}
          <Popconfirm
            title="删除该日程?"
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={() => void handleDelete(s.uuid, s.id)}
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      </div>
    </Card>
  );

  return (
    <div className="space-y-4">
      {/* 顶部:视图切换 + 新建 */}
      <Card>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space size="middle" wrap>
              <Title level={4} style={{ margin: 0 }}>
                日程
              </Title>
              <Segmented<ViewMode>
                value={view}
                onChange={(v) => setView(v)}
                options={[
                  {
                    label: (
                      <span>
                        <CalendarOutlined /> 日历
                      </span>
                    ),
                    value: 'calendar',
                  },
                  {
                    label: (
                      <span>
                        <UnorderedListOutlined /> 列表
                      </span>
                    ),
                    value: 'list',
                  },
                ]}
              />
              {view === 'list' && (
                <Radio.Group
                  value={listFilter}
                  onChange={(e) => setListFilter(e.target.value)}
                  optionType="button"
                  buttonStyle="solid"
                >
                  <Radio.Button value="all">全部</Radio.Button>
                  <Radio.Button value="pending">待办</Radio.Button>
                  <Radio.Button value="collaborative">协作</Radio.Button>
                  <Radio.Button value="personal">个人</Radio.Button>
                  <Radio.Button value="work">工作</Radio.Button>
                  <Radio.Button value="family">家庭</Radio.Button>
                </Radio.Group>
              )}
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={openCreate}
            >
              新建日程
            </Button>
          </Col>
        </Row>
      </Card>

      <Spin spinning={loading} tip="加载中...">
        {view === 'calendar' ? (
          <Row gutter={16}>
            <Col xs={24} lg={16}>
              <Card>
                <Calendar
                  value={selectedDate}
                  onSelect={(d) => setSelectedDate(d)}
                  onPanelChange={handlePanelChange}
                  cellRender={cellRender}
                />
              </Card>
            </Col>
            <Col xs={24} lg={8}>
              <Card
                title={
                  <Space>
                    <Text strong>{selectedDate.format('YYYY-MM-DD')}</Text>
                    <Badge
                      count={schedulesOnSelectedDate.length}
                      showZero
                      color="#1677ff"
                    />
                  </Space>
                }
                bodyStyle={{ maxHeight: 600, overflowY: 'auto' }}
              >
                {schedulesOnSelectedDate.length === 0 ? (
                  <Empty description="该日无日程" />
                ) : (
                  <Space direction="vertical" className="w-full" size="small">
                    {schedulesOnSelectedDate.map(renderCard)}
                  </Space>
                )}
              </Card>
            </Col>
          </Row>
        ) : (
          <Card>
            {filteredList.length === 0 ? (
              <Empty description="没有匹配的日程" />
            ) : (
              <List
                dataSource={filteredList}
                rowKey={(s) => s.uuid}
                grid={{ gutter: 12, column: 2 }}
                renderItem={(s) => <List.Item>{renderCard(s)}</List.Item>}
              />
            )}
          </Card>
        )}
      </Spin>

      <ScheduleForm
        open={formOpen}
        initial={editing}
        submitting={submitting}
        onClose={() => {
          setFormOpen(false);
          setEditing(undefined);
        }}
        onSubmit={handleSubmit}
      />

      <Modal
        open={!!detail}
        title={detail?.title}
        onCancel={() => setDetail(undefined)}
        footer={[
          detail?.is_collaborative &&
            detail.collaborator_status !== 'confirmed' && (
              <Button
                key="confirm"
                type="primary"
                icon={<CheckCircleOutlined />}
                loading={confirmingId === detail?.uuid}
                onClick={() => detail && void handleConfirm(detail)}
              >
                协作确认
              </Button>
            ),
          <Button
            key="edit"
            icon={<EditOutlined />}
            onClick={() => {
              if (detail) {
                const d = detail;
                setDetail(undefined);
                openEdit(d);
              }
            }}
          >
            编辑
          </Button>,
          <Popconfirm
            key="del"
            title="删除该日程?"
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={() => {
              if (detail) void handleDelete(detail.uuid, detail.id);
            }}
          >
            <Button danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>,
          <Button
            key="close"
            type="primary"
            onClick={() => setDetail(undefined)}
          >
            关闭
          </Button>,
        ]}
      >
        {detail && (
          <Space direction="vertical" className="w-full" size="small">
            <Space wrap>
              <Tag color={PRIORITY_COLOR[detail.priority]}>
                {PRIORITY_LABEL[detail.priority]}优先级
              </Tag>
              <Tag color={TYPE_COLOR[detail.schedule_type]}>
                {TYPE_LABEL[detail.schedule_type]}
              </Tag>
              <Tag color={STATUS_COLOR[detail.status]}>
                {STATUS_LABEL[detail.status]}
              </Tag>
              {detail.is_collaborative && (
                <Tag
                  color={
                    detail.collaborator_status === 'confirmed'
                      ? 'green'
                      : detail.collaborator_status === 'declined'
                      ? 'red'
                      : 'gold'
                  }
                >
                  {detail.collaborator_status === 'confirmed'
                    ? '协作 · 已确认'
                    : detail.collaborator_status === 'declined'
                    ? '协作 · 已拒绝'
                    : '协作 · 待对方确认'}
                  {detail.collaborator_name
                    ? ` (${detail.collaborator_name})`
                    : ''}
                </Tag>
              )}
            </Space>
            <Text type="secondary">
              {dayjs(detail.start_time).format('YYYY-MM-DD HH:mm')} ~{' '}
              {dayjs(detail.end_time).format('YYYY-MM-DD HH:mm')}
            </Text>
            {detail.description && (
              <div className="whitespace-pre-wrap text-sm">
                {detail.description}
              </div>
            )}
          </Space>
        )}
      </Modal>
    </div>
  );
}
