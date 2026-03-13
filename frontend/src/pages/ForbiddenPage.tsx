import React from 'react';
import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';

export const ForbiddenPage: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
            <Result
                status="403"
                title="403"
                subTitle="当前账号无权访问该页面，请联系管理员开通权限。"
                extra={
                    <Button type="primary" onClick={() => navigate('/')}>
                        返回首页
                    </Button>
                }
            />
        </div>
    );
};

export default ForbiddenPage;