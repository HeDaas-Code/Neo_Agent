import React from 'react';
import { Table, Tag, Button, Space, Typography, Descriptions, Empty } from 'antd';
import type { ColumnsType, ExpandableConfig } from 'antd/es/table/interface';
import { CheckOutlined, InboxOutlined, EyeOutlined } from '@ant-design/icons';
import type { Event, EventStatus, EventType } from '../types/event';

const { Text, Paragraph } = Typography;

export interface EventTableProps {
  events: Event[];
  onMarkRead?: (uuid: string) => void;
  onArchive?: (uuid: string) => void;
  loading?: boolean;
}

const typeColorMap: Record<EventType, string> = {
  notification: 'blue',
  task: 'geekblue',
  system: 'purple',
};

const typeLabelMap: Record<EventType, string> = {
  notification: 'notification',
  task: 'task',
  system: 'system',
};

const statusColorMap: Record<EventStatus, string> = {
  pending: 'gold',
  completed: 'green',
  failed: 'red',
};

const statusLabelMap: Record<EventStatus, string> = {
  pending: 'pending',
  completed: 'completed',
  failed: 'failed',
};

const formatTimestamp = (iso: string): string => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

const EventTable: React.FC<EventTableProps> = ({ events, onMarkRead, onArchive, loading = false }) => {
  const columns: ColumnsType<Event> = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      sorter: (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      defaultSortOrder: 'descend',
      render: (value: string) => <Text code>{formatTimestamp(value)}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 130,
      filters: (Object.keys(typeLabelMap) as EventType[]).map((k) => ({ text: typeLabelMap[k], value: k })),
      onFilter: (value, record) => record.type === value,
      render: (value: EventType) => <Tag color={typeColorMap[value]}>{typeLabelMap[value]}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      filters: (Object.keys(statusLabelMap) as EventStatus[]).map((k) => ({ text: statusLabelMap[k], value: k })),
      onFilter: (value, record) => record.status === value,
      render: (value: EventStatus) => <Tag color={statusColorMap[value]}>{statusLabelMap[value]}</Tag>,
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 200,
      ellipsis: true,
      sorter: (a, b) => a.source.localeCompare(b.source),
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      sorter: (a, b) => a.message.localeCompare(b.message),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_value, record) => (
        <Space size="small">
          <Button
            size="small"
            type="link"
            icon={<CheckOutlined />}
            disabled={record.status !== 'pending'}
            onClick={(e) => {
              e.stopPropagation();
              onMarkRead?.(record.uuid);
            }}
          >
            标记已读
          </Button>
          <Button
            size="small"
            type="link"
            icon={<InboxOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              onArchive?.(record.uuid);
            }}
          >
            归档
          </Button>
        </Space>
      ),
    },
  ];

  const expandable: ExpandableConfig<Event> = {
    expandedRowRender: (record) => (
      <div style={{ padding: '4px 8px' }}>
        <Descriptions size="small" column={1} bordered title={<span><EyeOutlined /> Payload 详情</span>}>
          <Descriptions.Item label="UUID">
            <Text code>{record.uuid}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="时间">
            <Text code>{record.timestamp}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Payload (JSON)">
            <Paragraph
              copyable
              style={{ marginBottom: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}
            >
              <pre style={{ margin: 0 }}>{JSON.stringify(record.payload, null, 2)}</pre>
            </Paragraph>
          </Descriptions.Item>
        </Descriptions>
      </div>
    ),
    rowExpandable: () => true,
  };

  return (
    <Table<Event>
      rowKey="uuid"
      columns={columns}
      dataSource={events}
      loading={loading}
      size="middle"
      bordered
      pagination={{
        pageSize: 20,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 条`,
        pageSizeOptions: ['10', '20', '50', '100'],
      }}
      scroll={{ x: 1000 }}
      expandable={expandable}
      locale={{
        emptyText: <Empty description="暂无事件" />,
      }}
    />
  );
};

export default EventTable;
