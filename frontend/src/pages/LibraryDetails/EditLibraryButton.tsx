import { copy } from '@/locales/zh-CN';
import type { Library } from '@/types';
import { stringifyError } from '@/utils/errors';
import { EditOutlined } from '@ant-design/icons';
import { Button, Form, Input, message, Modal } from 'antd';
import axios from 'axios';
import React, { useState } from 'react';

interface FormValues {
  name: string;
  description: string;
}

export const EditLibraryButton: React.FC<{
  library: Library;
  disabled?: boolean;
  onSuccess?: (library: Library) => void;
}> = ({ library, disabled, onSuccess }) => {
  const [form] = Form.useForm<FormValues>();
  const [messageApi, contextHolder] = message.useMessage();
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleEdit = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsModalOpen(true);
  };

  const handleEditSubmit = async (values: FormValues) => {
    if (!library.id) return;
    setIsSubmitting(true);
    try {
      const { data } = await axios.patch<Library>(
        `/api/library/${library.id}`,
        {
          name: values.name,
          description: values.description || undefined,
        }
      );
      messageApi.success('书架更新成功。');
      setIsModalOpen(false);
      onSuccess?.(data);
    } catch (err) {
      messageApi.error(stringifyError(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {contextHolder}
      <Button
        icon={<EditOutlined />}
        onClick={handleEdit}
        disabled={disabled || isSubmitting}
      >
        编辑
      </Button>

      <Modal
        closable={{ 'aria-label': '关闭编辑书架窗口' }}
        title="编辑书架"
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        confirmLoading={isSubmitting}
        onOk={() => form.submit()}
        okText={copy.common.save}
        cancelText={copy.common.cancel}
      >
        <Form<FormValues>
          form={form}
          layout="vertical"
          onFinish={handleEditSubmit}
          initialValues={{
            name: library.name,
            description: library.description || '',
          }}
        >
          <Form.Item
            name="name"
            label="书架名称"
            rules={[{ required: true, message: '请输入书架名称' }]}
          >
            <Input placeholder="我喜爱的小说" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea
              placeholder="可选：输入书架描述"
              rows={4}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
