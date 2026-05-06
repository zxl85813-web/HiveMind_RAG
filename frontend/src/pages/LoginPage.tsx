import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, Alert, Flex } from 'antd';
import { UserOutlined, LockOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';

const { Title, Text } = Typography;

export const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Get redirection path or fallback to '/'
    const from = (location.state as { from?: string })?.from || '/';

    const onFinish = async (values: any) => {
        setLoading(true);
        setError(null);
        try {
            const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
            const response = await axios.post(`${apiBaseUrl}/auth/login`, {
                username: values.username,
                password: values.password,
            });

            if (response.data?.access_token) {
                localStorage.setItem('access_token', response.data.access_token);
                // Redirect user to original page or dashboard
                navigate(from, { replace: true });
            } else {
                setError('服务器未能返回有效的登录凭证');
            }
        } catch (err: any) {
            console.error('[Login Error]', err);
            const msg = err.response?.data?.message || err.response?.data?.detail;
            if (Array.isArray(msg)) {
                setError(msg[0]?.msg || '密码或用户名错误');
            } else {
                setError(msg || '无法连接到认证服务器，请检查用户名或密码');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            {/* Ambient Background Glows */}
            <div style={styles.glowLeft}></div>
            <div style={styles.glowRight}></div>

            <Card style={styles.glassCard} bodyStyle={{ padding: '40px 32px' }} bordered={false}>
                <Flex vertical align="center" style={{ marginBottom: 32 }}>
                    {/* Logo Indicator */}
                    <div style={styles.logoBadge}>
                        <SafetyCertificateOutlined style={{ fontSize: '26px', color: '#10B981' }} />
                    </div>
                    <Title level={2} style={styles.title}>
                        HiveMind RAG
                    </Title>
                    <Text style={styles.subtitle}>
                        企业级智能知识库与智能体蜂巢协作平台
                    </Text>
                </Flex>

                {error && (
                    <Alert
                        message={error}
                        type="error"
                        showIcon
                        closable
                        onClose={() => setError(null)}
                        style={styles.alert}
                    />
                )}

                <Form
                    name="login_form"
                    initialValues={{ remember: true }}
                    onFinish={onFinish}
                    size="large"
                    layout="vertical"
                >
                    <Form.Item
                        name="username"
                        rules={[{ required: true, message: '请输入您的用户名或邮箱' }]}
                    >
                        <Input
                            prefix={<UserOutlined style={{ color: 'rgba(255,255,255,0.45)' }} />}
                            placeholder="用户名 (例如: admin)"
                            style={styles.input}
                        />
                    </Form.Item>

                    <Form.Item
                        name="password"
                        rules={[{ required: true, message: '请输入您的密码' }]}
                    >
                        <Input.Password
                            prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.45)' }} />}
                            placeholder="密码 (例如: admin123)"
                            style={styles.input}
                        />
                    </Form.Item>

                    <Form.Item style={{ marginTop: 24, marginBottom: 0 }}>
                        <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                            style={styles.submitBtn}
                            block
                        >
                            {loading ? '正在验证身份...' : '登 录'}
                        </Button>
                    </Form.Item>
                </Form>

                <div style={styles.footer}>
                    <Text style={styles.footerText}>
                        Default Account: <span style={{ color: '#10B981', fontWeight: 600 }}>admin</span> / <span style={{ color: '#10B981', fontWeight: 600 }}>admin123</span>
                    </Text>
                </div>
            </Card>
        </div>
    );
};

// === Premium Cyberpunk Refined CSS-in-JS Styles ===
const styles: Record<string, React.CSSProperties> = {
    container: {
        width: '100vw',
        height: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: '#0B0F19',
        overflow: 'hidden',
        position: 'relative',
        fontFamily: "'Inter', 'Segoe UI', Roboto, sans-serif",
    },
    glowLeft: {
        position: 'absolute',
        top: '10%',
        left: '15%',
        width: '450px',
        height: '450px',
        background: 'radial-gradient(circle, rgba(16,185,129,0.12) 0%, rgba(16,185,129,0) 70%)',
        borderRadius: '50%',
        pointerEvents: 'none',
        filter: 'blur(40px)',
    },
    glowRight: {
        position: 'absolute',
        bottom: '10%',
        right: '15%',
        width: '450px',
        height: '450px',
        background: 'radial-gradient(circle, rgba(59,130,246,0.1) 0%, rgba(59,130,246,0) 70%)',
        borderRadius: '50%',
        pointerEvents: 'none',
        filter: 'blur(40px)',
    },
    glassCard: {
        width: '440px',
        background: 'rgba(17, 24, 39, 0.7)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '24px',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)',
        zIndex: 10,
    },
    logoBadge: {
        width: '60px',
        height: '60px',
        borderRadius: '16px',
        background: 'rgba(16, 185, 129, 0.1)',
        border: '1px solid rgba(16, 185, 129, 0.25)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: '16px',
        boxShadow: '0 0 20px rgba(16, 185, 129, 0.15)',
    },
    title: {
        color: '#FFFFFF',
        margin: 0,
        fontWeight: 700,
        letterSpacing: '-0.5px',
    },
    subtitle: {
        color: 'rgba(255, 255, 255, 0.45)',
        fontSize: '13px',
        textAlign: 'center',
        marginTop: '8px',
    },
    alert: {
        marginBottom: '20px',
        borderRadius: '12px',
        background: 'rgba(239, 68, 68, 0.1)',
        border: '1px solid rgba(239, 68, 68, 0.2)',
        color: '#FCA5A5',
    },
    input: {
        background: 'rgba(31, 41, 55, 0.6)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '12px',
        color: '#FFFFFF',
        padding: '12px 16px',
        transition: 'all 0.3s ease',
    },
    submitBtn: {
        height: '50px',
        background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
        borderColor: 'transparent',
        borderRadius: '12px',
        fontSize: '16px',
        fontWeight: 600,
        boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)',
        transition: 'all 0.3s ease',
    },
    footer: {
        marginTop: '28px',
        textAlign: 'center',
    },
    footerText: {
        color: 'rgba(255, 255, 255, 0.35)',
        fontSize: '12px',
    },
};
