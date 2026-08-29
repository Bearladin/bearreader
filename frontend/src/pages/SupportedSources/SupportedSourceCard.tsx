import { Favicon } from '@/components/Favicon';
import type { SourceItem } from '@/types';
import { getGradientForId } from '@/utils/gradients';
import { formatDate, parseDate } from '@/utils/time';
import {
  FlagOutlined,
  GlobalOutlined,
  LoginOutlined,
  PictureOutlined,
  SearchOutlined,
  StopOutlined,
  TranslationOutlined,
} from '@ant-design/icons';
import { Card, Flex, Space, Tag, Typography } from 'antd';
import { Link } from 'react-router-dom';
import { URL_SOURCE_HINTS, getLanguageLabel } from './utils';

const capabilityTagStyle: React.CSSProperties = {
  background: '#F1F1EE',
  borderColor: '#D8D8D4',
  color: '#4B4B48',
  fontWeight: 500,
};

const capabilityIcon = <SearchOutlined style={{ color: '#686868' }} />;

export const SupportedSourceCard: React.FC<{
  source: SourceItem;
  disabled?: boolean;
}> = ({ source, disabled }) => {
  const updatedAt = formatDate(parseDate(Number(source.version) * 1000));

  return (
    <Card size="small" style={{ opacity: disabled ? 0.8 : 1 }}>
      <Space size={15} style={{ width: '100%' }}>
        <Favicon
          size="large"
          url={source.url}
          style={{ background: getGradientForId(source.url, 'dark') }}
          icon={disabled ? <StopOutlined /> : <GlobalOutlined />}
        />

        <Flex vertical>
          <Typography.Link
            strong
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ margin: 0, fontSize: 16 }}
          >
            {source.url}
          </Typography.Link>

          {disabled && source.disable_reason ? (
            <Typography.Text type="secondary" italic>
              停用原因：{source.disable_reason}
            </Typography.Text>
          ) : source.total_novels > 0 ? (
            <Typography.Text type="secondary" italic>
              使用此书源找到{' '}
              <Link type="secondary" to={`/novels?domain=${source.domain}`}>
                {source.total_novels} 部小说
              </Link>
            </Typography.Text>
          ) : null}

          <Flex gap={7} align="center" wrap style={{ marginTop: 8 }}>
            {Boolean(source.version && updatedAt) && (
              <Tag icon={'版本：'} title="更新时间">
                {updatedAt}
              </Tag>
            )}
            {Boolean(source.language) && (
              <Tag icon={<FlagOutlined />} title="语言">
                {getLanguageLabel(source.language)}
              </Tag>
            )}
            {Boolean(source.has_manga) && (
              <Tag icon={<PictureOutlined />}>支持漫画</Tag>
            )}
            {Boolean(source.has_mtl) && (
              <Tag icon={<TranslationOutlined />}>包含机器翻译内容</Tag>
            )}
            {Boolean(source.can_login) && (
              <Tag icon={<LoginOutlined />}>支持登录</Tag>
            )}
            {Boolean(source.can_search) && (
              <Tag
                icon={capabilityIcon}
                style={capabilityTagStyle}
              >
                支持书名搜索
              </Tag>
            )}
            {URL_SOURCE_HINTS.includes(source.domain) && (
              <Tag
                icon={capabilityIcon}
                style={capabilityTagStyle}
              >
                到这里搜索具体书获取 URL
              </Tag>
            )}
          </Flex>
        </Flex>
      </Space>
    </Card>
  );
};
