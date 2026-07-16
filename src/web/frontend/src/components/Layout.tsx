/**
 * AppLayout - 全局壳布局(Sider + Header + Content)
 *
 * Stage B.1 移动端降级:
 *  - 监听 window.innerWidth,当 < 768px 时不渲染主布局
 *  - 改用 antd Result 组件显示"请使用桌面端访问"提示
 *  - 提供"刷新重试"按钮,方便用户切回桌面后手动验证
 *  - SSR 安全:用 typeof window 兜底,避免在非浏览器环境崩溃
 *
 * 注意:本降级是软提示,实际渲染层(echarts 等)对窄屏并不友好,因此
 * 显式拦截比"勉强渲染"更稳妥。
 */

import React, { useEffect, useState } from 'react';
import { Layout, Menu, Badge, Result, Button } from 'antd';
import {
  MessageOutlined,
  BugOutlined,
  BookOutlined,
  CalendarOutlined,
  AlertOutlined,
  StarOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';

const { Sider, Header, Content } = Layout;

/** 移动端判断阈值(像素) */
const MOBILE_BREAKPOINT = 768;

type MenuItem = {
  key: string;
  label: string;
  icon: React.ReactNode;
};

const menuItems: MenuItem[] = [
  { key: '/chat', label: 'Chat', icon: <MessageOutlined /> },
  { key: '/debug', label: 'Debug', icon: <BugOutlined /> },
  { key: '/knowledge', label: 'Knowledge', icon: <BookOutlined /> },
  { key: '/schedule', label: 'Schedule', icon: <CalendarOutlined /> },
  { key: '/event', label: 'Event', icon: <AlertOutlined /> },
  { key: '/nps', label: 'NPS', icon: <StarOutlined /> },
  { key: '/database', label: 'Database', icon: <DatabaseOutlined /> },
  { key: '/creative', label: 'Creative', icon: <ThunderboltOutlined /> },
  { key: '/settings', label: '系统设置', icon: <SettingOutlined /> },
];

/** SSR 安全的初始窗口宽度(默认按桌面端,避免水合不一致) */
function getInitialWidth(): number {
  if (typeof window === 'undefined') return 1280;
  return window.innerWidth;
}

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  // 移动端检测:< 768px 视为移动端
  const [isMobile, setIsMobile] = useState<boolean>(
    () => getInitialWidth() < MOBILE_BREAKPOINT
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const handler = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  const selectedKey =
    menuItems.find((item) => location.pathname.startsWith(item.key))?.key ?? '/chat';

  // 移动端降级:不渲染主布局,改用 Result 提示用户
  if (isMobile) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <Result
          status="warning"
          title="请使用桌面端访问"
          subTitle={`Neo Agent Web GUI 当前仅支持 ≥ ${MOBILE_BREAKPOINT}px 屏幕宽度,移动端体验将在后续版本提供。`}
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              刷新重试
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <Layout className="min-h-screen">
      <Sider width={200} theme="dark" breakpoint="lg" collapsible>
        <div className="flex items-center justify-center h-16 text-white text-xl font-bold tracking-wide">
          Neo Agent
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems.map((item) => ({
            key: item.key,
            icon: item.icon,
            label: item.label,
          }))}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="flex items-center justify-between bg-white px-6 shadow-sm">
          <div className="text-lg font-semibold text-gray-800">Neo Agent 控制台</div>
          <div className="flex items-center gap-2">
            <Badge status="success" text="服务正常" />
          </div>
        </Header>
        <Content className="m-4 p-4 bg-white rounded shadow-sm">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
