import { copy } from '@/locales/zh-CN';
import { type Feedback, FeedbackType } from '@/types';
import { stringifyError } from '@/utils/errors';
import { EditOutlined } from '@ant-design/icons';
import { Button, Form, Input, message, Modal, Select, Space } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { FeedbackTypeLabels } from '../FeedbackList/utils';

type FormValues = {
  type?: FeedbackType;
  subject?: string;
  message?: string;
};

export const FeedbackEditButton: React.FC<{
  feedback: Feedback;
  onSuccess?: (feedback: Feedback) => void;
}> = ({ feedback, onSuccess }) => {
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  const [open, setOpen] = useState(false);
  const [updating, setUpdating] = useState(false);

  const handleEdit = async (values: FormValues) => {
    setUpdating(true);
    try {
      const payload: FormValues = {};
      if (values.type !== undefined) {
        payload.type = values.type;
      }
      if (values.subject) {
        payload.subject = values.subject;
      }
      if (values.subject) {
        payload.subject = values.subject;
      }
      if (values.message) {
        payload.message = values.message;
      }
      const { data } = await axios.put<Feedback>(
        `/api/feedback/${feedback.id}`,
        payload
      );
      messageApi.success('反馈更新成功。');
      setOpen(false);
      form.resetFields();
      onSuccess?.(data);
    } catch (err) {
      messageApi.error(stringifyError(err, '更新反馈失败，请稍后重试。'));
    } finally {
      setUpdating(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Button
        icon={<EditOutlined />}
        onClick={() => {
          form.setFieldsValue({
            type: feedback.type,
            subject: feedback.subject,
            message: feedback.message,
          });
          setOpen(true);
        }}
      >
        编辑
      </Button>

      {/* User Edit Modal */}
      <Modal
        closable={{ 'aria-label': '关闭编辑反馈窗口' }}
        title="编辑反馈"
        open={open}
        onCancel={() => {
          setOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          onFinish={handleEdit}
          initialValues={{
            type: feedback.type,
            subject: feedback.subject,
            message: feedback.message,
          }}
          size="large"
          layout="vertical"
          labelCol={{ style: { padding: 0 } }}
        >
          <Form.Item
            name="type"
            label="类型"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <Select
              options={Object.values(FeedbackType).map((value) => ({
                value,
                label: FeedbackTypeLabels[value],
              }))}
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
            <Input placeholder="简要说明反馈内容" maxLength={200} />
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
            <Input.TextArea
              rows={6}
              placeholder="详细说明反馈内容"
              maxLength={5000}
              showCount
            />
          </Form.Item>

          <Form.Item style={{ marginTop: '40px' }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button
                onClick={() => {
                  setOpen(false);
                  form.resetFields();
                }}
                disabled={updating}
              >
                {copy.common.cancel}
              </Button>
              <Button type="primary" htmlType="submit" loading={updating}>
                {copy.common.save}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
