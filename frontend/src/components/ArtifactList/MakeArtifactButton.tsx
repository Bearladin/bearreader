import { OutputFormat, type Job } from '@/types';
import { stringifyError } from '@/utils/errors';
import { AppstoreAddOutlined } from '@ant-design/icons';
import { Button, Checkbox, Col, Modal, Row, Typography, message } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export const MakeArtifactButton: React.FC<{
  novelId: string;
}> = ({ novelId }) => {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();

  const [open, setOpen] = useState(false);
  const [changing, setChanging] = useState(false);
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  const toggleSelected = (value: string) => {
    setSelected((p) => ({ ...p, [value]: !p[value] }));
  };

  const handleMakeArtifact = async () => {
    const formats = Object.keys(selected).filter((v) => selected[v]);
    if (!formats.length) {
      return messageApi.warning('请至少选择一种格式');
    }
    try {
      setChanging(true);
      const result = await axios.post<Job>('/api/job/create/make-artifacts', {
        novel_id: novelId,
        formats,
      });
      setOpen(false);
      navigate(`/job/${result.data.id}`);
    } catch (err) {
      console.error(err);
      messageApi.error(stringifyError(err));
    } finally {
      setChanging(false);
    }
  };

  return (
    <>
      {contextHolder}

      <Button
        shape="round"
        icon={<AppstoreAddOutlined />}
        onClick={() => setOpen(true)}
      >
        生成导出文件
      </Button>

      <Modal
        width={400}
        open={open}
        destroyOnHidden
        loading={changing}
        okText="创建"
        onOk={handleMakeArtifact}
        onCancel={() => setOpen(false)}
        title={
          <Typography.Title level={4} style={{ margin: 0 }}>
            <AppstoreAddOutlined /> 生成导出文件
          </Typography.Title>
        }
      >
        <Row>
          {Object.entries(OutputFormat)
            .filter(([name]) => name === 'epub' || name === 'text')
            .map(([name, value]) => (
            <Col xs={12} key={name}>
              <Checkbox
                checked={selected[value]}
                onClick={() => toggleSelected(value)}
                style={{
                  width: '100%',
                  borderRadius: 0,
                  padding: '5px 10px',
                  fontSize: '14px',
                  fontFamily: 'monospace',
                  justifyContent: 'flex-start',
                }}
              >
                {name}
              </Checkbox>
            </Col>
          ))}
        </Row>
      </Modal>
    </>
  );
};
