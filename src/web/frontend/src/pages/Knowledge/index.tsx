import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Row,
  Segmented,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import KnowledgeGraph from '../../components/KnowledgeGraph';
import * as knowledgeApi from '../../api/knowledge';
import type { Entity, EntityCategory, Relation } from '../../types/knowledge';

const { Title, Text, Paragraph } = Typography;

const CATEGORY_LABELS: Record<EntityCategory, string> = {
  person: '人物',
  project: '项目',
  concept: '概念',
  location: '地点',
  organization: '组织',
  event: '事件',
};

const CATEGORY_COLORS: Record<EntityCategory, string> = {
  person: 'blue',
  project: 'purple',
  concept: 'cyan',
  location: 'green',
  organization: 'orange',
  event: 'magenta',
};

type FilterCategory = EntityCategory | 'all';

export default function KnowledgePage(): JSX.Element {
  const [entities, setEntities] = useState<Entity[]>([]);
  // 后端暂未提供 /api/knowledge/relations 端点,relations 始终置空,
  // 关系图组件会自然渲染为无边的散点;不影响列表/详情/统计。
  const [relations] = useState<Relation[]>([]);
  const [searchText, setSearchText] = useState('');
  const [filter, setFilter] = useState<FilterCategory>('all');
  const [selectedUuid, setSelectedUuid] = useState<string | undefined>();
  const [createOpen, setCreateOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm<{
    name: string;
    category: EntityCategory;
    description: string;
  }>();

  /**
   * 加载实体列表(GET /api/knowledge/search?q=&limit=)。
   * 通过 knowledgeApi.searchEntities('') 在空关键词时回退到 listEntities。
   */
  const loadEntities = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const rows = await knowledgeApi.searchEntities('', 200);
      setEntities(rows);
      setSelectedUuid((prev) => prev ?? rows[0]?.uuid);
    } catch {
      // 错误提示已由 knowledgeApi 内部 message.error 处理
      setEntities([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadEntities();
  }, [loadEntities]);

  const filteredEntities = useMemo(() => {
    const text = searchText.trim().toLowerCase();
    return entities.filter((e) => {
      if (filter !== 'all' && e.category !== filter) return false;
      if (!text) return true;
      return (
        e.name.toLowerCase().includes(text) ||
        e.description.toLowerCase().includes(text)
      );
    });
  }, [entities, searchText, filter]);

  const selectedEntity = useMemo(
    () => entities.find((e) => e.uuid === selectedUuid),
    [entities, selectedUuid],
  );

  const relatedEntities = useMemo(() => {
    if (!selectedEntity) return [] as Entity[];
    const ids = new Set(selectedEntity.related_uuids);
    return entities.filter((e) => ids.has(e.uuid));
  }, [selectedEntity, entities]);

  /** 刷新按钮:重新拉取列表 */
  const refresh = (): void => {
    void loadEntities();
  };

  /**
   * 删除实体(DELETE /api/knowledge/{uuid}),成功后重新拉取列表。
   */
  const handleDelete = async (uuid: string): Promise<void> => {
    try {
      await knowledgeApi.deleteEntity(uuid);
      // 删除成功后刷新列表,以保证与服务端一致
      await loadEntities();
      if (selectedUuid === uuid) {
        setSelectedUuid(undefined);
      }
    } catch {
      // 错误提示已由 knowledgeApi 内部处理
    }
  };

  /**
   * 新增实体(POST /api/knowledge),成功后关闭弹窗并刷新。
   */
  const handleCreate = async (): Promise<void> => {
    try {
      const values = await form.validateFields();
      await knowledgeApi.createEntity({
        name: values.name,
        category: values.category,
        description: values.description,
      });
      setCreateOpen(false);
      form.resetFields();
      // 创建后重新拉取,把新实体的 uuid 选上
      await loadEntities();
      // loadEntities 里只会把第一个 uuid 设为 selected,
      // 这里再尝试选中刚刚创建的那条
      setSelectedUuid((prev) => prev);
    } catch {
      /* 校验失败或 API 错误,前者由 antd 处理,后者已 message.error */
    }
  };

  const totalMentions = entities.reduce((sum, e) => sum + e.mention_count, 0);
  const avgConfidence =
    entities.length === 0
      ? 0
      : entities.reduce((sum, e) => sum + e.confidence, 0) / entities.length;

  return (
    <div className="space-y-4">
      {/* 顶部:统计 + 搜索 + 新增 */}
      <Card>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space size="middle" wrap>
              <Statistic title="实体数" value={entities.length} />
              <Statistic title="关系数" value={relations.length} />
              <Statistic title="总提及次数" value={totalMentions} />
              <Statistic
                title="平均置信度"
                value={(avgConfidence * 100).toFixed(0)}
                suffix="%"
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Input.Search
                allowClear
                placeholder="搜索实体名 / 描述"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                onSearch={(v) => setSearchText(v)}
                style={{ width: 240 }}
                enterButton={<SearchOutlined />}
              />
              <Button
                icon={<PlusOutlined />}
                type="primary"
                onClick={() => setCreateOpen(true)}
              >
                新增实体
              </Button>
              <Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
        <div className="mt-3">
          <Segmented<FilterCategory>
            value={filter}
            onChange={(v) => setFilter(v)}
            options={[
              { label: '全部', value: 'all' },
              { label: '人物', value: 'person' },
              { label: '项目', value: 'project' },
              { label: '概念', value: 'concept' },
              { label: '地点', value: 'location' },
              { label: '组织', value: 'organization' },
              { label: '事件', value: 'event' },
            ]}
          />
        </div>
      </Card>

      {/* 主体:左 列表 / 右 详情 */}
      <Row gutter={16}>
        <Col xs={24} md={10} lg={9}>
          <Card
            title={
              <Space>
                <Text strong>知识条目</Text>
                <Badge count={filteredEntities.length} showZero color="#1677ff" />
              </Space>
            }
            bodyStyle={{ padding: 0, maxHeight: 520, overflowY: 'auto' }}
          >
            <Spin spinning={loading}>
              {filteredEntities.length === 0 ? (
                <Empty
                  description={loading ? '加载中…' : '没有匹配的实体'}
                  className="my-6"
                />
              ) : (
                <List
                  dataSource={filteredEntities}
                  rowKey={(item) => item.uuid}
                  renderItem={(item) => (
                    <List.Item
                      className="px-4 cursor-pointer hover:bg-gray-50"
                      style={
                        item.uuid === selectedUuid
                          ? { background: '#e6f4ff' }
                          : undefined
                      }
                      onClick={() => setSelectedUuid(item.uuid)}
                      actions={[
                        <Button
                          key="edit"
                          type="text"
                          size="small"
                          icon={<EditOutlined />}
                          onClick={(e) => {
                            e.stopPropagation();
                            message.info(`编辑 ${item.name} (TODO:打开编辑表单)`);
                          }}
                        />,
                        <Popconfirm
                          key="del"
                          title="删除该实体?"
                          description="同时会移除其所有关系,且不可恢复。"
                          okText="删除"
                          cancelText="取消"
                          okButtonProps={{ danger: true }}
                          onConfirm={(e) => {
                            e?.stopPropagation();
                            void handleDelete(item.uuid);
                          }}
                          onCancel={(e) => e?.stopPropagation()}
                        >
                          <Button
                            type="text"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </Popconfirm>,
                      ]}
                    >
                      <List.Item.Meta
                        title={
                          <Space>
                            <Text strong>{item.name}</Text>
                            <Tag color={CATEGORY_COLORS[item.category]}>
                              {CATEGORY_LABELS[item.category]}
                            </Tag>
                          </Space>
                        }
                        description={
                          <Space size="small" wrap>
                            <Text type="secondary" className="text-xs">
                              置信度 {(item.confidence * 100).toFixed(0)}%
                            </Text>
                            <Text type="secondary" className="text-xs">
                              提及 {item.mention_count} 次
                            </Text>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              )}
            </Spin>
          </Card>
        </Col>

        <Col xs={24} md={14} lg={15}>
          <Card
            title={
              selectedEntity ? (
                <Space>
                  <Text strong>{selectedEntity.name}</Text>
                  <Tag color={CATEGORY_COLORS[selectedEntity.category]}>
                    {CATEGORY_LABELS[selectedEntity.category]}
                  </Tag>
                  <Text type="secondary" className="text-xs">
                    uuid: {selectedEntity.uuid}
                  </Text>
                </Space>
              ) : (
                '详情'
              )
            }
            bodyStyle={{ maxHeight: 520, overflowY: 'auto' }}
          >
            {!selectedEntity ? (
              <Empty description="请在左侧选择一个实体" />
            ) : (
              <div className="space-y-3">
                <Descriptions size="small" column={2} bordered>
                  <Descriptions.Item label="置信度">
                    {(selectedEntity.confidence * 100).toFixed(0)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="提及次数">
                    {selectedEntity.mention_count}
                  </Descriptions.Item>
                  <Descriptions.Item label="更新时间">
                    {new Date(selectedEntity.updated_at).toLocaleString()}
                  </Descriptions.Item>
                  <Descriptions.Item label="分类">
                    {CATEGORY_LABELS[selectedEntity.category]}
                  </Descriptions.Item>
                </Descriptions>

                <div>
                  <Title level={5}>描述</Title>
                  <Alert
                    type="info"
                    showIcon
                    message="当前使用简化文本渲染,完整 Markdown 渲染将随后端 API 联调后切换。"
                    className="mb-2"
                  />
                  <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                    {selectedEntity.description}
                  </Paragraph>
                </div>

                {Object.keys(selectedEntity.metadata).length > 0 && (
                  <div>
                    <Title level={5}>元数据</Title>
                    <Descriptions size="small" column={2} bordered>
                      {Object.entries(selectedEntity.metadata).map(([k, v]) => (
                        <Descriptions.Item key={k} label={k}>
                          {String(v)}
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  </div>
                )}

                <div>
                  <Title level={5}>相关实体</Title>
                  {relatedEntities.length === 0 ? (
                    <Text type="secondary">无</Text>
                  ) : (
                    <Space wrap>
                      {relatedEntities.map((e) => (
                        <Tag
                          key={e.uuid}
                          color={CATEGORY_COLORS[e.category]}
                          style={{ cursor: 'pointer' }}
                          onClick={() => setSelectedUuid(e.uuid)}
                        >
                          {e.name}
                        </Tag>
                      ))}
                    </Space>
                  )}
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 底部:关系图 */}
      <Card title="实体关系图">
        <KnowledgeGraph
          entities={entities}
          relations={relations}
          selectedUuid={selectedUuid}
          onNodeClick={(uuid) => setSelectedUuid(uuid)}
          height={460}
        />
      </Card>

      {/* 新增实体弹窗 */}
      <Modal
        title="新增实体"
        open={createOpen}
        onCancel={() => {
          setCreateOpen(false);
          form.resetFields();
        }}
        onOk={handleCreate}
        okText="创建"
        cancelText="取消"
        destroyOnClose
        confirmLoading={loading}
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入实体名' }]}
          >
            <Input placeholder="例如:Neo_Agent" />
          </Form.Item>
          <Form.Item
            label="分类"
            name="category"
            initialValue="concept"
            rules={[{ required: true, message: '请选择分类' }]}
          >
            <Input placeholder="person / project / concept / ..." />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={4} placeholder="可选,支持 Markdown" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
