import { copy } from '@/locales/zh-CN';
import type { Feedback } from '@/types';
import { stringifyError } from '@/utils/errors';
import { DeleteOutlined } from '@ant-design/icons';
import { Button, message, Popconfirm } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export const FeedbackDeleteButton: React.FC<{
  feedback: Feedback;
}> = ({ feedback }) => {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();

  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await axios.delete(`/api/feedback/${feedback.id}`);
      messageApi.success('反馈删除成功。');
      navigate('/feedbacks');
    } catch (err) {
      messageApi.error(stringifyError(err, '删除反馈失败，请稍后重试。'));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Popconfirm
        title="删除反馈"
        description="确定要永久删除这条反馈吗？"
        onConfirm={handleDelete}
        okText="确认删除"
        okType="danger"
        cancelText={copy.common.cancel}
      >
        <Button danger icon={<DeleteOutlined />} loading={deleting}>
          {copy.common.delete}
        </Button>
      </Popconfirm>
    </>
  );
};
