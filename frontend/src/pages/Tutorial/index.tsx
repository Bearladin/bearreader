import {
  BookOutlined,
  DownloadOutlined,
  FileDoneOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { APP_VERSION } from '@/version';
import { Divider, Typography } from 'antd';
import { Link } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;

export const TutorialPage: React.FC<any> = () => {
  return (
    <div className="br-page-container">
      <Text className="br-section-label">快速开始</Text>
      <Title level={2} className="br-page-title">使用教程</Title>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        当前版本：{APP_VERSION}
      </Paragraph>

      <Divider />

      <section style={{ padding: '4px 0 20px 24px', borderLeft: '2px solid var(--br-ink)' }}>
        <Title level={3} style={{ marginTop: 0 }}>
          <BookOutlined /> 第一步：创建任务请求
        </Title>
        <Paragraph>
          前往<Link to="/">任务请求</Link>页面，输入框支持两种输入方式，任选其一后点击“提交”或按 Enter 键：
        </Paragraph>
        <ul>
          <li>
            <Text strong>粘贴小说页面 URL：</Text>
            打开受支持的书源网站（见<Link to="/meta/sources">书源</Link>
            页面），找到要获取的小说，复制小说主页的完整 URL（以“http://”或“https://”开头）后粘贴到输入框。
          </li>
          <li>
            <Text strong>直接输入书名：</Text>
            输入小说书名（2–50 个字符），系统会自动按书名搜索。仅 www.mayiwsk.com
            支持书名搜索。如果书名搜索找不到书，请到书源页面的其他书源中获取到具体的
            URL。
          </li>
        </ul>
      </section>

      <section style={{ padding: '4px 0 20px 24px', borderLeft: '2px solid var(--br-border-strong)' }}>
        <Title level={3} style={{ marginTop: 0 }}>
          <SearchOutlined /> 第二步：搜索书
        </Title>
        <Paragraph>
          提交书名后，系统会在支持搜索的书源中查找，并在任务请求详情页显示“搜索结果”面板，搜索期间页面会自动刷新，请耐心等待。系统会自动获取匹配小说的基本信息。
        </Paragraph>
        <Paragraph>
          如果提交的是小说页面 URL，系统会直接进入小说获取流程，无需搜索。
        </Paragraph>
      </section>

      <section style={{ padding: '4px 0 20px 24px', borderLeft: '2px solid var(--br-border-strong)' }}>
        <Title level={3} style={{ marginTop: 0 }}>
          <DownloadOutlined /> 第三步：获取书
        </Title>
        <Paragraph>搜到书之后，点击结果旁的「获取此小说」即可下载全书内容。</Paragraph>
        <Paragraph>
          已获取的小说也可以随时在<Link to="/novels">全部小说</Link>
          中找到并打开详情页，点击「获取」或「获取全部分卷」补抓章节正文。等待任务完成后，章节即可阅读。
        </Paragraph>
      </section>

      <section style={{ padding: '4px 0 4px 24px', borderLeft: '2px solid var(--br-border-strong)' }}>
        <Title level={3} style={{ marginTop: 0 }}>
          <FileDoneOutlined /> 第四步：导出下载 EPUB
        </Title>
        <Paragraph>将小说导出为 EPUB 电子书，可离线阅读或拷贝到电子书设备：</Paragraph>
        <ol>
          <li>打开小说详情页。</li>
          <li>点击「生成导出文件」。</li>
          <li>在窗口中选择 EPUB 格式，点击“创建”开始生成任务。</li>
          <li>在任务请求详情页查看进度，完成后返回小说详情页下载文件。</li>
        </ol>
        <Paragraph>
          <Text type="warning">
            注意：请先完成「获取书」步骤（下载章节正文）再生成导出文件；仅抓取了章节列表而没有正文时，系统会拒绝生成并提示先获取正文。
          </Text>
        </Paragraph>
      </section>
    </div>
  );
};
