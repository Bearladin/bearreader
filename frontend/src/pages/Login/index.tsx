import { store } from '@/store';
import { Auth } from '@/store/_auth';
import { stringifyError } from '@/utils/errors';
import { LoginOutlined } from '@ant-design/icons';
import { Alert, Button, Flex, Form, Input, Typography } from 'antd';
import FormItem from 'antd/es/form/FormItem';
import axios from 'axios';
import { useState } from 'react';

export const LoginPage: React.FC<any> = () => {
  const [form] = Form.useForm();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState<boolean>(false);

  const handleLogin = async (data: any) => {
    setLoading(true);
    setError(undefined);
    try {
      const result = await axios.post(`/api/auth/login`, data);
      store.dispatch(Auth.action.login(result.data));
    } catch (err) {
      setError(stringifyError(err, '登录失败，请稍后重试。'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form
      form={form}
      onFinish={handleLogin}
      size="large"
      layout="vertical"
      labelCol={{ style: { padding: 0 } }}
    >
      <Form.Item
        name="email"
        label="邮箱"
        rules={[{ required: true, message: '请输入邮箱' }]}
      >
        <Input placeholder="请输入邮箱" autoComplete="current-user" />
      </Form.Item>

      <Form.Item
        name={'password'}
        label="密码"
        rules={[{ required: true, message: '请输入密码' }]}
      >
        <Input.Password
          placeholder="请输入密码"
          autoComplete="current-password"
        />
      </Form.Item>

      <Flex justify="end">
        <Typography.Link href="/forgot-password">
          忘记密码？
        </Typography.Link>
      </Flex>

      {Boolean(error) && (
        <Alert
          type="warning"
          showIcon
          message={error}
          closable
          onClose={() => setError('')}
        />
      )}

      <FormItem style={{ marginTop: '20px' }}>
        <Button
          block
          type="primary"
          htmlType="submit"
          loading={loading}
          disabled={loading}
          icon={<LoginOutlined />}
          children={'登录'}
        />
      </FormItem>
    </Form>
  );
};
