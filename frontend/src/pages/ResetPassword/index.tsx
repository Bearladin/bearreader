import type { User } from '@/types';
import { stringifyError } from '@/utils/errors';
import { parseJwt } from '@/utils/jwt';
import { Alert, Button, Flex, Form, Input, Spin } from 'antd';
import FormItem from 'antd/es/form/FormItem';
import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';

export const ResetPasswordPage: React.FC<any> = () => {
  const navigate = useNavigate();
  const [search] = useSearchParams();

  const token = useMemo(() => search.get('token'), [search]);

  const [form] = Form.useForm();
  const [user, setUser] = useState<User>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        setLoading(true);
        setError(undefined);
        if (!parseJwt(token)) {
          return setError('无效的重置令牌');
        }
        const result = await axios.get<User>('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setUser(result.data);
      } catch (err) {
        setError(stringifyError(err));
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [token]);

  const sendResetLink = async (data: any) => {
    if (!token) return;
    setLoading(true);
    setError(undefined);
    try {
      await axios.post(`/api/auth/reset-password-with-token`, data, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      navigate('/login');
    } catch (err) {
      setError(stringifyError(err, '密码重置失败，请稍后重试。'));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Flex align="center" justify="center">
        <Spin aria-label="正在加载" size="large" style={{ margin: '100px 0' }} />
      </Flex>
    );
  }

  if (!user) {
    return <Navigate to="/forgot-password" replace />;
  }

  return (
    <Form
      form={form}
      onFinish={sendResetLink}
      size="large"
      layout="vertical"
      labelCol={{ style: { padding: 0 } }}
    >
      <Form.Item name="email" label="邮箱" initialValue={user.email}>
        <Input disabled autoComplete="email" placeholder="请输入邮箱" />
      </Form.Item>

      <Form.Item
        name={'password'}
        label="密码"
        rules={[
          { required: true, message: '请输入密码' },
          { min: 6, message: '密码至少需要 6 个字符' },
        ]}
        hasFeedback
      >
        <Input.Password
          placeholder="请输入新密码"
          autoComplete="new-password"
        />
      </Form.Item>

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
          children={'重置密码'}
        />
      </FormItem>
    </Form>
  );
};
