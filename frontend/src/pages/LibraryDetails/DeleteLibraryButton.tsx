import { copy } from '@/locales/zh-CN';
import type { Library } from '@/types';
import { stringifyError } from '@/utils/errors';
import { DeleteOutlined } from '@ant-design/icons';
import { Button, message, Popconfirm } from 'antd';
import axios from 'axios';
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface DeleteLibraryButtonProps {
  library: Library;
  disabled?: boolean;
}

export const DeleteLibraryButton: React.FC<DeleteLibraryButtonProps> = ({
  library,
  disabled,
}) => {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();
  const [deleting, setDeleting] = useState<boolean>(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await axios.delete(`/api/library/${library.id}`);
      messageApi.success('书架删除成功。');
      navigate('/libraries');
    } catch (err) {
      messageApi.error(stringifyError(err));
      setDeleting(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Popconfirm
        title="删除书架？"
        description="确定要永久删除这个书架吗？"
        onConfirm={handleDelete}
        okText="确认删除"
        okType="danger"
        cancelText={copy.common.cancel}
      >
        <Button
          danger
          icon={<DeleteOutlined />}
          loading={deleting}
          disabled={disabled || deleting}
        >
          {copy.common.delete}
        </Button>
      </Popconfirm>
    </>
  );
};
