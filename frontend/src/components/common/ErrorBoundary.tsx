import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button, Result, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface Props {
    children?: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error?: Error;
}

/**
 * 🛰️ [Architecture-Gate]: 错误边界组件
 * 
 * 职责: 捕获子组件树中的 React 运行时错误，防止全局白屏。
 * 策略: 在生产环境下展示优雅的降级 UI，并提供重试/刷新机制。
 */
export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false
    };

    public static getDerivedStateFromError(error: Error): State {
        // 更新 state 使下一次渲染能够显示降级 UI
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        import('../../core/MonitorService').then(({ monitor }) => {
            monitor.reportError(error, {
                componentStack: errorInfo.componentStack,
                type: 'REACT_BOUNDARY',
                severity: 'critical'
            });
        });
        console.error('🧩 [ErrorBoundary] Uncaught error:', error, errorInfo);
    }

    private handleReload = () => {
        window.location.reload();
    };

    public render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div style={{
                    height: '100vh',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    background: 'var(--ant-color-bg-layout)',
                    padding: '24px'
                }}>
                    <Result
                        status="error"
                        title="应用组件运行异常"
                        subTitle={
                            <div style={{ maxWidth: '500px' }}>
                                <Text type="secondary">
                                    HiveMind 捕捉到一个未处理的渲染错误。这可能是由于本地状态同步、后台返回异常或组件依赖加载失败导致的。
                                </Text>
                                <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(239, 71, 111, 0.05)', borderRadius: '8px', border: '1px solid rgba(239, 71, 111, 0.1)' }}>
                                    <Text type="danger" code style={{ fontSize: '12px' }}>
                                        {this.state.error?.message || 'Unknown Runtime Error'}
                                    </Text>
                                </div>
                            </div>
                        }
                        extra={[
                            <Button
                                type="primary"
                                key="reload"
                                icon={<ReloadOutlined />}
                                onClick={this.handleReload}
                                style={{ borderRadius: '8px' }}
                            >
                                刷新并重启应用
                            </Button>
                        ]}
                    />
                </div>
            );
        }

        return this.props.children;
    }
}
