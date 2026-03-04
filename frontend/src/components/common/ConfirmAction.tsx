import React from 'react';
import { Popconfirm, Modal } from 'antd';
import { QuestionCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';

export interface ConfirmActionProps {
    /** 确认标题 */
    title: string;
    /** 确认详情描述 (Modal 时建议提供详细说明) */
    description?: React.ReactNode;
    /** 执行的主要回调 */
    onConfirm: () => void | Promise<any>;
    /** 取消的回调 */
    onCancel?: () => void;
    /** 展示形态: 气泡确认(popconfirm) 还是 模态窗对话框(modal) */
    mode?: 'popconfirm' | 'modal';
    /** 透传触发确认的子组件 (例如: <Button>删除</Button>) */
    children: React.ReactElement;
    /** 按键风格，如 danger */
    okType?: 'primary' | 'danger' | 'dashed' | 'default';
    okText?: string;
    cancelText?: string;
}

/**
 * 统一的操作确认组件
 * 
 * 把不可逆的危险操作（删除、重置）包在里面，自动接管二次确认 UI。
 */
export const ConfirmAction: React.FC<ConfirmActionProps> = ({
    title,
    description,
    onConfirm,
    onCancel,
    mode = 'popconfirm',
    children,
    okType = 'primary',
    okText = '确定',
    cancelText = '取消'
}) => {
    if (mode === 'modal') {
        const handleClick = (e: React.MouseEvent) => {
            // 防止冒泡或其他默认行为
            e.stopPropagation();
            Modal.confirm({
                title: title,
                icon: okType === 'danger' ? <ExclamationCircleOutlined style={{ color: 'var(--hm-color-error)' }} /> : <QuestionCircleOutlined />,
                content: description,
                okText,
                okType,
                cancelText,
                onOk: async () => {
                    await onConfirm();
                },
                onCancel,
                centered: true,
                maskClosable: true,
                className: 'hm-confirm-modal'
            });
        };

        const child = children as React.ReactElement<any>;
        return React.cloneElement(child, {
            onClick: (e: React.MouseEvent) => {
                handleClick(e);
                if (child.props.onClick) {
                    child.props.onClick(e);
                }
            }
        });
    }

    // Default to Popconfirm
    return (
        <Popconfirm
            title={title}
            description={description}
            onConfirm={onConfirm}
            onCancel={onCancel}
            okText={okText}
            cancelText={cancelText}
            okButtonProps={{ danger: okType === 'danger' }}
            icon={<QuestionCircleOutlined style={{ color: okType === 'danger' ? 'var(--hm-color-error)' : 'var(--hm-color-warning)' }} />}
        >
            {children}
        </Popconfirm>
    );
};
