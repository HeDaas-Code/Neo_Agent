/**
 * Settings 页面 - v3.1.0
 * ======================
 *
 * 三个卡片:
 *  - Card 1: LLM 配置(只读展示 provider / base_url / model_name / temperature / max_tokens / timeout)
 *  - Card 2: 测试连接(按钮 + 结果展示 ok/error + 延迟)
 *  - Card 3: 会话管理(跳转到 /chat)
 */

import { useEffect, useState } from 'react';
import {
  Card,
  Button,
  Descriptions,
  Tag,
  Alert,
  Space,
  Spin,
  Typography,
  Result,
  message,
} from 'antd';
import {
  ReloadOutlined,
  ThunderboltOutlined,
  MessageOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getConfig, testConnection, type LLMConfig, type LLMTestResult } from '../../api/llm';

const { Title, Paragraph } = Typography;

export default function SettingsPage() {
  const navigate = useNavigate();
  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [configLoading, setConfigLoading] = useState<boolean>(false);
  const [configError, setConfigError] = useState<string | null>(null);

  const [testResult, setTestResult] = useState<LLMTestResult | null>(null);
  const [testLoading, setTestLoading] = useState<boolean>(false);

  const loadConfig = async () => {
    setConfigLoading(true);
    setConfigError(null);
    try {
      const cfg = await getConfig();
      setConfig(cfg);
    } catch (err) {
      setConfigError((err as Error).message);
    } finally {
      setConfigLoading(false);
    }
  };

  useEffect(() => {
    void loadConfig();
  }, []);

  const onTestConnection = async () => {
    setTestLoading(true);
    setTestResult(null);
    try {
      const result = await testConnection('ping');
      setTestResult(result);
      if (result.ok) {
        message.success(`连接成功 (${result.latency_ms ?? 0} ms)`);
      } else {
        message.error(`连接失败: ${result.error ?? '未知错误'}`);
      }
    } catch (err) {
      const errMsg = (err as Error).message;
      setTestResult({ ok: false, error: errMsg });
      message.error(`测试请求失败: ${errMsg}`);
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div>
        <Title level={3} className="!mb-1">
          系统设置
        </Title>
        <Paragraph type="secondary" className="!mb-0">
          v3.1.0 新增:LLM 多供应商配置与会话持久化。修改 .env 后需重启后端生效。
        </Paragraph>
      </div>

      {/* Card 1: LLM 配置 */}
      <Card
        title={
          <Space>
            <span>LLM 配置</span>
            {config ? (
              <Tag color={config.valid ? 'success' : 'error'} icon={
                config.valid ? <CheckCircleOutlined /> : <CloseCircleOutlined />
              }>
                {config.valid ? '有效' : '无效'}
              </Tag>
            ) : null}
          </Space>
        }
        extra={
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => void loadConfig()}
            loading={configLoading}
          >
            刷新
          </Button>
        }
      >
        {configLoading && !config ? (
          <div className="flex items-center justify-center py-6">
            <Spin />
          </div>
        ) : configError ? (
          <Alert
            type="error"
            showIcon
            message="加载 LLM 配置失败"
            description={configError}
          />
        ) : config ? (
          <Descriptions
            column={2}
            size="small"
            bordered
            items={[
              { key: 'provider', label: 'Provider', children: config.provider || '—' },
              { key: 'base_url', label: 'Base URL', children: config.base_url || '—' },
              { key: 'model_name', label: 'Model', children: config.model_name || '—' },
              {
                key: 'temperature',
                label: 'Temperature',
                children: typeof config.temperature === 'number' ? config.temperature.toFixed(2) : '—',
              },
              {
                key: 'max_tokens',
                label: 'Max Tokens',
                children: typeof config.max_tokens === 'number' ? String(config.max_tokens) : '—',
              },
              {
                key: 'timeout',
                label: 'Timeout (s)',
                children: typeof config.timeout === 'number' ? String(config.timeout) : '—',
              },
              {
                key: 'api_key',
                label: 'API Key',
                children: config.api_key_set ? <Tag color="green">已配置</Tag> : <Tag color="red">未配置</Tag>,
              },
            ]}
          />
        ) : (
          <Alert type="info" message="暂无配置" />
        )}
      </Card>

      {/* Card 2: 测试连接 */}
      <Card
        title={
          <Space>
            <ThunderboltOutlined />
            <span>测试连接</span>
          </Space>
        }
      >
        <Space direction="vertical" size="middle" className="w-full">
          <Paragraph type="secondary" className="!mb-0">
            用当前 LLM 配置发送一次 "ping" 调用，验证连通性与延迟。
          </Paragraph>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={testLoading}
            onClick={() => void onTestConnection()}
          >
            测试连接
          </Button>

          {testResult ? (
            testResult.ok ? (
              <Alert
                type="success"
                showIcon
                message={`连接成功 (${testResult.latency_ms ?? 0} ms)`}
                description={
                  testResult.sample_response ? (
                    <span>
                      样例回复: <code>{testResult.sample_response.slice(0, 100)}</code>
                    </span>
                  ) : undefined
                }
              />
            ) : (
              <Alert
                type="error"
                showIcon
                message="连接失败"
                description={testResult.error ?? '未知错误'}
              />
            )
          ) : null}
        </Space>
      </Card>

      {/* Card 3: 会话管理 */}
      <Card
        title={
          <Space>
            <MessageOutlined />
            <span>会话管理</span>
          </Space>
        }
      >
        <Space direction="vertical" size="middle" className="w-full">
          <Paragraph type="secondary" className="!mb-0">
            v3.1.0 新增:聊天会话与消息持久化存储到数据库(<code>chat_sessions</code> / <code>chat_messages</code>)。
            在 Chat 页面顶部点击「会话」按钮可新建/切换/删除会话;刷新页面后会自动恢复最近一次会话。
          </Paragraph>
          <Button
            type="default"
            icon={<MessageOutlined />}
            onClick={() => navigate('/chat')}
          >
            跳转到 Chat 页面
          </Button>
          {configError || !config?.valid ? (
            <Alert
              type="warning"
              showIcon
              message="提示"
              description="如未配置 LLM API Key，聊天时 /api/llm/test 会返回错误。请先在 .env 中设置 LLM_API_KEY。"
            />
          ) : null}
        </Space>
      </Card>
    </div>
  );
}

export const SettingsPageFallback: React.FC = () => (
  <Result
    status="info"
    title="Settings"
    subTitle="未挂载"
    extra={<Button type="primary" onClick={() => (window.location.href = '/chat')}>回到 Chat</Button>}
  />
);
