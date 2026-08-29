import { UserRoleTag } from '@/components/Tags/UserRoleTag';
import { UserTierTag } from '@/components/Tags/UserTierTag';
import { store } from '@/store';
import { Auth } from '@/store/_auth';
import { UserRole, UserTier, type User } from '@/types';
import { stringifyError } from '@/utils/errors';
import { EditOutlined, SaveOutlined } from '@ant-design/icons';
import {
  Button,
  Divider,
  Flex,
  Form,
  Input,
  Modal,
  Select,
  Space,
  message,
  type ButtonProps,
} from 'antd';
import axios from 'axios';
import { useState } from 'react';

export const UserEditButton: React.FC<
  {
    user: User;
    onChange?: () => any;
  } & ButtonProps
> = ({ user, onChange, ...buttonProps }) => {
  const [messageApi, contextHolder] = message.useMessage();

  const [editOpen, setEditOpen] = useState(false);
  const [updating, setUpdating] = useState(false);

  const handleUpdateName = async (values: {
    name?: string;
    password?: string;
    role?: string;
    tier?: number;
  }) => {
    try {
      setUpdating(true);
      const changes: any = {};
      if (values.password?.trim()) {
        changes.password = values.password.trim();
      }
      if (typeof values.role === 'string' && values.role !== user.role) {
        changes.role = values.role;
      }
      if (typeof values.tier === 'number' && values.tier !== user.tier) {
        changes.tier = values.tier;
      }
      if (values.name?.trim() && values.name?.trim() !== user.name) {
        changes.name = values.name;
      }
      if (!Object.keys(changes).length) {
        messageApi.info('未修改任何内容');
        return;
      }
      await axios.put(`/api/user/${user.id}`, changes);
      delete changes.password;
      store.dispatch(Auth.action.setUser({ ...user, ...changes }));
      messageApi.success('用户更新成功');
      setEditOpen(false);
      if (onChange) onChange();
    } catch (err) {
      console.error(err);
      messageApi.error(stringifyError(err));
    } finally {
      setUpdating(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Button
        icon={<EditOutlined />}
        {...buttonProps}
        onClick={() => setEditOpen(true)}
      >
        编辑用户
      </Button>

      <Modal
        title={
          <Space>
            <EditOutlined /> 编辑用户
          </Space>
        }
        open={editOpen}
        footer={null}
        onCancel={() => setEditOpen(false)}
        destroyOnHidden
      >
        <Form
          layout="vertical"
          initialValues={user}
          onFinish={handleUpdateName}
          labelCol={{ style: { padding: 0 } }}
        >
          <Form.Item
            name="name"
            label="姓名"
            rules={[
              {
                validator: (_: any, value: string) =>
                  value && value.trim().length >= 2
                    ? Promise.resolve()
                    : Promise.reject('请输入有效姓名'),
              },
            ]}
          >
            <Input
              size="large"
              placeholder="请输入姓名"
              autoComplete="name"
            />
          </Form.Item>

          <Form.Item name="role" label="角色">
            <Select
              virtual={false}
              size="large"
              placeholder="请选择角色"
              options={Object.values(UserRole).map((value) => ({
                value,
                label: <UserRoleTag value={value} />,
              }))}
            />
          </Form.Item>

          <Form.Item name="tier" label="用户等级">
            <Select
              virtual={false}
              size="large"
              placeholder="请选择用户等级"
              options={Object.values(UserTier).map((value) => ({
                value,
                label: <UserTierTag value={value} />,
              }))}
            />
          </Form.Item>

          <Form.Item
            name={'password'}
            label="新密码"
            rules={[
              { min: 6, message: '密码至少需要 6 个字符' },
            ]}
            hasFeedback
          >
            <Input.Password
              size="large"
              placeholder="请输入新密码"
              autoComplete="new-password"
            />
          </Form.Item>

          <Divider size="small" />

          <Flex gap={10} justify="end">
            <Button onClick={() => setEditOpen(false)}>取消</Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={updating}
              icon={<SaveOutlined />}
            >
              保存
            </Button>
          </Flex>
        </Form>
      </Modal>
    </>
  );
};
