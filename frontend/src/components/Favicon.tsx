import { API_BASE_URL } from '@/config';
import { GlobalOutlined } from '@ant-design/icons';
import { Avatar, type AvatarProps } from 'antd';
import qs from 'qs';
import { useMemo } from 'react';

export const Favicon: React.FC<
  Omit<AvatarProps, 'src'> & {
    url: string;
  }
> = ({ url, ...props }) => {
  const faviconLink = useMemo(() => {
    if (!url) return null;
    const search = qs.stringify({ url });
    return `${API_BASE_URL}/api/meta/favicon?${search}`;
  }, [url]);

  return (
    <Avatar size={24} icon={<GlobalOutlined />} {...props} src={faviconLink} />
  );
};
