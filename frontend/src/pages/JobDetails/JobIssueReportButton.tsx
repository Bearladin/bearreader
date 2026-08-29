import { copy, enumLabels } from '@/locales/zh-CN';
import type { Feedback, Job } from '@/types';
import { FeedbackType } from '@/types';
import { stringifyError } from '@/utils/errors';
import { BugOutlined } from '@ant-design/icons';
import type { ButtonProps } from 'antd';
import { Button, Flex, Form, Input, message, Modal, Space } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const issueFeedbackLabel = enumLabels.feedbackType[FeedbackType.ISSUE];

export const JobIssueReportButton: React.FC<{
  job: Job;
  size?: ButtonProps['size'];
}> = ({ job, size }) => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const { data } = await axios.post<Feedback>('/api/feedback', {
        type: FeedbackType.ISSUE,
        subject: form.getFieldValue('subject'),
        message: form.getFieldValue('message'),
        extra: {
          ...job.extra,
          job_id: job.id,
          job_error: job.error,
        },
      });
      messageApi.success(`${issueFeedbackLabel}提交成功，感谢您的反馈。`);
      form.resetFields();
      setOpen(false);
      navigate(`/feedback/${data.id}`);
    } catch (err) {
      messageApi.error(
        stringifyError(err, `提交${issueFeedbackLabel}失败，请稍后重试。`)
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Button
        danger
        size={size}
        type="default"
        icon={<BugOutlined />}
        onClick={() => setOpen(true)}
      >
        {issueFeedbackLabel}
      </Button>

      <Modal
        closable={{ 'aria-label': `关闭${issueFeedbackLabel}窗口` }}
        title={
          <Space>
            <BugOutlined /> {issueFeedbackLabel}
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
          initialValues={{
            subject: `任务失败：${job.job_title || job.id}`,
            message: [
              job.extra.url && `URL: ${job.extra.url}`,
              job.extra.novel_title && `小说：${job.extra.novel_title}`,
              job.extra.chapter_serial &&
                `章节：${job.extra.chapter_serial}`,
              job.extra.volume_serial && `分卷：${job.extra.volume_serial}`,
              job.extra.format && `格式：${job.extra.format}`,
              job.error &&
                `错误：${job.error.trim().split('\n').reverse()[0]}`,
            ]
              .filter(Boolean)
              .join('\n'),
          }}
        >
          <Form.Item
            name="subject"
            label="主题"
            rules={[
              { required: true, message: '请输入主题' },
              { max: 200, message: '主题不能超过 200 个字符' },
            ]}
          >
            <Input
              placeholder="简要说明遇到的问题"
              maxLength={200}
              showCount
            />
          </Form.Item>

          <Form.Item
            name="message"
            label="详细信息"
            rules={[
              {
                max: 5000,
                message: '详细信息不能超过 5000 个字符',
              },
            ]}
          >
            <Input.TextArea
              placeholder="可选：补充问题的详细信息"
              rows={3}
              maxLength={5000}
              showCount
            />
          </Form.Item>

          <Form.Item style={{ marginTop: 35 }}>
            <Flex justify="end" gap={10}>
              <Button onClick={() => setOpen(false)} disabled={loading}>
                {copy.common.cancel}
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                onClick={handleSubmit}
                loading={loading}
              >
                提交{issueFeedbackLabel}
              </Button>
            </Flex>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
