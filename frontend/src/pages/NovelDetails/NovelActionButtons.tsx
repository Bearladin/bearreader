import { copy } from '@/locales/zh-CN';
import { AddToLibraryButton } from '@/components/Library/AddToLibraryButton';
import { Auth } from '@/store/_auth';
import type { Job, Novel } from '@/types';
import { stringifyError } from '@/utils/errors';
import { BookOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { Button, Flex, message, Popconfirm } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';

export const NovelActionButtons: React.FC<{ novel: Novel }> = ({ novel }) => {
  const navigate = useNavigate();
  const isAdmin = useSelector(Auth.select.isAdmin);
  const [messageApi, contextHolder] = message.useMessage();
  const [busy, setBusy] = useState(false);

  const handleContinue = async () => {
    try {
      const { data } = await axios.get<{ chapter_id?: string }>(
        '/api/read-history/continue',
        { params: { novel_id: novel.id } }
      );
      if (!data.chapter_id) {
        messageApi.info('暂无可读章节');
        return;
      }
      navigate(`/read/${data.chapter_id}`);
    } catch (err) {
      messageApi.error(stringifyError(err));
    }
  };

  // "检查更新并补全": checks the catalog for new chapters, fetches any
  // missing chapter bodies and rebuilds the EPUB (FETCH_LATEST job type).
  const handleRefresh = async () => {
    try {
      setBusy(true);
      const result = await axios.post<Job>(`/api/job/create/fetch-latest`, {
        novel_id: novel.id,
      });
      navigate(`/job/${result.data.id}`);
    } catch (err) {
      messageApi.error(stringifyError(err));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    try {
      await axios.delete(`/api/novel/${novel.id}`);
      navigate(`/novels`);
    } catch (err) {
      messageApi.error(stringifyError(err));
    }
  };

  return (
    <Flex wrap align="center" justify="end" gap={10}>
      {contextHolder}
      {isAdmin && (
        <Popconfirm
          title="删除小说？"
          description={`确定要永久删除《${novel.title}》吗？`}
          okText="确认删除"
          okType="danger"
          cancelText={copy.common.cancel}
          onConfirm={handleDelete}
        >
          <Button danger icon={<DeleteOutlined />}>
            {copy.common.delete}
          </Button>
        </Popconfirm>
      )}
      <div style={{ flex: 1 }} />
      <AddToLibraryButton novelId={novel.id} />
      <Button icon={<BookOutlined />} onClick={handleContinue}>
        继续阅读
      </Button>
      <Button icon={<ReloadOutlined />} loading={busy} onClick={handleRefresh}>
        检查更新并补全
      </Button>
    </Flex>
  );
};
