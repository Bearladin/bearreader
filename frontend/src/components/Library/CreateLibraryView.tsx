import type { Library } from '@/types';
import { stringifyError } from '@/utils/errors';
import { ArrowLeftOutlined } from '@ant-design/icons';
import {
  Button,
  Flex,
  Form,
  Input,
  Space,
  Switch,
  Typography,
  message,
} from 'antd';
import axios from 'axios';
import { useState } from 'react';

interface FormValues {
  name: string;
  description?: string;
  is_public?: boolean;
}

interface Props {
  novelId: string;
  onBack: () => void;
  onSuccess: () => void;
}

export const CreateLibraryView: React.FC<Props> = ({
  novelId,
  onBack,
  onSuccess,
}) => {
  const [form] = Form.useForm<FormValues>();
  const [saving, setSaving] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const handleSubmit = async (values: FormValues) => {
    if (!values.name?.trim()) {
      messageApi.error('请输入书架名称');
      return;
    }

    setSaving(true);
    try {
      const { data } = await axios.post<Library>('/api/library', {
        name: values.name.trim(),
        description: values.description?.trim(),
        is_public: Boolean(values.is_public),
      });
      await axios.put(`/api/library/${data.id}/novel/${novelId}`);
      messageApi.success('小说已成功添加到书架');
      onSuccess();
    } catch (err) {
      messageApi.error(stringifyError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Form<FormValues>
        form={form}
        size="large"
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{ is_public: false }}
        labelCol={{ style: { padding: 0 } }}
      >
        <Form.Item
          label="名称"
          name="name"
          rules={[{ required: true, message: '请输入书架名称' }]}
        >
          <Input placeholder="我喜爱的小说" />
        </Form.Item>

        <Form.Item label="描述" name="description">
          <Input.TextArea placeholder="选填描述" rows={3} />
        </Form.Item>

        <Form.Item label="可见范围" name="is_public" valuePropName="checked">
          <Space>
            <Switch aria-label="公开书架" />
            <Typography.Text>所有人可见</Typography.Text>
          </Space>
        </Form.Item>

        <Form.Item>
          <Flex gap={8} justify="flex-end">
            <Button icon={<ArrowLeftOutlined />} onClick={onBack}>
              返回
            </Button>
            <Button type="primary" htmlType="submit" loading={saving}>
              新建并添加
            </Button>
          </Flex>
        </Form.Item>
      </Form>
    </>
  );
};
