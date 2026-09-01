import type {
  EpubImportSession,
  EpubImportStartResponse,
} from '@/types';
import { stringifyError } from '@/utils/errors';
import {
  CheckCircleOutlined,
  InboxOutlined,
  ReloadOutlined,
  StopOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Divider,
  Input,
  Modal,
  Progress,
  Space,
  Typography,
  Upload,
} from 'antd';
import type { UploadFile, UploadProps } from 'antd';
import axios from 'axios';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const { Dragger } = Upload;

const ACTIVE_STATUSES = new Set(['analyzing', 'committing']);

export const EpubImportModal: React.FC<{
  open: boolean;
  onClose: () => void;
}> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const [uploadFile, setUploadFile] = useState<UploadFile>();
  const [session, setSession] = useState<EpubImportSession>();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string>();
  const [title, setTitle] = useState('');
  const [authors, setAuthors] = useState('');
  const uploadAborter = useRef<AbortController | undefined>(undefined);

  const active = Boolean(session && ACTIVE_STATUSES.has(session.status));
  const preview = session?.preview;
  const uploadOrigin = uploadFile?.originFileObj;

  useEffect(() => {
    if (!open || !session?.id || ACTIVE_STATUSES.has(session.status)) {
      return;
    }
    if (session.status !== 'ready') {
      return;
    }
    setTitle(preview?.title || '');
    setAuthors(preview?.authors || '');
  }, [open, preview?.authors, preview?.title, session?.id, session?.status]);

  useEffect(() => {
    if (!open || !session?.id || !ACTIVE_STATUSES.has(session.status)) {
      return;
    }
    let stopped = false;
    const poll = async () => {
      try {
        const { data } = await axios.get<EpubImportSession>(
          `/api/import/epub/${session.id}`
        );
        if (!stopped) {
          setSession(data);
          if (data.status === 'completed' && data.novel_id) {
            navigate(`/novel/${data.novel_id}`);
            onClose();
          }
        }
      } catch (err) {
        if (!stopped && !axios.isCancel(err)) {
          if (axios.isAxiosError(err) && err.response?.status === 404) {
            setSession((current) =>
              current
                ? {
                    ...current,
                    status: 'expired',
                    error: '导入会话已过期，请重新选择 EPUB 文件。',
                  }
                : current
            );
            setError('导入会话已过期，请重新选择 EPUB 文件。');
            return;
          }
          setError(stringifyError(err, '导入状态获取失败，请稍后重试。'));
        }
      }
    };
    void poll();
    const timer = window.setInterval(poll, 1500);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [navigate, onClose, open, session?.id, session?.status]);

  const reset = () => {
    uploadAborter.current?.abort();
    uploadAborter.current = undefined;
    setUploadFile(undefined);
    setSession(undefined);
    setUploading(false);
    setUploadProgress(0);
    setError(undefined);
    setTitle('');
    setAuthors('');
  };

  const handleClose = () => {
    uploadAborter.current?.abort();
    if (session?.id && session.status !== 'completed') {
      void axios.post(`/api/import/epub/${session.id}/cancel`).catch(() => {});
    }
    onClose();
  };

  const beforeUpload: UploadProps['beforeUpload'] = (file) => {
    if (!file.name.toLowerCase().endsWith('.epub')) {
      setError('仅支持 EPUB 文件。');
      return Upload.LIST_IGNORE;
    }
    setError(undefined);
    setUploadFile({
      uid: file.uid,
      name: file.name,
      originFileObj: file,
    });
    return false;
  };

  const handleStart = async () => {
    if (!uploadOrigin) {
      setError('请先选择一个 EPUB 文件。');
      return;
    }
    setUploading(true);
    setUploadProgress(0);
    setError(undefined);
    const body = new FormData();
    body.append('file', uploadOrigin, uploadOrigin.name);
    const controller = new AbortController();
    uploadAborter.current = controller;
    try {
      const { data } = await axios.post<EpubImportStartResponse>(
        '/api/import/epub',
        body,
        {
          signal: controller.signal,
          onUploadProgress: (event) => {
            if (event.total) {
              setUploadProgress(Math.round((event.loaded / event.total) * 100));
            }
          },
        }
      );
      if (data.existing_novel_id) {
        navigate(`/novel/${data.existing_novel_id}`);
        onClose();
        return;
      }
      if (!data.session_id) {
        throw new Error('导入任务未创建');
      }
      setSession({
        id: data.session_id,
        status: 'analyzing',
        original_name: uploadOrigin.name,
        file_size: uploadOrigin.size,
        expires_at: Date.now() + 24 * 60 * 60 * 1000,
        analyze_job_id: data.job_id,
        progress: 0,
      });
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(stringifyError(err, '上传 EPUB 失败，请稍后重试。'));
      }
    } finally {
      uploadAborter.current = undefined;
      setUploading(false);
    }
  };

  const handleCancel = async () => {
    if (!session?.id) {
      handleClose();
      return;
    }
    try {
      await axios.post(`/api/import/epub/${session.id}/cancel`);
      setSession((current) =>
        current ? { ...current, status: 'canceled', error: undefined } : current
      );
    } catch (err) {
      setError(stringifyError(err, '取消导入失败，请稍后重试。'));
    }
  };

  const handleCommit = async () => {
    if (!session?.id) return;
    try {
      setError(undefined);
      const { data } = await axios.post<EpubImportStartResponse>(
        `/api/import/epub/${session.id}/commit`,
        {
          title: title.trim(),
          authors: authors.trim(),
        }
      );
      setSession((current) =>
        current
          ? {
              ...current,
              status: 'committing',
              commit_job_id: data.job_id,
              progress: 0,
            }
          : current
      );
    } catch (err) {
      setError(stringifyError(err, '开始导入失败，请稍后重试。'));
    }
  };

  const footer = (() => {
    if (uploading || active) {
      return (
        <Button danger icon={<StopOutlined />} onClick={handleCancel}>
          取消导入
        </Button>
      );
    }
    if (session?.status === 'ready') {
      return (
        <Space>
          <Button onClick={handleCancel}>取消</Button>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={handleCommit}
          >
            确认导入
          </Button>
        </Space>
      );
    }
    if (
      session?.status === 'failed' ||
      session?.status === 'canceled' ||
      session?.status === 'expired'
    ) {
      return (
        <Space>
          <Button onClick={handleClose}>关闭</Button>
          <Button type="primary" icon={<ReloadOutlined />} onClick={reset}>
            重新选择
          </Button>
        </Space>
      );
    }
    return (
      <Space>
        <Button onClick={handleClose}>取消</Button>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          disabled={!uploadOrigin}
          onClick={handleStart}
        >
          开始分析
        </Button>
      </Space>
    );
  })();

  return (
    <Modal
      open={open}
      title="导入 EPUB"
      width={560}
      destroyOnHidden
      footer={footer}
      onCancel={handleClose}
    >
      {error && (
        <Alert
          type="warning"
          showIcon
          title={error}
          closable
          onClose={() => setError(undefined)}
          style={{ marginBottom: 15 }}
        />
      )}

      {!session && !uploading && (
        <Dragger
          accept="application/epub+zip"
          beforeUpload={beforeUpload}
          fileList={uploadFile ? [uploadFile] : []}
          maxCount={1}
          multiple={false}
          onRemove={() => {
            setUploadFile(undefined);
            return true;
          }}
          showUploadList
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">将 EPUB 文件拖到这里</p>
          <p className="ant-upload-hint">或点击选择文件，单个文件最大 100 MB</p>
        </Dragger>
      )}

      {uploading && (
        <Card variant="outlined">
          <Typography.Text>正在上传 {uploadOrigin?.name}</Typography.Text>
          <Progress percent={uploadProgress} style={{ marginTop: 10 }} />
        </Card>
      )}

      {session && active && (
        <Card variant="outlined">
          <Typography.Text strong>
            正在分析 {session.original_name}
          </Typography.Text>
          <Progress
            percent={Math.round(session.progress || 0)}
            status="active"
            style={{ marginTop: 10 }}
          />
          <Typography.Text type="secondary">
            {session.phase || '正在准备分析……'}
          </Typography.Text>
          <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
            分析可能需要一些时间，遇到复杂 EPUB 时请耐心等待。
          </Typography.Paragraph>
        </Card>
      )}

      {session?.status === 'ready' && preview && (
        <Space vertical size="middle" style={{ width: '100%' }}>
          <Descriptions
            bordered
            size="small"
            column={1}
            items={[
              {
                label: '章节',
                children: `${preview.chapters} 章 / ${preview.volumes} 卷`,
              },
              {
                label: '封面',
                children: preview.cover_available ? '已识别' : '未提供，将使用占位封面',
              },
              {
                label: '文件',
                children: session.original_name,
              },
            ]}
          />
          <div>
            <Typography.Text strong>书名</Typography.Text>
            <Input
              value={title}
              maxLength={200}
              onChange={(event) => setTitle(event.target.value)}
              style={{ marginTop: 5 }}
            />
          </div>
          <div>
            <Typography.Text strong>作者</Typography.Text>
            <Input
              value={authors}
              maxLength={200}
              onChange={(event) => setAuthors(event.target.value)}
              style={{ marginTop: 5 }}
            />
          </div>
          <div>
            <Typography.Text strong>目录与正文预览</Typography.Text>
            <Divider size="small" style={{ margin: '8px 0' }} />
            {preview.samples.map((sample, index) => (
              <Card
                key={`${sample.title}-${index}`}
                size="small"
                title={sample.title}
                style={{ marginTop: 8 }}
              >
                <Typography.Paragraph
                  type="secondary"
                  ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
                  style={{ marginBottom: 0 }}
                >
                  {sample.body_preview}
                </Typography.Paragraph>
              </Card>
            ))}
          </div>
        </Space>
      )}

      {session && ['failed', 'canceled', 'expired'].includes(session.status) && (
        <Alert
          type={session.status === 'canceled' ? 'info' : 'warning'}
          showIcon
          title={
            session.status === 'canceled'
              ? '导入已取消。'
              : session.error || '这个 EPUB 暂时无法导入。'
          }
        />
      )}
    </Modal>
  );
};
