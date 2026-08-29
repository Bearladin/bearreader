import { copy } from '@/locales/zh-CN';
import { FeedbackType } from '@/types';
import { stringifyError } from '@/utils/errors';
import { CommentOutlined } from '@ant-design/icons';
import { Button, Flex, Form, Input, message, Modal, Select, Space } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { FeedbackTypeLabels } from './utils';

const { TextArea } = Input;

const feedbackTypeOptions = Object.values(FeedbackType).map((value) => ({
  value,
  label: FeedbackTypeLabels[value],
}));

export const FeedbackButton: React.FC<{
  onSubmit?: () => any;
}> = ({ onSubmit }) => {
  const [form] = Form.useForm();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const handleSubmit = async (values: {
    type: FeedbackType;
    subject: string;
    message: string;
  }) => {
    setLoading(true);
    try {
      await axios.post('/api/feedback', values);
      messageApi.success('反馈提交成功，感谢您的意见。');
      form.resetFields();
      setOpen(false);
      onSubmit?.();
    } catch (err) {
      messageApi.error(stringifyError(err, '提交反馈失败，请稍后重试。'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Button
        type="primary"
        icon={<CommentOutlined />}
        onClick={() => setOpen(true)}
      >
        提交反馈
      </Button>

      <Modal
        closable={{ 'aria-label': '关闭提交反馈窗口' }}
        title={
          <Space>
            <CommentOutlined /> 提交反馈
          </Space>
        }
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        width={600}
        destroyOnHidden
      >
        <Form
          form={form}
          size="large"
          layout="vertical"
          onFinish={handleSubmit}
          autoComplete="off"
          labelCol={{ style: { padding: 0 } }}
        >
          <Form.Item
            name="type"
            label="反馈类型"
            initialValue={FeedbackType.GENERAL}
            rules={[
              { required: true, message: '请选择反馈类型' },
            ]}
          >
            <Select
              placeholder="选择反馈类型"
              options={feedbackTypeOptions}
            />
          </Form.Item>

          <Form.Item
            name="subject"
            label="主题"
            rules={[
              { required: true, message: '请输入主题' },
              { max: 200, message: '主题不能超过 200 个字符' },
            ]}
          >
            <Input
              placeholder="简要说明反馈内容"
              maxLength={200}
              showCount
            />
          </Form.Item>

          <Form.Item
            name="message"
            label="详细内容"
            rules={[
              { required: true, message: '请输入详细内容' },
              {
                max: 5000,
                message: '详细内容不能超过 5000 个字符',
              },
            ]}
          >
            <TextArea
              placeholder="请详细说明您的反馈"
              rows={6}
              maxLength={5000}
              showCount
            />
          </Form.Item>

          <Form.Item style={{ marginTop: 35 }}>
            <Flex justify="end" gap={10}>
              <Button onClick={() => setOpen(false)} disabled={loading}>
                {copy.common.cancel}
              </Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                提交
              </Button>
            </Flex>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
