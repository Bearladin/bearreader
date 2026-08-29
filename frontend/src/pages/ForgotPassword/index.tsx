import { stringifyError } from '@/utils/errors';
import { LeftOutlined } from '@ant-design/icons';
import { Alert, Button, Divider, Flex, Form, Input, Typography } from 'antd';
import FormItem from 'antd/es/form/FormItem';
import axios from 'axios';
import { useState } from 'react';

export const ForgotPasswordPage: React.FC<any> = () => {
  const [form] = Form.useForm();
  const [error, setError] = useState<string>();
  const [success, setSuccess] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  const sendResetLink = async (data: any) => {
    if (success) return;
    setLoading(true);
    setSuccess(false);
    setError(undefined);
    try {
      await axios.post(`/api/auth/send-password-reset-link`, data);
      setSuccess(true);
    } catch (err) {
      setError(stringifyError(err, '重置链接发送失败，请稍后重试。'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form
      form={form}
      onFinish={sendResetLink}
      size="large"
      layout="vertical"
      labelCol={{ style: { padding: 0 } }}
    >
      <Form.Item
        name="email"
        label="邮箱"
        rules={[
          { required: true, message: '请输入邮箱' },
          { type: 'email', message: '请输入有效的邮箱地址' },
        ]}
      >
        <Input
          placeholder="请输入邮箱"
          autoComplete="current-user"
          disabled={success}
        />
      </Form.Item>

      {error ? (
        <Alert
          type="warning"
          showIcon
          message={error}
          closable
          onClose={() => setError('')}
        />
      ) : success ? (
        <Alert type="success" showIcon message="请查收您的邮箱" />
      ) : null}

      {!success ? (
        <FormItem style={{ marginTop: '20px' }}>
          <Button
            block
            type="primary"
            htmlType="submit"
            loading={loading}
            disabled={loading}
            children={'发送重置链接'}
          />
        </FormItem>
      ) : (
        <Flex justify="center" style={{ marginTop: 20 }}>
          <Typography.Link href="/forgot-password">
            我没有收到重置链接
          </Typography.Link>
        </Flex>
      )}

      <Divider />
      <Flex justify="center">
        <Typography.Link href="/login">
          <LeftOutlined /> 返回登录
        </Typography.Link>
      </Flex>
    </Form>
  );
};
