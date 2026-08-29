import { copy } from '@/locales/zh-CN';
import type { Library } from '@/types';
import { stringifyError } from '@/utils/errors';
import { FolderAddOutlined } from '@ant-design/icons';
import { Button, Form, Input, message, Modal, Switch } from 'antd';
import axios from 'axios';
import { useState } from 'react';

type FormValues = {
  name: string;
  description?: string;
  is_public?: boolean;
};

export const CreateLibraryButton: React.FC<{
  onSuccess?: () => void;
}> = ({ onSuccess }) => {
  const [form] = Form.useForm<FormValues>();
  const [messageApi, contextHolder] = message.useMessage();

  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleCreate = async (values: FormValues) => {
    setSaving(true);
    try {
      await axios.post<Library>('/api/library', {
        name: values.name,
        description: values.description,
        is_public: Boolean(values.is_public),
      });
      messageApi.success('书架创建成功。');
      form.resetFields();
      setOpen(false);
      onSuccess?.();
    } catch (err) {
      messageApi.error(stringifyError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Button
        type="primary"
        loading={saving}
        icon={<FolderAddOutlined />}
        onClick={() => setOpen(true)}
      >
        新建书架
      </Button>

      <Modal
        closable={{ 'aria-label': '关闭创建书架窗口' }}
        title="创建书架"
        open={open}
        onCancel={() => setOpen(false)}
        destroyOnHidden
        confirmLoading={saving}
        onOk={() => form.submit()}
        okText={copy.common.save}
        cancelText={copy.common.cancel}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ is_public: false }}
        >
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入书架名称' }]}
          >
            <Input placeholder="我的书架" />
          </Form.Item>

          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="可选：输入书架描述" />
          </Form.Item>

          <Form.Item
            label="设为公开"
            name="is_public"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
