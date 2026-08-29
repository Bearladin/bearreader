import { copy } from '@/locales/zh-CN';
import type { Library, Novel } from '@/types';
import { stringifyError } from '@/utils/errors';
import { DeleteOutlined } from '@ant-design/icons';
import { Button, message, Popconfirm } from 'antd';
import axios from 'axios';

export const RemoveLibraryNovelButton: React.FC<{
  novel: Novel;
  library: Library;
  onRemoved?: () => void;
}> = ({ novel, library, onRemoved }) => {
  const [messageApi, contextHolder] = message.useMessage();

  const handleRemove = async (novel: Novel) => {
    try {
      await axios.delete(`/api/library/${library.id}/novels/${novel.id}`);
      messageApi.success('已从书架移除小说。');
      onRemoved?.();
    } catch (err) {
      messageApi.error(stringifyError(err));
    }
  };

  return (
    <>
      {contextHolder}
      <Popconfirm
        title="从书架移除小说？"
        description={`确定要从“${library.name}”中移除《${novel.title}》吗？`}
        okText="确认移除"
        okType="danger"
        cancelText={copy.common.cancel}
        onConfirm={() => handleRemove(novel)}
      >
        <Button
          aria-label="从书架移除小说"
          icon={<DeleteOutlined />}
          danger
          type="primary"
          size="small"
          style={{
            position: 'absolute',
            top: 4,
            right: 4,
            zIndex: 2,
          }}
          onClick={(e) => {
            e.stopPropagation();
            e.preventDefault();
          }}
        />
      </Popconfirm>
    </>
  );
};
