import { copy } from '@/locales/zh-CN';
import { Auth } from '@/store/_auth';
import { JobStatus, type Job } from '@/types';
import { stringifyError } from '@/utils/errors';
import { CloseOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { Button, message, Popconfirm, type ButtonProps } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { JobIssueReportButton } from './JobIssueReportButton';

export const JobActionButtons: React.FC<{
  job: Job;
  onChange?: () => any;
  onDeleted?: () => any;
  size?: ButtonProps['size'];
}> = ({ job, size, onChange, onDeleted }) => {
  const navigate = useNavigate();
  const isAdmin = useSelector(Auth.select.isAdmin);
  const currentUser = useSelector(Auth.select.user);
  const [messageApi, contextHolder] = message.useMessage();

  const [busy, setBusy] = useState<boolean>(false);

  const cancelJob = async () => {
    try {
      setBusy(true);
      await axios.post(`/api/job/${job.id}/cancel`);
      if (onChange) onChange();
    } catch (err) {
      messageApi.open({
        type: 'error',
        content: stringifyError(err, '取消任务请求失败，请稍后重试。'),
      });
    } finally {
      setBusy(false);
    }
  };

  const replayJob = async () => {
    try {
      setBusy(true);
      const result = await axios.post<Job>(`/api/job/${job.id}/replay`, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      navigate({ pathname: `/job/${result.data.id}` });
    } catch (err) {
      messageApi.open({
        type: 'error',
        content: stringifyError(err, '重新执行任务请求失败，请稍后重试。'),
      });
    } finally {
      setBusy(false);
    }
  };

  const deleteJob = async () => {
    try {
      setBusy(true);
      await axios.delete(`/api/job/${job.id}`);
      if (onDeleted) onDeleted();
    } catch (err) {
      messageApi.open({
        type: 'error',
        content: stringifyError(err, '删除任务记录失败，请稍后重试。'),
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {contextHolder}
      {job.status === JobStatus.FAILED && (
        <JobIssueReportButton size={size} job={job} />
      )}
      {job.is_done && (
        <Popconfirm
          title="重新执行任务请求？"
          description="将基于当前内容创建新的任务请求并重新执行。"
          okText="确认重新执行"
          cancelText={copy.common.cancel}
          onConfirm={replayJob}
        >
          <Button size={size} loading={busy}>
            <ReloadOutlined /> 重新执行
          </Button>
        </Popconfirm>
      )}
      {(isAdmin || job.user_id === currentUser?.id) && !job.is_done && (
        <Popconfirm
          title="取消任务请求？"
          description="取消后，此任务请求将停止执行。"
          okText="确认取消"
          okType="danger"
          cancelText={copy.common.cancel}
          onConfirm={cancelJob}
        >
          <Button size={size} danger loading={busy}>
            <CloseOutlined /> 取消任务请求
          </Button>
        </Popconfirm>
      )}
      {(isAdmin || job.user_id === currentUser?.id) && job.is_done && (
        <Popconfirm
          title="删除任务记录？"
          description="仅删除任务记录，已下载的小说与导出文件不受影响。"
          okText="确认删除"
          okType="danger"
          cancelText={copy.common.cancel}
          onConfirm={deleteJob}
        >
          <Button size={size} danger loading={busy}>
            <DeleteOutlined /> 删除记录
          </Button>
        </Popconfirm>
      )}
    </>
  );
};
