
import React, { useState } from 'react';
import { Card, Form, Input, Button, Typography, App as AntApp } from 'antd';
import { UserOutlined, LockOutlined, RocketOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { tokenVault } from '../core/auth/TokenVault';

const { Title, Text } = Typography;

export const LoginPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const { message } = AntApp.useApp();
    const navigate = useNavigate();
    const location = useLocation();
    const setAuthenticated = useAuthStore((state) => state.setAuthenticated);

    // Get original target path or default to dashboard
    const from = (location.state as any)?.from || '/';

    const onFinish = async (values: any) => {
        setLoading(true);
        try {
            const { authApi } = await import('../services/authApi');
            const response: any = await authApi.login({
                username: values.username,
                password: values.password
            });

            // response.data is the JSON body returned by backend
            const { success, data: apiData, message: apiMessage } = response.data;

            if (success && apiData) {
                const { access_token, user } = apiData;
                tokenVault.setTokens(access_token, 'refresh-token', user.id);
                setAuthenticated(true, user);
                
                message.success('登录成功，正在进入系统...');
                navigate(from, { replace: true });
            } else {
                message.error('登录失败: ' + (apiMessage || '未知错误'));
            }
        } catch (error: any) {
            console.error('Login error:', error);
            message.error(error.message || '登录异常，请检查后端连接');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ 
            height: '100vh', 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            background: 'linear-gradient(135deg, #0A0E1A 0%, #111827 100%)',
            overflow: 'hidden',
            position: 'relative'
        }}>
            {/* Background Decoration */}
            <div style={{
                position: 'absolute',
                width: '400px',
                height: '400px',
                background: 'rgba(6, 214, 160, 0.05)',
                filter: 'blur(100px)',
                borderRadius: '50%',
                top: '10%',
                right: '10%'
            }} />

            <Card style={{ 
                width: 400, 
                background: 'rgba(31, 41, 55, 0.8)', 
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '16px',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
            }}>
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <div style={{ 
                        width: 64, 
                        height: 64, 
                        background: '#06D6A0', 
                        borderRadius: '16px', 
                        display: 'flex', 
                        justifyContent: 'center', 
                        alignItems: 'center',
                        margin: '0 auto 16px',
                        fontSize: 32,
                        color: '#000',
                        boxShadow: '0 0 20px rgba(6, 214, 160, 0.4)'
                    }}>
                        <RocketOutlined />
                    </div>
                    <Title level={2} style={{ color: '#F8FAFC', marginBottom: 8, marginTop: 0 }}>HiveMind</Title>
                    <Text type="secondary">欢迎回来，请登录您的智体治理中心</Text>
                </div>

                <Form layout="vertical" onFinish={onFinish} size="large">
                    <Form.Item name="username" rules={[{ required: true, message: '请输入账号' }]}>
                        <Input prefix={<UserOutlined style={{ color: '#94A3B8' }} />} placeholder="账号 (admin)" />
                    </Form.Item>
                    <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                        <Input.Password prefix={<LockOutlined style={{ color: '#94A3B8' }} />} placeholder="密码 (admin123)" />
                    </Form.Item>
                    <Form.Item style={{ marginBottom: 0 }}>
                        <Button type="primary" htmlType="submit" block loading={loading}>
                            进入系统
                        </Button>
                    </Form.Item>
                </Form>
            </Card>
        </div>
    );
};
