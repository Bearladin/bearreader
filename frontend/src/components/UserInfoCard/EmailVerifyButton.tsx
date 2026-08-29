import { store } from '@/store';
import { Auth } from '@/store/_auth';
import { stringifyError } from '@/utils/errors';
import { WarningOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Flex,
  Input,
  message,
  Modal,
  Space,
  Typography,
} from 'antd';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';

export const EmailVerifyButton: React.FC<any> = () => {
  const isVerified = useSelector(Auth.select.isVerified);
  const [messageApi, contextHolder] = message.useMessage();
  const [showVerify, setShowVerify] = useState<boolean>(false);

  const [otp, setOtp] = useState<string>('');
  const [token, setToken] = useState<string>();
  const [resendTimeout, setResendTimeout] = useState<number>(0);

  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (resendTimeout <= 0) return;
    const tid = setTimeout(() => {
      setResendTimeout((v) => v - 1);
    }, 998);
    return () => clearTimeout(tid);
  }, [resendTimeout]);

  const sendOTP = async () => {
    try {
      setError(undefined);
      setLoading(true);
      setResendTimeout(30);
      const { data } = await axios.post('/api/auth/me/send-otp');
      setToken(data.token);
    } catch (err) {
      setError(stringifyError(err));
    } finally {
      setLoading(false);
    }
  };

  const startVerifyEmail = async () => {
    if (!loading && resendTimeout <= 0) {
      sendOTP();
    }
    setShowVerify(true);
  };

  const handleVerify = async () => {
    try {
      if (!token || !otp) {
        return;
      }
      await axios.post(
        `/api/auth/verify-otp`,
        new URLSearchParams({ otp, token }).toString(),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );
      store.dispatch(Auth.action.setEmailVerified());
      setShowVerify(false);
      messageApi.open({
        type: 'success',
        content: '邮箱验证成功。',
      });
    } catch (err) {
      messageApi.open({
        type: 'error',
        content: stringifyError(err),
      });
    } finally {
      setLoading(false);
    }
  };

  if (isVerified) {
    return null;
  }

  return (
    <>
      {contextHolder}

      <Button
        block
        danger
        shape="round"
        onClick={startVerifyEmail}
        icon={<WarningOutlined />}
        children="验证邮箱"
      />

      <Modal
        centered
        open={showVerify}
        title="验证邮箱"
        okText="验证"
        width={450}
        onOk={handleVerify}
        onCancel={() => setShowVerify(false)}
        cancelButtonProps={{ type: 'text' }}
        okButtonProps={{ loading, disabled: !otp || !token }}
        mask={{ closable: false }}
      >
        <Flex vertical gap={15}>
          <Typography.Text>
            6 位验证码已发送到您的邮箱，请在下方输入验证码以继续。
          </Typography.Text>

          <Input.OTP length={6} value={otp} onChange={setOtp} size="large" />

          <Space>
            <Typography.Text>没有收到验证码？</Typography.Text>
            {resendTimeout > 0 ? (
              <Typography.Text type="secondary">
                {resendTimeout} 秒后可重新发送。
              </Typography.Text>
            ) : (
              <Typography.Link onClick={sendOTP}>
                点击此处重新发送。
              </Typography.Link>
            )}
          </Space>

          {Boolean(error) && <Alert type="error" showIcon title={error} />}
        </Flex>
      </Modal>
    </>
  );
};
