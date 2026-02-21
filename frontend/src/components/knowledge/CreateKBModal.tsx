import React from 'react';
import { Modal, Form, Input, Switch, Select } from 'antd';
import type { CreateKnowledgeBaseParams } from '../../services/knowledgeApi';

interface Props {
    open: boolean;
    onCancel: () => void;
    onSubmit: (values: CreateKnowledgeBaseParams) => void;
    loading?: boolean;
}

export const CreateKBModal: React.FC<Props> = ({ open, onCancel, onSubmit, loading }) => {
    const [form] = Form.useForm();

    const handleOk = async () => {
        try {
            const values = await form.validateFields();
            // Clear form after submit? Or let parent handle closing
            onSubmit(values);
        } catch (e) {
            // validation error
        }
    };

    // Reset form when opening/closing
    React.useEffect(() => {
        if (!open) form.resetFields();
    }, [open, form]);

    return (
        <Modal
            title="创建知识库"
            open={open}
            onOk={handleOk}
            onCancel={onCancel}
            confirmLoading={loading}
        >
            <Form form={form} layout="vertical" initialValues={{ is_public: false, embedding_model: 'text-embedding-3-small' }}>
                <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
                    <Input placeholder="知识库名称 (例如: 产品文档)" />
                </Form.Item>
                <Form.Item name="description" label="描述">
                    <Input.TextArea placeholder="该知识库的用途..." rows={3} />
                </Form.Item>
                <Form.Item name="embedding_model" label="Embedding 模型">
                    <Select options={[
                        { label: 'OpenAI text-embedding-3-small', value: 'text-embedding-3-small' },
                        { label: 'OpenAI text-embedding-3-large', value: 'text-embedding-3-large' },
                    ]} />
                </Form.Item>
                <Form.Item name="is_public" label="公开可见" valuePropName="checked" tooltip="若开启，所有用户均可检索此知识库">
                    <Switch />
                </Form.Item>
            </Form>
        </Modal>
    );
};
