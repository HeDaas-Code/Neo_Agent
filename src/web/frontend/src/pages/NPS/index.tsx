import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Card,
  Button,
  List,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Empty,
  message,
  Typography,
  Descriptions,
  Statistic,
  Row,
  Col,
  Spin,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ApiOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import NPSConfigDrawer from '../../components/NPSConfigDrawer';
import * as npsApi from '../../api/nps';
import type { NPS, NPSConfigFormValues, NPSType } from '../../types/nps';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

// 类型与标签颜色映射
const typeColorMap: Record<NPSType, string> = {
  function: 'blue',
  tool: 'geekblue',
  workflow: 'purple',
};

// ISO 时间格式化为本地字符串
const formatDateTime = (iso: string | null): string => {
  if (!iso) return '从未调用';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

const NPSPage: React.FC = () => {
  // 列表数据
  const [npsList, setNpsList] = useState<NPS[]>([]);
  // 加载/错误/提交状态
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [invoking, setInvoking] = useState<boolean>(false);

  // Drawer / 弹窗状态
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [invokeModalOpen, setInvokeModalOpen] = useState(false);
  const [invokingNps, setInvokingNps] = useState<NPS | null>(null);
  const [invokeResult, setInvokeResult] = useState<{
    npsName: string;
    args: Record<string, any>;
    result: unknown;
    status: string;
    executed_at: string;
  } | null>(null);
  const [invokeForm] = Form.useForm();

  // 加载 NPS 列表（GET /api/nps）
  const fetchNpsList = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const list = await npsApi.listNps();
      setNpsList(Array.isArray(list) ? list : []);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '获取 NPS 列表失败';
      setLoadError(msg);
      message.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  // 首次加载
  useEffect(() => {
    void fetchNpsList();
  }, [fetchNpsList]);

  // 打开注册 Drawer
  const openCreateDrawer = useCallback(() => {
    setDrawerOpen(true);
  }, []);

  // 关闭 Drawer
  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
  }, []);

  // 提交注册（POST /api/nps/register）
  const handleDrawerSubmit = useCallback(
    async (values: NPSConfigFormValues) => {
      setSubmitting(true);
      try {
        const created = await npsApi.registerNps(values);
        // 头部插入新条目，立即可见
        setNpsList((prev) => [created, ...prev]);
        message.success(`已注册 NPS: ${created.name}`);
        setDrawerOpen(false);
      } catch (err) {
        const msg = err instanceof Error ? err.message : '注册 NPS 失败';
        message.error(msg);
      } finally {
        setSubmitting(false);
      }
    },
    [],
  );

  // 打开调用弹窗：按 NPS 声明的 params 动态生成入参表单
  const openInvokeModal = useCallback(
    (nps: NPS) => {
      if (!nps.enabled) {
        message.warning('该 NPS 当前已禁用，无法调用');
        return;
      }
      invokeForm.resetFields();
      const defaults: Record<string, string> = {};
      for (const p of nps.params) {
        defaults[p.key] = p.value ?? '';
      }
      invokeForm.setFieldsValue(defaults);
      setInvokeResult(null);
      setInvokingNps(nps);
      setInvokeModalOpen(true);
    },
    [invokeForm],
  );

  // 提交调用（POST /api/nps/invoke）
  const handleInvoke = useCallback(async () => {
    if (!invokingNps) return;
    try {
      const values = await invokeForm.validateFields();
      // 构造 args 对象（按 NPS 声明的参数键收集表单值）
      const argsObj: Record<string, any> = {};
      for (const p of invokingNps.params) {
        const raw = values[p.key];
        argsObj[p.key] = raw == null ? '' : raw;
      }
      setInvoking(true);
      const resp = await npsApi.invokeNps({ uuid: invokingNps.uuid, args: argsObj });
      setInvokeResult({
        npsName: invokingNps.name,
        args: argsObj,
        result: resp.result,
        status: resp.status,
        executed_at: resp.executed_at,
      });
      // 本地累计调用次数（乐观更新，后端可能在 listNps 中带真实值）
      setNpsList((prevList) =>
        prevList.map((n) =>
          n.uuid === invokingNps.uuid
            ? {
                ...n,
                call_count: n.call_count + 1,
                last_called_at: resp.executed_at,
              }
            : n,
        ),
      );
      message.success(`调用成功: ${invokingNps.name}`);
    } catch (err) {
      // 区分 antd 校验失败（无 err.message）和后端业务错误
      if (err instanceof Error && err.message) {
        message.error(err.message);
      }
    } finally {
      setInvoking(false);
    }
  }, [invokeForm, invokingNps]);

  // 4 个统计卡：总数 / 已启用 / 已禁用 / 累计调用
  const stats = useMemo(() => {
    const enabled = npsList.filter((n) => n.enabled).length;
    const disabled = npsList.length - enabled;
    const totalCalls = npsList.reduce((acc, n) => acc + n.call_count, 0);
    return { total: npsList.length, enabled, disabled, totalCalls };
  }, [npsList]);

  return (
    <div>
      {/* 顶部 4 个统计卡 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" bordered>
            <Statistic
              title="NPS 总数"
              value={stats.total}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" bordered>
            <Statistic
              title="已启用"
              value={stats.enabled}
              valueStyle={{ color: '#389e0d' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" bordered>
            <Statistic
              title="已禁用"
              value={stats.disabled}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" bordered>
            <Statistic
              title="累计调用"
              value={stats.totalCalls}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 列表区（带加载/错误/空态） */}
      <Card
        title="NPS 列表 (Neo Prompt Service)"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchNpsList}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={openCreateDrawer}
            >
              注册新 NPS
            </Button>
          </Space>
        }
      >
        {/* 错误提示：仍保留旧数据以便用户操作 */}
        {loadError && (
          <Alert
            type="error"
            showIcon
            style={{ marginBottom: 12 }}
            message="加载 NPS 列表失败"
            description={loadError}
            action={
              <Button size="small" onClick={fetchNpsList}>
                重试
              </Button>
            }
          />
        )}

        <Spin spinning={loading} tip="加载中...">
          <List<NPS>
            dataSource={npsList}
            rowKey="uuid"
            locale={{
              emptyText: loading ? (
                <span style={{ color: '#999' }}>正在加载...</span>
              ) : (
                <Empty description="暂无 NPS，点右上角注册" />
              ),
            }}
            pagination={{
              pageSize: 10,
              showSizeChanger: false,
              showTotal: (t) => `共 ${t} 条`,
            }}
            renderItem={(item) => (
              <List.Item
                key={item.uuid}
                actions={[
                  <Button
                    key="invoke"
                    type="link"
                    icon={<PlayCircleOutlined />}
                    disabled={!item.enabled}
                    onClick={() => openInvokeModal(item)}
                  >
                    调用
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text strong>{item.name}</Text>
                      <Tag color={typeColorMap[item.nps_type]}>
                        {item.nps_type}
                      </Tag>
                      {item.enabled ? (
                        <Tag color="green">已启用</Tag>
                      ) : (
                        <Tag color="default">已禁用</Tag>
                      )}
                    </Space>
                  }
                  description={
                    <Space
                      direction="vertical"
                      size={4}
                      style={{ width: '100%' }}
                    >
                      <Paragraph
                        type="secondary"
                        style={{ marginBottom: 0 }}
                        ellipsis={{ rows: 2, expandable: true }}
                      >
                        {item.description || '(无描述)'}
                      </Paragraph>
                      <Space size={16} wrap>
                        <Text type="secondary">
                          调用次数: <Text strong>{item.call_count}</Text>
                        </Text>
                        <Text type="secondary">
                          <ClockCircleOutlined /> 最后调用:{' '}
                          {formatDateTime(item.last_called_at)}
                        </Text>
                        <Text type="secondary">
                          参数: {item.params.length} 个
                        </Text>
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Spin>
      </Card>

      {/* 注册 NPS 的 Drawer（通过 props.onSubmit 回调注入 npsApi.registerNps） */}
      <NPSConfigDrawer
        open={drawerOpen}
        onClose={closeDrawer}
        onSubmit={handleDrawerSubmit}
        title="注册新 NPS"
        submitText={submitting ? '提交中...' : '注册'}
      />

      {/* 调用 NPS 的弹窗：动态生成入参表单 / 展示返回结果 */}
      <Modal
        title={
          invokeResult
            ? `调用结果 - ${invokeResult.npsName}`
            : `调用 NPS - ${invokingNps?.name ?? ''}`
        }
        open={invokeModalOpen}
        confirmLoading={invoking}
        onCancel={() => {
          setInvokeModalOpen(false);
          setInvokeResult(null);
          setInvokingNps(null);
        }}
        onOk={
          invokeResult
            ? () => {
                setInvokeModalOpen(false);
                setInvokeResult(null);
                setInvokingNps(null);
              }
            : handleInvoke
        }
        okText={invokeResult ? '关闭' : '提交调用'}
        cancelText="取消"
        width={640}
        destroyOnClose
      >
        {invokeResult ? (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="NPS">
              {invokeResult.npsName}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag
                color={invokeResult.status === 'success' ? 'green' : 'red'}
              >
                {invokeResult.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="执行时间">
              {formatDateTime(invokeResult.executed_at)}
            </Descriptions.Item>
            <Descriptions.Item label="调用参数">
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(invokeResult.args, null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="返回值">
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(invokeResult.result, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Form form={invokeForm} layout="vertical">
            <Text type="secondary">
              根据 NPS 配置 ({invokingNps?.params.length ?? 0} 个参数)
              动态生成入参表单：
            </Text>
            {invokingNps && invokingNps.params.length === 0 && (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="该 NPS 没有声明参数"
                style={{ marginTop: 16 }}
              />
            )}
            {invokingNps &&
              invokingNps.params.map((p) => (
                <Form.Item
                  key={p.key}
                  name={p.key}
                  label={p.key}
                  style={{ marginTop: 12 }}
                >
                  <TextArea rows={2} placeholder={`参数值 (${p.key})`} />
                </Form.Item>
              ))}
          </Form>
        )}
      </Modal>
    </div>
  );
};

export default NPSPage;
