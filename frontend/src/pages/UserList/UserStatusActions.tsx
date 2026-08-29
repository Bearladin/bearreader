import { Auth } from '@/store/_auth';
import { type User } from '@/types';
import { stringifyError } from '@/utils/errors';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { Button, message, Popconfirm } from 'antd';
import axios from 'axios';
import { useSelector } from 'react-redux';

export const UserStatusActions: React.FC<{
  user: User;
  onChange?: () => any;
}> = ({ user, onChange }) => {
  const currentUser = useSelector(Auth.select.user);
  const [messageApi, contextHolder] = message.useMessage();

  const toggleUserActiveStatus = async () => {
    try {
      await axios.put(`/api/user/${user.id}`, {
        is_active: !user.is_active,
      });
      if (onChange) onChange();
    } catch (err) {
      messageApi.open({
        type: 'error',
        content: stringifyError(err, '用户状态更新失败'),
      });
    }
  };

  if (user.id === currentUser?.id) {
    return null;
  }

  return (
    <>
      {contextHolder}
      {user.is_active ? (
        <Popconfirm
          title="确认停用该用户？"
          description="停用后，该用户将无法正常使用账户。"
          okText="确认停用"
          okType="danger"
          cancelText="取消"
          onConfirm={toggleUserActiveStatus}
        >
          <Button
            size="small"
            title="停用用户"
            type="primary"
            danger
            icon={<CloseCircleOutlined />}
          >
            停用
          </Button>
        </Popconfirm>
      ) : (
        <Popconfirm
          title="确认启用该用户？"
          description="启用后，该用户将恢复账户访问权限。"
          okText="确认启用"
          cancelText="取消"
          onConfirm={toggleUserActiveStatus}
        >
          <Button
            size="small"
            title="启用用户"
            type="primary"
            icon={<CheckCircleOutlined />}
          >
            启用
          </Button>
        </Popconfirm>
      )}
    </>
  );
};
