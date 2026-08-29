import { stringifyError } from '@/utils/errors';
import { EditOutlined, LockOutlined, SaveOutlined } from '@ant-design/icons';
import {
  Button,
  Divider,
  Flex,
  Form,
  Input,
  Modal,
  Space,
  message,
} from 'antd';
import axios from 'axios';
import { useState } from 'react';

export const ProfilePasswordChangeButton: React.FC<any> = () => {
  const [messageApi, contextHolder] = message.useMessage();

  const [open, setOpen] = useState(false);
  const [changing, setChanging] = useState(false);

  const handleChangePassword = async (values: {
    current_password: string;
    new_password: string;
  }) => {
    if (values.current_password === values.new_password) {
      messageApi.info('新密码不能与当前密码相同');
      return;
    }
    try {
      setChanging(true);
      await axios.put('/api/auth/me/password', {
        old_password: values.current_password,
        new_password: values.new_password,
      });
      messageApi.success('密码修改成功');
      setOpen(false);
    } catch (err) {
      console.error(err);
      messageApi.error(stringifyError(err));
    } finally {
      setChanging(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Button
        type="primary"
        icon={<EditOutlined />}
        onClick={() => setOpen(true)}
      >
        修改密码
      </Button>

      <Modal
        title={
          <Space>
            <LockOutlined /> 修改密码
          </Space>
        }
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form size="large" layout="vertical" onFinish={handleChangePassword}>
          <Form.Item
            name="current_password"
            label="当前密码"
            rules={[
              { required: true, message: '请输入当前密码' },
            ]}
          >
            <Input.Password
              placeholder="请输入当前密码"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item
            name="new_password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少需要 6 个字符' },
            ]}
            hasFeedback
          >
            <Input.Password
              placeholder="请输入新密码"
              autoComplete="new-password"
            />
          </Form.Item>

          <Divider size="small" />

          <Flex gap={10} justify="end">
            <Button onClick={() => setOpen(false)}>取消</Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={changing}
              icon={<SaveOutlined />}
            >
              更新密码
            </Button>
          </Flex>
        </Form>
      </Modal>
    </>
  );
};
