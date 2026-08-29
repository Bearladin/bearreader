import type { User } from '@/types';
import { UserOutlined } from '@ant-design/icons';
import { Avatar, theme, type AvatarProps } from 'antd';
import md5 from 'spark-md5';

const getGravatarUrl = (email: string, size = 200) => {
  const hash = md5.hash(email.trim().toLowerCase());
  return `https://www.gravatar.com/avatar/${hash}?d=identicon&s=${size}`;
};

export const UserAvatar: React.FC<
  {
    user?: User | null;
  } & AvatarProps
> = ({ user, ...avatarProps }) => {
  const { token } = theme.useToken();
  if (!user) {
    return null;
  }
  return (
    <Avatar
      key={user.email}
      size={72}
      alt={user.name || user.email}
      src={getGravatarUrl(user.email)}
      {...avatarProps}
      icon={<UserOutlined style={{ fontSize: 'inherit' }} />}
      style={{
        backgroundColor: token.colorPrimary,
        ...avatarProps.style,
      }}
    />
  );
};
