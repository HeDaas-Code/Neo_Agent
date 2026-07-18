import { useEffect } from 'react';
import {
  Button,
  DatePicker,
  Drawer,
  Form,
  Input,
  Radio,
  Select,
  Space,
  Switch,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import type {
  Schedule,
  SchedulePriority,
  ScheduleType,
} from '../api/schedule';

const { TextArea } = Input;

/**
 * ScheduleForm —— 新建 / 编辑日程的抽屉表单。
 *
 * 提交时通过 onSubmit 把已格式化的 SchedulePayload 抛给父组件。
 * 编辑场景下,父组件传入 initialValues 即可预填表单。
 */

export interface ScheduleFormValues {
  title: string;
  description?: string;
  start_time: Dayjs;
  end_time: Dayjs;
  priority: SchedulePriority;
  schedule_type: ScheduleType;
  is_collaborative: boolean;
  collaborator_name?: string;
}

export interface ScheduleFormProps {
  open: boolean;
  /** 编辑时传入;新建时省略 */
  initial?: Schedule;
  /** 提交中状态:为 true 时禁用保存按钮并显示 loading */
  submitting?: boolean;
  onClose: () => void;
  /** 提交回调,父组件负责实际创建/更新 (后端 API 联调后接入) */
  onSubmit: (values: ScheduleFormValues) => void;
}

const PRIORITY_OPTIONS: { label: string; value: SchedulePriority }[] = [
  { label: '低', value: 'low' },
  { label: '普通', value: 'normal' },
  { label: '高', value: 'high' },
];

const TYPE_OPTIONS: { label: string; value: ScheduleType }[] = [
  { label: '个人', value: 'personal' },
  { label: '工作', value: 'work' },
  { label: '家庭', value: 'family' },
];

export default function ScheduleForm({
  open,
  initial,
  submitting,
  onClose,
  onSubmit,
}: ScheduleFormProps): JSX.Element {
  const [form] = Form.useForm<ScheduleFormValues>();

  /**
   * 打开抽屉时同步表单:编辑模式预填 initial,新建模式重置。
   */
  useEffect(() => {
    if (!open) return;
    if (initial) {
      form.setFieldsValue({
        title: initial.title,
        description: initial.description,
        start_time: dayjs(initial.start_time),
        end_time: dayjs(initial.end_time),
        priority: initial.priority,
        schedule_type: initial.schedule_type,
        is_collaborative: initial.is_collaborative,
        collaborator_name: initial.collaborator_name,
      });
    } else {
      form.resetFields();
    }
  }, [open, initial, form]);

  const isCollaborative = Form.useWatch('is_collaborative', form);

  const handleOk = async (): Promise<void> => {
    try {
      const values = await form.validateFields();
      onSubmit(values);
    } catch {
      /* antd 校验失败,validateFields 会 reject */
    }
  };

  const title = initial ? '编辑日程' : '新建日程';

  return (
    <Drawer
      title={title}
      open={open}
      onClose={onClose}
      width={480}
      destroyOnClose
      extra={
        <Space>
          <Button onClick={() => form.resetFields()}>重置</Button>
          <Button onClick={onClose}>取消</Button>
          <Button
            type="primary"
            onClick={handleOk}
            loading={submitting}
            disabled={submitting}
          >
            保存
          </Button>
        </Space>
      }
    >
      <Form<ScheduleFormValues>
        form={form}
        layout="vertical"
        initialValues={{
          priority: 'normal',
          schedule_type: 'personal',
          is_collaborative: false,
        }}
      >
        <Form.Item
          label="标题"
          name="title"
          rules={[{ required: true, message: '请输入日程标题' }]}
        >
          <Input placeholder="例如:周会 / 健身 / 家庭聚餐" maxLength={120} />
        </Form.Item>

        <Form.Item label="描述" name="description">
          <TextArea rows={3} placeholder="可选,详细说明" maxLength={500} />
        </Form.Item>

        <Form.Item
          label="开始时间"
          name="start_time"
          rules={[{ required: true, message: '请选择开始时间' }]}
        >
          <DatePicker
            showTime={{ format: 'HH:mm' }}
            format="YYYY-MM-DD HH:mm"
            style={{ width: '100%' }}
          />
        </Form.Item>

        <Form.Item
          label="结束时间"
          name="end_time"
          dependencies={['start_time']}
          rules={[
            { required: true, message: '请选择结束时间' },
            ({ getFieldValue }) => ({
              validator(_rule, value: Dayjs | undefined) {
                if (!value) return Promise.resolve();
                const start = getFieldValue('start_time') as Dayjs | undefined;
                if (start && value.isBefore(start)) {
                  return Promise.reject(new Error('结束时间不能早于开始时间'));
                }
                return Promise.resolve();
              },
            }),
          ]}
        >
          <DatePicker
            showTime={{ format: 'HH:mm' }}
            format="YYYY-MM-DD HH:mm"
            style={{ width: '100%' }}
          />
        </Form.Item>

        <Form.Item
          label="优先级"
          name="priority"
          rules={[{ required: true, message: '请选择优先级' }]}
        >
          <Radio.Group options={PRIORITY_OPTIONS} optionType="button" />
        </Form.Item>

        <Form.Item
          label="类型"
          name="schedule_type"
          rules={[{ required: true, message: '请选择类型' }]}
        >
          <Select options={TYPE_OPTIONS} />
        </Form.Item>

        <Form.Item
          label="是否协作日程"
          name="is_collaborative"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        {isCollaborative && (
          <Form.Item
            label="协作人"
            name="collaborator_name"
            rules={[{ required: true, message: '请填写协作人' }]}
          >
            <Input placeholder="例如:王晓" maxLength={60} />
          </Form.Item>
        )}
      </Form>
    </Drawer>
  );
}
