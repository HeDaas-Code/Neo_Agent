// Shared types for the Creative page.
// 与后端 src/web/backend/schemas/creative.py 的 Pydantic 模型字段对齐。

// 业务状态：前端 UI 显式支持的子集。后端还可能返回 'drafting' / 'finished'，
// 会在 UI 层做归一化映射。
export type CreativeProjectStatus =
  | 'active'
  | 'completed'
  | 'paused'
  | 'drafting'
  | 'finished';

export interface CharacterRelation {
  target: string;
  relation: string;
}

export interface Character {
  uuid: string;
  name: string;
  role: string;
  description: string;
  relations: CharacterRelation[];
}

export interface Chapter {
  uuid: string;
  chapter_title: string;
  word_count: number;
  content: string;
}

export interface StoryBible {
  // 详情视图必备字段
  characters: Character[];
  worldview: string;
  chapters: Chapter[];
  // 详情视图扩展字段（后端会一并返回，UI 可选用）
  mainline_direction?: string;
  active_themes?: string[];
  unresolved_threads?: string[];
  resolved_threads?: string[];
  important_facts?: string[];
  next_direction?: string;
  recent_keywords?: string[];
}

export interface CreativeProject {
  // 列表与详情通用字段
  uuid: string;
  title: string;
  status: CreativeProjectStatus;
  word_count: number;
  created_at: string;
  updated_at: string;
  story_bible: StoryBible | null;
  // 详情扩展字段（后端 CreativeProject 提供）
  current_chars?: number;
  target_chars?: number;
  chapter_count?: number;
  work_type?: string;
  premise?: string;
  tone?: string;
  point_of_view?: string;
  inspiration_source?: string;
  outline?: unknown[];
  characters?: unknown[];
  draft_chunks?: unknown[];
  next_advance_at?: string | null;
  last_advanced_at?: string | null;
}
