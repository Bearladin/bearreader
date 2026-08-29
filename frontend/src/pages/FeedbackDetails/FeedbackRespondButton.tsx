import { copy } from '@/locales/zh-CN';
import type { Feedback } from '@/types';
import { FeedbackStatus } from '@/types';
import { stringifyError } from '@/utils/errors';
import { MessageOutlined } from '@ant-design/icons';
import { Button, Form, Input, message, Modal, Select, Space } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { FeedbackStatusLabels } from '../FeedbackList/utils';

type FormValues = {
  status?: FeedbackStatus;
  admin_notes?: string;
};

export const FeedbackRespondButton: React.FC<{
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
      if (values.status !== undefined) {
        payload.status = values.status;
      }
      if (values.admin_notes) {
        payload.admin_notes = values.admin_notes;
      }
      const { data } = await axios.post<Feedback>(
        `/api/feedback/${feedback.id}/respond`,
        payload
      );
      messageApi.success('反馈回复成功。');
      setOpen(false);
      form.resetFields();
      onSuccess?.(data);
    } catch (err) {
      messageApi.error(stringifyError(err, '回复反馈失败，请稍后重试。'));
    } finally {
      setUpdating(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Button
        icon={<MessageOutlined />}
        onClick={() => {
          form.setFieldsValue({
            status: feedback.status,
            admin_notes: feedback.admin_notes || '',
          });
          setOpen(true);
        }}
      >
        回复
      </Button>

      <Modal
        closable={{ 'aria-label': '关闭回复反馈窗口' }}
        title="回复反馈"
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
            status: feedback.status,
            admin_notes: feedback.admin_notes || '',
          }}
          size="large"
          layout="vertical"
          labelCol={{ style: { padding: 0 } }}
        >
          <Form.Item name="status" label="状态">
            <Select
              options={Object.values(FeedbackStatus).map((value) => ({
                value,
                label: FeedbackStatusLabels[value],
              }))}
            />
          </Form.Item>

          <Form.Item
            name="admin_notes"
            label="回复内容"
            rules={[
              {
                max: 5000,
                message: '回复内容不能超过 5000 个字符',
              },
            ]}
          >
            <Input.TextArea
              rows={6}
              placeholder="输入管理员回复"
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
                回复
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
