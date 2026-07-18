import React, { useMemo, useState } from 'react';
import { Table, Button, Popconfirm, Tag, Tooltip, Typography, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DeleteOutlined, CodeOutlined } from '@ant-design/icons';
import type { Column, Row } from '@/types/database';

const { Text, Paragraph } = Typography;

export interface DataTableProps {
  columns: Column[];
  data: Row[];
  loading?: boolean;
  rowKey?: string;
  onDelete?: (uuid: string) => void;
}

const formatValue = (value: unknown, type: Column['type']): React.ReactNode => {
  if (value === null || value === undefined) {
    return <Text type="secondary">—</Text>;
  }
  switch (type) {
    case 'number':
      return <Text>{Number(value).toLocaleString()}</Text>;
    case 'datetime':
      return <Text>{String(value)}</Text>;
    case 'boolean':
      return value ? <Tag color="green">true</Tag> : <Tag color="default">false</Tag>;
    case 'json':
      return <JsonCell value={value} />;
    case 'string':
    default:
      return <Text>{String(value)}</Text>;
  }
};

const JsonCell: React.FC<{ value: unknown }> = ({ value }) => {
  const [open, setOpen] = useState(false);
  const text = useMemo(() => {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }, [value]);
  if (open) {
    return (
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <Button
          size="small"
          type="link"
          icon={<CodeOutlined />}
          onClick={() => setOpen(false)}
          style={{ padding: 0 }}
        >
          Collapse JSON
        </Button>
        <pre
          style={{
            background: '#f5f5f5',
            padding: 8,
            borderRadius: 4,
            margin: 0,
            maxHeight: 240,
            overflow: 'auto',
            fontSize: 12,
          }}
        >
          {text}
        </pre>
      </Space>
    );
  }
  return (
    <Tooltip title="Click to expand JSON">
      <Button size="small" type="link" onClick={() => setOpen(true)} style={{ padding: 0 }}>
        {`{ ${text.length > 60 ? `${text.slice(0, 60)}…` : text.slice(0, 60)} }`}
      </Button>
    </Tooltip>
  );
};

const DataTable: React.FC<DataTableProps> = ({
  columns,
  data,
  loading = false,
  rowKey = 'uuid',
  onDelete,
}) => {
  const tableColumns: ColumnsType<Row> = useMemo(() => {
    const antdColumns: ColumnsType<Row> = columns.map((col) => ({
      title: col.label,
      dataIndex: col.key,
      key: col.key,
      width: col.width,
      sorter:
        col.type === 'number' || col.type === 'datetime'
          ? (a: Row, b: Row) => {
              const av = a[col.key];
              const bv = b[col.key];
              if (typeof av === 'number' && typeof bv === 'number') {
                return av - bv;
              }
              return String(av ?? '').localeCompare(String(bv ?? ''));
            }
          : undefined,
      filters:
        col.type === 'string' || col.type === 'datetime'
          ? Array.from(new Set(data.map((r) => String(r[col.key] ?? ''))))
              .slice(0, 20)
              .map((v) => ({ text: v, value: v }))
          : undefined,
      onFilter: (value, record) => String(record[col.key] ?? '') === value,
      render: (value: unknown) => formatValue(value, col.type),
      ellipsis: col.type === 'string' || col.type === 'datetime',
    }));

    if (onDelete) {
      antdColumns.push({
        title: 'Actions',
        key: 'actions',
        width: 120,
        fixed: 'right',
        render: (_value, record) => {
          const uuid = String(record[rowKey] ?? '');
          return (
            <Popconfirm
              title="Delete this row?"
              description="This action cannot be undone."
              okText="Delete"
              okButtonProps={{ danger: true }}
              cancelText="Cancel"
              onConfirm={() => onDelete(uuid)}
            >
              <Button danger size="small" icon={<DeleteOutlined />}>
                Delete
              </Button>
            </Popconfirm>
          );
        },
      });
    }

    return antdColumns;
  }, [columns, data, onDelete, rowKey]);

  return (
    <div>
      <Table<Row>
        rowKey={rowKey}
        columns={tableColumns}
        dataSource={data}
        loading={loading}
        scroll={{ x: 'max-content' }}
        size="small"
        pagination={{
          defaultPageSize: 10,
          pageSizeOptions: ['10', '20', '50', '100'],
          showSizeChanger: true,
          showTotal: (total) => `${total} rows`,
        }}
      />
      {data.length === 0 && !loading ? (
        <Paragraph type="secondary" style={{ textAlign: 'center', marginTop: 16 }}>
          No rows in this table.
        </Paragraph>
      ) : null}
    </div>
  );
};

export default DataTable;
