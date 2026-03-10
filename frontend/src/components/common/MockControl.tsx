import React, { useState } from 'react';
import { FloatButton, Drawer, Radio, Space, Button, message, Tag, Typography, Divider } from 'antd';
import { BugOutlined, ClearOutlined } from '@ant-design/icons';

const { Text, Title } = Typography;

export const MockControl: React.FC = () => {
    const [open, setOpen] = useState(false);
    const currentCase = localStorage.getItem('VITE_MOCK_CASE') || 'NORMAL';

    const handleCaseChange = (val: string) => {
        if (val === 'NORMAL') {
            localStorage.removeItem('VITE_MOCK_CASE');
        } else {
            localStorage.setItem('VITE_MOCK_CASE', val);
        }
        message.success(`已切换到场景: ${val}，正在刷新页面...`);
        setTimeout(() => window.location.reload(), 800);
    };

    if (import.meta.env.MODE !== 'mock' && import.meta.env.VITE_USE_MOCK !== 'true') return null;

    return (
        <>
            <FloatButton
                icon={<BugOutlined />}
                type="primary"
                style={{ right: 24, bottom: 84 }}
                tooltip={<div>Mock 控制中心</div>}
                onClick={() => setOpen(true)}
            />
            <Drawer
                title="🛠️ Mock 特殊用例测试"
                placement="right"
                onClose={() => setOpen(false)}
                open={open}
                size="default"
            >
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <section>
                        <Title level={5}>常规状态</Title>
                        <Radio.Group value={currentCase} onChange={(e) => handleCaseChange(e.target.value)}>
                            <Space direction="vertical">
                                <Radio value="NORMAL"><Tag color="green">NORMAL</Tag> 正常 Mock 数据</Radio>
                                <Radio value="EMPTY_STATE"><Tag color="default">EMPTY_STATE</Tag> 空数据状态</Radio>
                            </Space>
                        </Radio.Group>
                    </section>

                    <Divider />

                    <section>
                        <Title level={5}>异常 / 边界测试</Title>
                        <Radio.Group value={currentCase} onChange={(e) => handleCaseChange(e.target.value)}>
                            <Space direction="vertical">
                                <Radio value="ERROR_500"><Tag color="red">ERROR_500</Tag> 服务器内部错误</Radio>
                                <Radio value="ERROR_403"><Tag color="orange">ERROR_403</Tag> 权限拒绝</Radio>
                                <Radio value="LONG_LATENCY"><Tag color="blue">LONG_LATENCY</Tag> 高延迟 (5s)</Radio>
                                <Radio value="MALFORMED_DATA"><Tag color="magenta">MALFORMED</Tag> 异常字段/数据</Radio>
                                <Radio value="MAX_CONTENT"><Tag color="purple">MAX_CONTENT</Tag> 极长文本/大数据</Radio>
                            </Space>
                        </Radio.Group>
                    </section>

                    <Divider />

                    <Button
                        block
                        icon={<ClearOutlined />}
                        onClick={() => {
                            localStorage.removeItem('VITE_MOCK_CASE');
                            window.location.reload();
                        }}
                    >
                        重置回标准后端
                    </Button>
                </Space>

                <div style={{ marginTop: 40, padding: 12, background: 'var(--hm-color-bg-elevated)', borderRadius: 8 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        选用特殊用例后，拦截器会强制所有请求返回对应的异常数据，用于验证前端的容错处理和 Loading 状态。
                    </Text>
                </div>
            </Drawer>
        </>
    );
};
