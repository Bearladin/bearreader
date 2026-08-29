import { Auth } from '@/store/_auth';
import { NotificationItem } from '@/types';
import { stringifyError } from '@/utils/errors';
import {
  Alert,
  Descriptions,
  Flex,
  message,
  Space,
  Switch,
  Typography,
} from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';

const items = [
  {
    key: NotificationItem.NOVEL_SUCCESS,
    label: '小说获取任务请求成功时',
  },
  {
    key: NotificationItem.ARTIFACT_SUCCESS,
    label: '导出文件创建任务请求成功时',
  },
  {
    key: NotificationItem.JOB_RUNNING,
    label: '任意任务请求开始运行时',
  },
  {
    key: NotificationItem.JOB_SUCCESS,
    label: '任意任务请求成功时',
  },
  {
    key: NotificationItem.JOB_FAILURE,
    label: '任意任务请求失败时',
  },
  {
    key: NotificationItem.JOB_CANCELED,
    label: '任意任务请求取消时',
  },
];

export const NotificationSettings: React.FC<any> = () => {
  const dispatch = useDispatch();
  const [messageApi, contextHolder] = message.useMessage();

  const verified = useSelector(Auth.select.isVerified);
  const notifications = useSelector(Auth.select.emailAlerts);

  const [loading, setLoading] = useState<boolean>(false);

  const toggleNotification = async (item: NotificationItem) => {
    setLoading(true);
    try {
      const value = !(notifications && notifications[item]);
      const update = { ...notifications, [item]: value };
      await axios.put(`/api/settings/notifications`, { email_alerts: update });
      dispatch(Auth.action.setEmailAlerts(update));
    } catch (err) {
      messageApi.error(stringifyError(err, '通知设置更新失败'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Flex vertical gap={5}>
      {contextHolder}

      {!verified && (
        <Alert
          showIcon
          type="warning"
          title="请先验证邮箱以接收通知。"
        />
      )}

      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        以下事件发生时，系统会通过邮件通知您：
      </Typography.Text>

      <Descriptions
        bordered
        column={1}
        size="small"
        styles={{ label: { width: 275 } }}
        items={items.map(({ key, label }) => ({
          key,
          label,
          children: (
            <Space size="small">
              <Switch
                loading={loading}
                disabled={!verified}
                onClick={() => toggleNotification(key)}
                checked={Boolean(notifications && notifications[key])}
              />
            </Space>
          ),
        }))}
      />
    </Flex>
  );
};
