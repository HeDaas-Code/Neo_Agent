import React, { useEffect } from 'react';
import {
  Drawer,
  Form,
  Input,
  Select,
  Switch,
  Button,
  Space,
  Divider,
  Typography,
  Empty,
  Card,
} from 'antd';
import { PlusOutlined, MinusCircleOutlined } from '@ant-design/icons';
import type { NPSType, NPSParam, NPSConfigFormValues } from '../types/nps';

const { TextArea } = Input;
const { Text } = Typography;

export interface NPSConfigDrawerProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (values: NPSConfigFormValues) => void;
  initialValues?: Partial<NPSConfigFormValues>;
  title?: string;
  submitText?: string;
}

const defaultValues: NPSConfigFormValues = {
  name: '',
  description: '',
  nps_type: 'function',
  params: [],
  enabled: true,
};

const ParamKeyValueEditor: React.FC = () => {
  const form = Form.useFormInstance();
  const params: NPSParam[] = (form.getFieldValue('params') as NPSParam[] | undefined) ?? [];

  const updateParams = (next: NPSParam[]) => {
    form.setFieldValue('params', next);
  };

  const addRow = () => {
    updateParams([...params, { key: '', value: '' }]);
  };

  const removeRow = (idx: number) => {
    updateParams(params.filter((_, i) => i !== idx));
  };

  const updateRow = (idx: number, patch: Partial<NPSParam>) => {
    updateParams(params.map((p, i) => (i === idx ? { ...p, ...patch } : p)));
  };

  return (
    <div>
      {params.length === 0 && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={<span style={{ color: '#999' }}>暂无参数，点击下方按钮添加</span>}
          style={{ margin: '12px 0' }}
        />
      )}
      <Space direction="vertical" style={{ width: '100%' }} size={6}>
        {params.map((p, idx) => (
          <Space.Compact key={idx} style={{ width: '100%' }}>
            <Input
              placeholder="key"
              style={{ width: '40%' }}
              value={p.key}
              onChange={(e) => updateRow(idx, { key: e.target.value })}
            />
            <Input
              placeholder="value"
              style={{ width: 'calc(60% - 32px)' }}
              value={p.value}
              onChange={(e) => updateRow(idx, { value: e.target.value })}
            />
            <Button
              type="text"
              danger
              icon={<MinusCircleOutlined />}
              onClick={() => removeRow(idx)}
              aria-label="删除参数"
            />
          </Space.Compact>
        ))}
      </Space>
      <Button
        type="dashed"
        block
        icon={<PlusOutlined />}
        onClick={addRow}
        style={{ marginTop: 8 }}
      >
        添加参数
      </Button>
    </div>
  );
};

const NPSConfigDrawer: React.FC<NPSConfigDrawerProps> = ({
  open,
  onClose,
  onSubmit,
  initialValues,
  title = '注册新 NPS',
  submitText = '提交',
}) => {
  const [form] = Form.useForm<NPSConfigFormValues>();

  useEffect(() => {
    if (open) {
      const merged: NPSConfigFormValues = {
        ...defaultValues,
        ...initialValues,
        params: (initialValues?.params ?? []) as NPSParam[],
      };
      form.setFieldsValue(merged);
    } else {
      form.resetFields();
    }
  }, [open, initialValues, form]);

  const handleFinish = (values: NPSConfigFormValues) => {
    onSubmit(values);
  };

  const handleReset = () => {
    const merged: NPSConfigFormValues = {
      ...defaultValues,
      ...initialValues,
      params: (initialValues?.params ?? []) as NPSParam[],
    };
    form.setFieldsValue(merged);
  };

  return (
    <Drawer
      title={title}
      width={520}
      open={open}
      onClose={onClose}
      destroyOnClose
      extra={
        <Space>
          <Button onClick={handleReset}>重置</Button>
          <Button type="primary" onClick={() => form.submit()}>
            {submitText}
          </Button>
        </Space>
      }
      footer={
        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button onClick={onClose}>取消</Button>
            <Button type="primary" onClick={() => form.submit()}>
              {submitText}
            </Button>
          </Space>
        </div>
      }
    >
      <Form<NPSConfigFormValues>
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={defaultValues}
        requiredMark="optional"
      >
        <Form.Item
          label="名称"
          name="name"
          rules={[
            { required: true, message: '请输入 NPS 名称' },
            { max: 64, message: '名称长度不能超过 64 个字符' },
            {
              pattern: /^[A-Za-z][A-Za-z0-9_]*$/,
              message: '仅允许字母、数字、下划线，且以字母开头',
            },
          ]}
        >
          <Input placeholder="例如: web_search" allowClear />
        </Form.Item>

        <Form.Item
          label="描述"
          name="description"
          rules={[{ max: 500, message: '描述长度不能超过 500 个字符' }]}
        >
          <TextArea rows={3} placeholder="简要说明该 NPS 的功能与使用场景" showCount maxLength={500} />
        </Form.Item>

        <Form.Item
          label="类型"
          name="nps_type"
          rules={[{ required: true, message: '请选择 NPS 类型' }]}
        >
          <Select<NPSType>
            options={[
              { label: 'function', value: 'function' },
              { label: 'tool', value: 'tool' },
              { label: 'workflow', value: 'workflow' },
            ]}
            placeholder="选择 NPS 类型"
          />
        </Form.Item>

        <Divider orientation="left" plain>
          参数 (Params)
        </Divider>
        <Form.Item
          label={null}
          name="params"
          valuePropName="value"
          tooltip="Key-Value 形式的入参定义；调用时将作为 JSON Schema 提示"
        >
          <ParamKeyValueEditor />
        </Form.Item>

        <Card size="small" style={{ background: '#fafafa', marginBottom: 16 }}>
          <Form.Item
            label="启用"
            name="enabled"
            valuePropName="checked"
            style={{ marginBottom: 0 }}
          >
            <Switch checkedChildren="ON" unCheckedChildren="OFF" />
          </Form.Item>
          <Text type="secondary" style={{ fontSize: 12 }}>
            禁用后该 NPS 将不会出现在调用列表中
          </Text>
        </Card>
      </Form>
    </Drawer>
  );
};

export default NPSConfigDrawer;
