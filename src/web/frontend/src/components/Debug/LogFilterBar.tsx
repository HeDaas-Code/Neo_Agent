/**
 * LogFilterBar - client-side filter controls for the debug log viewer.
 *
 * Three controls, all controlled by the parent via the `value` / `onChange`
 * contract so the filtering logic stays in the page that owns the data:
 *
 *   1. Module substring match (`Input`)
 *   2. Level multi-select (`Select mode="multiple"`) — INFO / WARN / ERROR / DEBUG
 *   3. Time range (`DatePicker.RangePicker`) — from / to
 *
 * Convention: an empty `levels` array means "match all levels" (no filter).
 * The parent is responsible for translating this state into a `filter()`
 * predicate over the raw log list.
 */

import React from 'react';
import { Input, Select, DatePicker, Space } from 'antd';
import type { Dayjs } from 'dayjs';

export const ALL_LOG_LEVELS = ['INFO', 'WARN', 'ERROR', 'DEBUG'] as const;
export type LogLevelOption = (typeof ALL_LOG_LEVELS)[number];

export interface LogFilterValue {
  levels: LogLevelOption[];
  module: string;
  range: [Dayjs | null, Dayjs | null] | null;
}

export interface LogFilterBarProps {
  value: LogFilterValue;
  onChange: (next: LogFilterValue) => void;
  /**
   * Optional list of known module names. When provided, the Input
   * is augmented with a native <datalist> for browser-side autocomplete.
   */
  moduleOptions?: string[];
}

const LogFilterBar: React.FC<LogFilterBarProps> = ({ value, onChange, moduleOptions }) => {
  // Stable, collision-resistant id for the native datalist.
  const datalistId = React.useMemo(
    () => `debug-modules-${Math.random().toString(36).slice(2, 8)}`,
    []
  );

  return (
    <Space wrap>
      <Input
        placeholder="按模块筛选 (子串匹配)"
        value={value.module}
        onChange={(e) => onChange({ ...value, module: e.target.value })}
        allowClear
        style={{ width: 220 }}
        list={moduleOptions && moduleOptions.length > 0 ? datalistId : undefined}
      />
      {moduleOptions && moduleOptions.length > 0 && (
        <datalist id={datalistId}>
          {moduleOptions.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>
      )}
      <Select<LogLevelOption[]>
        mode="multiple"
        allowClear
        maxTagCount="responsive"
        placeholder="选择级别 (空 = 全部)"
        value={value.levels}
        onChange={(levels) =>
          // Defensive cast: antd's SelectValue widens to string|number|LabeledValue,
          // but the parent only ever feeds LogLevelOption values.
          onChange({ ...value, levels: levels as LogLevelOption[] })
        }
        style={{ minWidth: 220 }}
        options={ALL_LOG_LEVELS.map((l) => ({ value: l, label: l }))}
      />
      <DatePicker.RangePicker
        showTime
        value={value.range as any}
        onChange={(r) =>
          onChange({ ...value, range: r as [Dayjs | null, Dayjs | null] | null })
        }
        allowClear
      />
    </Space>
  );
};

export default LogFilterBar;
