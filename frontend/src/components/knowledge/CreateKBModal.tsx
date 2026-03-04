import React from 'react';
import { Modal, Form, Input, Switch, Select } from 'antd';
import { useTranslation } from 'react-i18next';
import type { CreateKnowledgeBaseParams } from '../../services/knowledgeApi';

interface Props {
    open: boolean;
    onCancel: () => void;
    onSubmit: (values: CreateKnowledgeBaseParams) => void;
    loading?: boolean;
}

export const CreateKBModal: React.FC<Props> = ({ open, onCancel, onSubmit, loading }) => {
    const { t } = useTranslation();
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
            title={t('knowledge.create')}
            open={open}
            onOk={handleOk}
            onCancel={onCancel}
            confirmLoading={loading}
            destroyOnHidden={true}
            forceRender={true}
        >
            <Form form={form} layout="vertical" initialValues={{ is_public: false, embedding_model: 'text-embedding-3-small', chunking_strategy: 'recursive' }}>
                <Form.Item name="name" label={t('knowledge.name')} rules={[{ required: true, message: 'Please input name' }]}>
                    <Input placeholder="eg: Product Docs" />
                </Form.Item>
                <Form.Item name="description" label={t('knowledge.desc')}>
                    <Input.TextArea rows={3} />
                </Form.Item>
                <Form.Item name="embedding_model" label={t('knowledge.embedding')}>
                    <Select options={[
                        { label: 'OpenAI text-embedding-3-small', value: 'text-embedding-3-small' },
                        { label: 'OpenAI text-embedding-3-large', value: 'text-embedding-3-large' },
                    ]} />
                </Form.Item>
                <Form.Item name="chunking_strategy" label="Chunking Strategy">
                    <Select options={[
                        { label: 'Recursive Character (Default)', value: 'recursive' },
                        { label: 'Parent-Child (Advanced Context)', value: 'parent_child' },
                        { label: 'Table Aware (Markdown)', value: 'table_aware' },
                    ]} />
                </Form.Item>
                <Form.Item name="is_public" label={t('knowledge.public')} valuePropName="checked">
                    <Switch />
                </Form.Item>
            </Form>
        </Modal>
    );
};
