import { PlusOutlined } from '@ant-design/icons';
import type { ButtonProps } from 'antd';
import { Button, Modal } from 'antd';
import { useState } from 'react';
import { CreateLibraryView } from './CreateLibraryView';
import { LibrarySelectionView } from './LibrarySelectionView';

type View = 'selection' | 'create';

interface Props {
  novelId: string;
  buttonText?: string;
  buttonType?: ButtonProps['type'];
  size?: ButtonProps['size'];
}

export const AddToLibraryButton: React.FC<Props> = ({
  novelId,
  buttonText = '添加到书架',
  buttonType = 'default',
  size = 'middle',
}) => {
  const [open, setOpen] = useState(false);

  const [view, setView] = useState<View>('selection');

  const handleCancel = () => {
    setView('selection');
    setOpen(false);
  };

  return (
    <>
      <Button
        icon={<PlusOutlined />}
        type={buttonType}
        size={size}
        onClick={() => setOpen(true)}
      >
        {buttonText}
      </Button>

      <Modal
        title="添加到书架"
        open={open}
        footer={null}
        onCancel={handleCancel}
        destroyOnHidden
      >
        {view === 'selection' ? (
          <LibrarySelectionView
            novelId={novelId}
            onCreateNew={() => setView('create')}
            onSuccess={handleCancel}
          />
        ) : (
          <CreateLibraryView
            novelId={novelId}
            onSuccess={handleCancel}
            onBack={() => setView('selection')}
          />
        )}
      </Modal>
    </>
  );
};
