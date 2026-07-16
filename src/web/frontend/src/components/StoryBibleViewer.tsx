import React, { useMemo } from 'react';
import { Tabs, List, Typography, Tag, Card, Space, Empty } from 'antd';
import { UserOutlined, GlobalOutlined, ReadOutlined } from '@ant-design/icons';
import type { StoryBible, Character, Chapter } from '@/types/creative';

const { Title, Paragraph, Text } = Typography;

export interface StoryBibleViewerProps {
  storyBible: StoryBible;
}

// A lightweight markdown renderer. Intentionally not a full commonmark
// implementation: it covers the subset used by mock worldview content
// (headings, paragraphs, bold, italic, inline code, ordered/unordered
// lists, horizontal rules, blockquotes). Avoids adding a markdown
// runtime dependency.
const renderInline = (raw: string): React.ReactNode[] => {
  const nodes: React.ReactNode[] = [];
  let buffer = '';
  let i = 0;
  let key = 0;
  const flushBuffer = () => {
    if (buffer) {
      nodes.push(<span key={`t-${key++}`}>{buffer}</span>);
      buffer = '';
    }
  };
  while (i < raw.length) {
    const ch = raw[i];
    if (ch === '`') {
      const end = raw.indexOf('`', i + 1);
      if (end !== -1) {
        flushBuffer();
        nodes.push(
          <code
            key={`c-${key++}`}
            style={{
              background: '#f5f5f5',
              padding: '0 4px',
              borderRadius: 3,
              fontSize: 12,
            }}
          >
            {raw.slice(i + 1, end)}
          </code>,
        );
        i = end + 1;
        continue;
      }
    }
    if (ch === '*' && raw[i + 1] === '*') {
      const end = raw.indexOf('**', i + 2);
      if (end !== -1) {
        flushBuffer();
        nodes.push(<strong key={`b-${key++}`}>{raw.slice(i + 2, end)}</strong>);
        i = end + 2;
        continue;
      }
    }
    if (ch === '*') {
      const end = raw.indexOf('*', i + 1);
      if (end !== -1 && raw[end + 1] !== '*') {
        flushBuffer();
        nodes.push(<em key={`i-${key++}`}>{raw.slice(i + 1, end)}</em>);
        i = end + 1;
        continue;
      }
    }
    buffer += ch;
    i += 1;
  }
  flushBuffer();
  return nodes;
};

const renderMarkdown = (md: string): React.ReactNode => {
  const lines = md.split('\n');
  const blocks: React.ReactNode[] = [];
  let listBuffer: string[] = [];
  let listType: 'ul' | 'ol' | null = null;
  let key = 0;

  const flushList = () => {
    if (listBuffer.length === 0 || !listType) return;
    const items = listBuffer.map((item, idx) => (
      <li key={`li-${key}-${idx}`}>{renderInline(item)}</li>
    ));
    if (listType === 'ul') {
      blocks.push(
        <ul key={`ul-${key++}`} style={{ paddingLeft: 20 }}>
          {items}
        </ul>,
      );
    } else {
      blocks.push(
        <ol key={`ol-${key++}`} style={{ paddingLeft: 20 }}>
          {items}
        </ol>,
      );
    }
    listBuffer = [];
    listType = null;
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (line.trim() === '') {
      flushList();
      continue;
    }
    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(line);
    if (headingMatch) {
      flushList();
      const level = headingMatch[1].length;
      const content = headingMatch[2];
      const sizes: Record<number, number> = { 1: 24, 2: 20, 3: 18, 4: 16, 5: 14, 6: 13 };
      blocks.push(
        <Title
          key={`h-${key++}`}
          level={level as 1 | 2 | 3 | 4 | 5}
          style={{ fontSize: sizes[level] ?? 14, marginTop: 16, marginBottom: 8 }}
        >
          {renderInline(content)}
        </Title>,
      );
      continue;
    }
    if (/^[-*_]{3,}$/.test(line.trim())) {
      flushList();
      blocks.push(<hr key={`hr-${key++}`} />);
      continue;
    }
    if (line.trim().startsWith('> ')) {
      flushList();
      blocks.push(
        <blockquote
          key={`q-${key++}`}
          style={{
            borderLeft: '3px solid #d9d9d9',
            paddingLeft: 12,
            color: '#595959',
            margin: '8px 0',
          }}
        >
          {renderInline(line.trim().slice(2))}
        </blockquote>,
      );
      continue;
    }
    const ulMatch = /^[-*]\s+(.*)$/.exec(line);
    if (ulMatch) {
      if (listType !== 'ul') flushList();
      listType = 'ul';
      listBuffer.push(ulMatch[1]);
      continue;
    }
    const olMatch = /^\d+\.\s+(.*)$/.exec(line);
    if (olMatch) {
      if (listType !== 'ol') flushList();
      listType = 'ol';
      listBuffer.push(olMatch[1]);
      continue;
    }
    flushList();
    blocks.push(
      <Paragraph key={`p-${key++}`} style={{ marginBottom: 8 }}>
        {renderInline(line)}
      </Paragraph>,
    );
  }
  flushList();
  return blocks;
};

const CharacterList: React.FC<{ characters: Character[] }> = ({ characters }) => {
  if (characters.length === 0) {
    return <Empty description="No characters yet" />;
  }
  return (
    <List
      itemLayout="vertical"
      dataSource={characters}
      renderItem={(c) => (
        <List.Item key={c.uuid}>
          <Card size="small" style={{ width: '100%' }}>
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <Space>
                <UserOutlined />
                <Text strong>{c.name}</Text>
                <Tag color="geekblue">{c.role}</Tag>
              </Space>
              <Paragraph style={{ marginBottom: 0 }}>{c.description}</Paragraph>
              {c.relations.length > 0 ? (
                <Space size={4} wrap>
                  <Text type="secondary">Relations:</Text>
                  {c.relations.map((r, idx) => (
                    <Tag key={`${c.uuid}-rel-${idx}`} color="purple">
                      {r.relation} → {r.target}
                    </Tag>
                  ))}
                </Space>
              ) : null}
            </Space>
          </Card>
        </List.Item>
      )}
    />
  );
};

const ChapterList: React.FC<{ chapters: Chapter[] }> = ({ chapters }) => {
  if (chapters.length === 0) {
    return <Empty description="No chapters yet" />;
  }
  return (
    <List
      itemLayout="vertical"
      dataSource={chapters}
      renderItem={(ch) => (
        <List.Item key={ch.uuid}>
          <Card size="small" style={{ width: '100%' }}>
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <Space>
                <ReadOutlined />
                <Text strong>{ch.chapter_title}</Text>
                <Tag color="cyan">{ch.word_count.toLocaleString()} words</Tag>
              </Space>
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                {ch.content}
              </Paragraph>
            </Space>
          </Card>
        </List.Item>
      )}
    />
  );
};

const WorldviewPanel: React.FC<{ worldview: string }> = ({ worldview }) => {
  const rendered = useMemo(() => renderMarkdown(worldview), [worldview]);
  return (
    <Card size="small">
      <Space>
        <GlobalOutlined />
        <Text strong>World bible</Text>
      </Space>
      <div style={{ marginTop: 12 }}>{rendered}</div>
    </Card>
  );
};

const StoryBibleViewer: React.FC<StoryBibleViewerProps> = ({ storyBible }) => {
  const tabItems = [
    {
      key: 'characters',
      label: (
        <Space>
          <UserOutlined />
          <span>Characters ({storyBible.characters.length})</span>
        </Space>
      ),
      children: <CharacterList characters={storyBible.characters} />,
    },
    {
      key: 'worldview',
      label: (
        <Space>
          <GlobalOutlined />
          <span>Worldview</span>
        </Space>
      ),
      children: <WorldviewPanel worldview={storyBible.worldview} />,
    },
    {
      key: 'chapters',
      label: (
        <Space>
          <ReadOutlined />
          <span>Chapters ({storyBible.chapters.length})</span>
        </Space>
      ),
      children: <ChapterList chapters={storyBible.chapters} />,
    },
  ];

  return (
    <Tabs defaultActiveKey="characters" items={tabItems} />
  );
};

export default StoryBibleViewer;
