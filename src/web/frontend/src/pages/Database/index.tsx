// Database 页面 —— 业务表查询 / 删除（mock→真接口）
// 数据源：`/api/database/*`（23 表白名单）。删除走 `X-Confirm: true` 二次确认。

import React, { useEffect, useMemo, useState, useCallback } from 'react';
import {
  Layout,
  Menu,
  Input,
  Empty,
  Card,
  Statistic,
  Space,
  Tag,
  Typography,
  App as AntdApp,
  Button,
  Tooltip,
  Spin,
  Alert,
} from 'antd';
import {
  DatabaseOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import * as databaseApi from '@/api/database';
import DataTable from '@/components/DataTable';
import type { Column, ColumnType, Row, TableData } from '@/types/database';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

// 单表数据缓存条目（columns 由首行 schema 推导，避免对后端 schemas 强耦合）
interface TableEntry {
  columns: Column[];
  rows: Row[];
  total: number;
}

// 根据样本值推断列类型（DataTable 渲染时需要明确类型）
const inferColumnType = (value: unknown): ColumnType => {
  if (value === null || value === undefined) return 'string';
  if (typeof value === 'number') return 'number';
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'object') return 'json';
  if (typeof value === 'string') {
    // ISO 日期/时间启发式：YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SS
    if (/^\d{4}-\d{2}-\d{2}([T\s]\d{2}:\d{2})?/.test(value)) return 'datetime';
  }
  return 'string';
};

// 从数据首行 schema 推导 Column[]，供 DataTable 渲染
const deriveColumns = (rows: Row[]): Column[] => {
  if (!rows || rows.length === 0) return [];
  const sample = rows[0] || {};
  return Object.keys(sample).map((key) => ({
    key,
    label: key,
    type: inferColumnType((sample as Row)[key]),
  }));
};

const DatabasePage: React.FC = () => {
  const { message } = AntdApp.useApp();

  // 左侧表名列表（由 `/api/database/tables` 拉取）
  const [tables, setTables] = useState<string[]>([]);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [tablesError, setTablesError] = useState<string | null>(null);

  // 当前选中的表
  const [selectedTable, setSelectedTable] = useState<string>('');

  // 单表数据缓存：按表名存 { columns, rows, total }
  const [tableData, setTableData] = useState<Record<string, TableEntry>>({});
  const [tableLoading, setTableLoading] = useState(false);
  const [tableError, setTableError] = useState<string | null>(null);

  // 搜索框
  const [search, setSearch] = useState('');

  // 加载表名列表（页面挂载时 + 手动 Reload 时）
  const loadTables = useCallback(async () => {
    setTablesLoading(true);
    setTablesError(null);
    try {
      const res = await databaseApi.listTables();
      const names = res?.tables ?? [];
      setTables(names);
      // 若之前没选过表，默认选第一张
      setSelectedTable((prev) => prev || names[0] || '');
    } catch (err) {
      const msg = databaseApi.formatApiError(err);
      setTablesError(msg);
      message.error(`加载表列表失败: ${msg}`);
    } finally {
      setTablesLoading(false);
    }
  }, [message]);

  useEffect(() => {
    void loadTables();
  }, [loadTables]);

  // 选中表变化时拉取该表数据
  const loadTableData = useCallback(
    async (table: string) => {
      if (!table) return;
      setTableLoading(true);
      setTableError(null);
      try {
        const res = await databaseApi.getTableData(table, 100, 0);
        const rows = (res?.rows ?? []) as Row[];
        setTableData((prev) => ({
          ...prev,
          [table]: {
            columns: deriveColumns(rows),
            rows,
            total: res?.total ?? rows.length,
          },
        }));
      } catch (err) {
        const msg = databaseApi.formatApiError(err);
        setTableError(msg);
        message.error(`加载表 ${table} 失败: ${msg}`);
      } finally {
        setTableLoading(false);
      }
    },
    [message],
  );

  useEffect(() => {
    if (selectedTable) {
      void loadTableData(selectedTable);
    }
  }, [selectedTable, loadTableData]);

  // 搜索过滤后的表名
  const filteredTableNames = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return tables;
    return tables.filter((name) => name.toLowerCase().includes(q));
  }, [tables, search]);

  // Sider Menu 数据源
  const menuItems: MenuProps['items'] = useMemo(
    () =>
      filteredTableNames.map((name) => ({
        key: name,
        label: name,
        icon: <DatabaseOutlined />,
      })),
    [filteredTableNames],
  );

  // 当前展示的表数据
  const currentEntry: TableEntry | undefined = selectedTable
    ? tableData[selectedTable]
    : undefined;

  // 适配 DataTable 期望的 TableData 形状（仅用于渲染，不写回 state）
  const currentView: TableData | undefined = useMemo(() => {
    if (!selectedTable || !currentEntry) return undefined;
    return {
      name: selectedTable,
      info: {
        rowCount: currentEntry.rows.length,
        columnCount: currentEntry.columns.length,
        sizeKB: 0, // 后端未提供 sizeKB，前端不臆造
      },
      columns: currentEntry.columns,
      rows: currentEntry.rows,
    };
  }, [selectedTable, currentEntry]);

  const handleSelect = (key: string) => {
    setSelectedTable(key);
  };

  // 重新拉取当前表数据
  const handleRefresh = () => {
    if (!selectedTable) return;
    void loadTableData(selectedTable);
    message.success(`Reloaded ${selectedTable}`);
  };

  // 删除单行：必须带 X-Confirm: true（由 databaseApi.deleteRecord 内部处理）
  const handleDeleteRow = async (uuid: string) => {
    if (!selectedTable) return;
    try {
      const res = await databaseApi.deleteRecord(selectedTable, uuid);
      if (res?.deleted) {
        // 本地剔除该行，避免再发一次 list 请求
        setTableData((prev) => {
          const cur = prev[selectedTable];
          if (!cur) return prev;
          return {
            ...prev,
            [selectedTable]: {
              ...cur,
              rows: cur.rows.filter(
                (r) => String((r as Row).uuid ?? '') !== uuid,
              ),
              total: Math.max(0, cur.total - 1),
            },
          };
        });
        message.success(`Deleted row ${uuid}`);
      } else {
        message.warning('后端未匹配到记录（可能已被删除）');
      }
    } catch (err) {
      // 400 + 缺 X-Confirm 等场景都走这里
      const msg = databaseApi.formatApiError(err);
      message.error(`删除失败: ${msg}`);
    }
  };

  return (
    <Layout style={{ background: 'transparent', minHeight: 600 }}>
      <Sider
        width={240}
        theme="light"
        style={{
          background: '#fafafa',
          borderRight: '1px solid #f0f0f0',
          padding: 12,
        }}
      >
        <Title level={5} style={{ marginTop: 0 }}>
          Tables
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          Whitelisted business tables only.
        </Text>
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Search tables"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ marginTop: 12, marginBottom: 8 }}
        />
        {tablesLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin size="small" />
          </div>
        ) : tablesError ? (
          <Alert
            type="error"
            showIcon
            message="加载表列表失败"
            description={tablesError}
            action={
              <Button size="small" onClick={loadTables}>
                重试
              </Button>
            }
          />
        ) : filteredTableNames.length > 0 ? (
          <Menu
            mode="inline"
            selectedKeys={selectedTable ? [selectedTable] : []}
            items={menuItems}
            onSelect={({ key }) => handleSelect(String(key))}
            style={{ borderRight: 0, background: 'transparent' }}
          />
        ) : (
          <Empty description="No tables match" style={{ marginTop: 24 }} />
        )}
      </Sider>
      <Content style={{ padding: '0 0 0 16px', background: 'transparent' }}>
        {currentView ? (
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                <span>{currentView.name}</span>
                <Tag color="blue">business</Tag>
              </Space>
            }
            extra={
              <Space>
                <Tooltip title="Reload from server">
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={handleRefresh}
                    loading={tableLoading}
                  >
                    Reload
                  </Button>
                </Tooltip>
                {/* 注意：保留 DataTable 行级 Popconfirm 二次确认（删除时触发） */}
              </Space>
            }
          >
            {tableError && (
              <Alert
                type="error"
                showIcon
                message="加载表数据失败"
                description={tableError}
                style={{ marginBottom: 16 }}
                action={
                  <Button size="small" onClick={handleRefresh}>
                    重试
                  </Button>
                }
              />
            )}
            <Space size="large" style={{ marginBottom: 16 }} wrap>
              <Statistic
                title="Rows (loaded)"
                value={currentView.info.rowCount}
                valueStyle={{ fontSize: 20 }}
              />
              <Statistic
                title="Columns"
                value={currentView.info.columnCount}
                valueStyle={{ fontSize: 20 }}
              />
              <Statistic
                title="Total (server)"
                value={currentEntry?.total ?? currentView.info.rowCount}
                valueStyle={{ fontSize: 20 }}
              />
            </Space>
            <Spin spinning={tableLoading}>
              <DataTable
                columns={currentView.columns}
                data={currentView.rows}
                rowKey="uuid"
                loading={tableLoading}
                onDelete={handleDeleteRow}
              />
            </Spin>
          </Card>
        ) : selectedTable ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin />
          </div>
        ) : (
          <Empty description="Select a table from the left" />
        )}
      </Content>
    </Layout>
  );
};

export default DatabasePage;
