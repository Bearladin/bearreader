import { store } from '@/store';
import { Auth } from '@/store/_auth';
import type { LibraryItem } from '@/types';
import { stringifyError } from '@/utils/errors';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Input, List, message, Space, Typography } from 'antd';
import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import { LibraryItemCard } from './LibraryItemCard';

interface Props {
  novelId: string;
  onCreateNew: () => void;
  onSuccess: () => void;
}

export const LibrarySelectionView: React.FC<Props> = ({
  novelId,
  onCreateNew,
  onSuccess,
}) => {
  const user = Auth.select.user(store.getState());
  const [messageApi, contextHolder] = message.useMessage();

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | undefined>();
  const [libraries, setLibraries] = useState<LibraryItem[]>([]);
  const [searchValue, setSearchValue] = useState<string>('');

  useEffect(() => {
    if (user?.id) {
      setLoading(true);
      axios
        .get<LibraryItem[]>('/api/library/my/list')
        .then((resp) => setLibraries(resp.data))
        .catch((err) => setError(stringifyError(err)))
        .finally(() => setLoading(false));
    } else {
      setLibraries([]);
    }
  }, [user?.id]);

  const filteredLibraries = useMemo(() => {
    if (!searchValue) {
      return libraries;
    }
    return libraries.filter((library) =>
      library.name.toLowerCase().includes(searchValue.toLowerCase())
    );
  }, [libraries, searchValue]);

  const handleLibrarySelect = async (libraryId: string) => {
    setLoading(true);
    try {
      await axios.put(`/api/library/${libraryId}/novel/${novelId}`);
      messageApi.success('已添加到书架');
      onSuccess();
    } catch (err) {
      messageApi.error(stringifyError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {contextHolder}
      <Space vertical size="small" style={{ width: '100%' }}>
        <Input.Search
          allowClear
          size="large"
          value={searchValue}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            setSearchValue(e.target.value)
          }
          placeholder="搜索书架…"
        />

        <Typography.Text>选择要添加小说的书架：</Typography.Text>

        <List
          size="small"
          loading={loading}
          dataSource={filteredLibraries}
          locale={{
            emptyText: error ? (
              <>
                <Typography.Text type="danger">
                  书架加载失败。
                </Typography.Text>
                <br />
                {error}
              </>
            ) : (
              <>未找到书架</>
            ),
          }}
          style={{
            maxHeight: 300,
            overflowY: 'auto',
          }}
          renderItem={(library) => (
            <LibraryItemCard
              library={library}
              onClick={() => handleLibrarySelect(library.id)}
            />
          )}
        />

        <Button
          block
          icon={<PlusOutlined />}
          onClick={onCreateNew}
          type="dashed"
          size="large"
        >
          新建书架
        </Button>
      </Space>
    </>
  );
};
