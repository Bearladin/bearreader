import type { Job } from '@/types';
import { stringifyError } from '@/utils/errors';
import { SendOutlined } from '@ant-design/icons';
import { Alert, Button, Form, Grid, Input, Typography } from 'antd';
import type { TextAreaProps } from 'antd/es/input';
import axios from 'axios';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TidyURL } from 'tidy-url';

const URL_PATTERN = /^https?:\/\//i;

export const RequestNovelCard: React.FC<any> = () => {
  const { lg } = Grid.useBreakpoint();

  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState<boolean>(false);

  const submitJob = async (values: any) => {
    const input: string = String(values.input ?? '').trim();
    setLoading(true);
    setError(undefined);
    try {
      if (URL_PATTERN.test(input)) {
        const result = await axios.post<Job>(`/api/job/create/fetch-novels`, {
          urls: [input],
          full: true,
        });
        navigate(`/job/${result.data.id}`);
      } else {
        const result = await axios.post<Job>(
          `/api/job/create/search-sources`,
          { query: input }
        );
        navigate(`/job/${result.data.id}`);
      }
    } catch (err) {
      setError(stringifyError(err, '提交任务请求失败，请稍后重试。'));
    } finally {
      setLoading(false);
    }
  };

  const onInput: TextAreaProps['onInput'] = (e) => {
    try {
      const value = e.currentTarget.value;
      if (!URL_PATTERN.test(value)) {
        return;
      }
      const trimmed = value.replace(/[\n\r\t ]+/g, '');
      const cleaned = TidyURL.clean(trimmed).url;
      if (cleaned !== value) {
        e.currentTarget.value = cleaned;
      }
    } catch {}
  };

  return (
    <Form
      form={form}
      size="large"
      onFinish={submitJob}
      labelCol={{ style: { padding: 0 } }}
      encType="application/x-www-form-urlencoded"
    >
      <Typography.Text className="br-section-label">新建请求</Typography.Text>
      <Typography.Title className="br-page-title" level={2}>获取一本小说</Typography.Title>
      <Typography.Paragraph type="secondary" style={{ marginTop: 6 }}>
        粘贴小说页面地址，或输入书名搜索支持的书源。
      </Typography.Paragraph>

      {Boolean(error) && (
        <Alert
          type="warning"
          showIcon
          title={error}
          style={{ marginTop: '15px' }}
          closable={{ onClose: () => setError('') }}
        />
      )}
      <Form.Item
        name="input"
        rules={[
          { required: true, message: '请输入小说页面 URL 或书名' },
          {
            validator: (_, value) => {
              const v = String(value ?? '').trim();
              if (!v) {
                return Promise.resolve();
              }
              if (URL_PATTERN.test(v)) {
                try {
                  new URL(v);
                  return Promise.resolve();
                } catch {
                  return Promise.reject(
                    new Error('请输入以 http:// 或 https:// 开头的有效 URL')
                  );
                }
              }
              if (v.length < 2) {
                return Promise.reject(new Error('书名至少需要 2 个字'));
              }
              if (v.length > 50) {
                return Promise.reject(new Error('书名最多 50 个字'));
              }
              return Promise.resolve();
            },
          },
        ]}
      >
        <div style={{ position: 'relative' }}>
          <Input.TextArea
            rows={1}
            autoSize
            placeholder="输入小说页面 URL 或书名"
            autoComplete="off"
            onInput={onInput}
            style={{
              resize: 'none',
              fontWeight: 500,
              fontSize: lg ? '1.2rem' : '1.05rem',
              paddingRight: lg ? 125 : 50,
              outline: 'none',
              minHeight: 50,
              borderRadius: 2,
            }}
            styles={{
              textarea: {
                overflowX: 'hidden',
                overflowY: 'hidden',
                scrollbarWidth: 'none',
                msOverflowStyle: 'none',
              },
            }}
            onPressEnter={(e) => {
              e.preventDefault();
              form.submit();
            }}
          />
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            icon={<SendOutlined />}
            aria-label="提交任务请求"
            children={lg ? '提交' : ''}
            style={{
              height: 43,
              position: 'absolute',
              right: 3,
              bottom: 4,
              zIndex: 2,
              padding: lg ? 18 : '0 15px',
              fontSize: lg ? '1.25rem' : '1rem',
              borderRadius: 2,
            }}
          />
        </div>
      </Form.Item>

      <Typography.Text type="secondary" style={{ fontSize: 13 }}>
        输入小说页面的完整 URL（以“http://”或“https://”开头），或直接输入书名（2–50
        个字），系统会在支持搜索的书源中查找并获取小说。www.mayiwsk.com 和
        uukanshu.cc 支持书名搜索。
      </Typography.Text>
    </Form>
  );
};
