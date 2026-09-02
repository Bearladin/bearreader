import { Auth } from '@/store/_auth';
import type { Job } from '@/types';
import { Alert } from 'antd';
import { useMemo } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';

const CAPTCHA_FAILURES = ['HTTPError: 403 Client Error: Forbidden for url'];

const LEGACY_JOB_MESSAGES: Record<string, string> = {
  'Canceled by user': '任务已取消',
  'Canceled by admin': '任务已取消',
  'Canceled by one of the parent': '因上级任务取消而取消',
  'Canceled as the parent job was canceled by user': '因关联任务取消而结束',
  'Canceled as the parent job was canceled by admin': '因关联任务取消而结束',
  'No novel id': '缺少小说 ID',
  'No novel url': '缺少小说 URL',
  'No volume id': '缺少分卷 ID',
  'No chapter id': '缺少章节 ID',
  'No image id': '缺少图片 ID',
  'No output format': '未指定导出格式',
  'No target language': '未指定目标语言',
  'No chapter content': '章节没有可翻译的正文',
  'No epub request found': '找不到 EPUB 导出任务',
  'Failed to fetch contents': '获取章节正文失败',
  'Failed to download image': '下载图片失败',
  'Failed to make artifact': '生成导出文件失败',
  'Source domain is not specified': '未指定书源域名',
  'Search query must be at least 2 characters long':
    '搜索关键词至少需要 2 个字',
  'Unexpected runner error': '任务调度器发生意外错误',
};

const FAILURE_HEADLINES: Record<string, string> = {
  impassable: '站点要求无法由抓取器伪造的凭据',
  exhausted: '当前配置可用的重试与绕过方式均已尝试，但请求仍未成功',
  blocked: '站点拒绝了本次请求',
  unreachable: '请求未能到达站点或未收到响应',
  poisoned: '站点返回了疑似无效或诱导内容',
  tier_unavailable: '当前配置没有可处理此请求的抓取能力',
  missing_dependency: '处理此请求所需的可选组件尚未安装',
  render_failed: '浏览器已打开页面，但未出现书源需要的内容',
  solve_failed: '浏览器未能完成站点验证',
  http_error: '站点返回了错误响应',
  bad_image: '站点返回的图片内容无法解析',
  aborted: '请求已中止',
  failed: '请求执行失败',
};

const FAILURE_ADVICE: Record<string, string> = {
  render_failed:
    '可能是书源等待的页面元素没有出现、选择器已经失效，或页面加载时间超过浏览器渲染时限。',
  solve_failed:
    '请确认已安装可用浏览器、浏览器窗口能够正常启动，并为验证过程预留足够时间。',
  missing_dependency: '请检查是否使用完整依赖安装，并重新安装缺失的可选组件。',
  tier_unavailable: '请检查浏览器抓取、代理和归档读取等能力是否已正确配置。',
  bad_image: '请稍后重试；若持续出现，通常需要修正书源的图片地址或解析规则。',
  poisoned: '为避免保存错误内容，本次结果已拒绝；请改用其他书源或等待书源修复。',
};

const STANCE_ADVICE: Record<string, string> = {
  satisfy: '需要调整抓取器生成的请求签名，这不是用户设置可以解决的问题。',
  lease: '只有更换网络出口才可能解决；可在抓取设置中配置代理或 Tor 地址池。',
  accumulate: '站点正在根据访问历史判断请求；应降低该书源的访问频率，更换地址通常无效。',
  solve: '需要真实浏览器完成验证；请确认浏览器抓取已启用并且本机已安装浏览器。',
  avoid: '该请求触发了本可避免的限制，需要修改书源请求方式。',
  delegate: '继续处理需要当前应用未集成的外部付费服务，因此没有可用的本地设置。',
  refuse: '此内容需要有效账号凭据或已注册的访问身份，无法通过技术绕过。',
};

const STATUS_NOTES: Record<number, string> = {
  404: '页面不存在，通常表示该书源的网址规则已经变化。',
  410: '站点明确表示该页面已永久删除。',
  451: '站点因法律原因拒绝提供该页面。',
};

const localizeJobMessage = (message: string): string => {
  const known = LEGACY_JOB_MESSAGES[message];
  if (known) return known;

  let match = message.match(/^Invalid format: (.+)$/);
  if (match) return `不支持的导出格式：${match[1]}`;

  match = message.match(/^Dependency job not found for (.+)$/);
  if (match) return `找不到 ${match[1]} 所需的前置任务`;

  match = message.match(/^Job type is not supported: (.+)$/);
  if (match) return `不支持的任务类型：${match[1]}`;

  match = message.match(
    /^(?:HTTPError: )?(\d{3}) (?:Client|Server) Error: .+ for url: (.+)$/
  );
  if (match) return `站点返回错误（HTTP ${match[1]}）：${match[2]}`;

  return message;
};

const localizeDiagnosedFailure = (job: Job): string | undefined => {
  const kind = job.extra.failure_kind;
  if (!kind) return undefined;

  let headline = FAILURE_HEADLINES[kind] ?? FAILURE_HEADLINES.failed;
  if (job.extra.status_code != null) {
    headline += `（HTTP ${job.extra.status_code}）`;
  }
  if (job.extra.failure_url) {
    headline += `：${job.extra.failure_url}`;
  }

  const lines = [headline];
  const detail = job.extra.failure_detail ?? '';
  const attemptMatch = detail.match(/gave up after (\d+) attempts?/i);
  const attempts = attemptMatch ? Number(attemptMatch[1]) : undefined;
  const count = attempts ? `连续 ${attempts} 次请求` : '请求';
  const hasLayer = job.extra.blocking_layer != null;

  if (kind === 'exhausted' && /transport failure \(Timeout\)|\bTimeout\b/i.test(detail)) {
    lines.push(
      `${count}均超时，未收到 HTTP 状态码${
        hasLayer ? '' : '，也未识别到明确的站点防护层'
      }。`
    );
  } else if (kind === 'exhausted') {
    lines.push(
      `${count}均未取得可用响应${
        hasLayer ? '' : '，但未识别到明确的站点防护层'
      }。`
    );
  } else if (kind === 'unreachable') {
    lines.push('连接可能被本机网络、DNS、代理设置或站点临时故障中断。');
  }

  const statusNote =
    job.extra.status_code != null
      ? STATUS_NOTES[job.extra.status_code]
      : undefined;
  if (statusNote) lines.push(statusNote);

  if (hasLayer && job.extra.stance) {
    const advice = STANCE_ADVICE[job.extra.stance];
    if (advice) {
      lines.push(`检测到第 ${job.extra.blocking_layer} 层站点防护。${advice}`);
    }
  } else if (['exhausted', 'blocked', 'unreachable'].includes(kind)) {
    lines.push(
      '请检查本机网络、DNS 和代理设置，或稍后重试；若其他网站正常，也可能是该站点暂时不可用。'
    );
  }

  const advice = FAILURE_ADVICE[kind];
  if (advice) lines.push(advice);
  return lines.join('\n');
};

export const JobErrorDetailsCard: React.FC<{ job: Job }> = ({ job }) => {
  const isAdmin = useSelector(Auth.select.isAdmin);

  const text = useMemo(() => {
    const diagnosed = localizeDiagnosedFailure(job);
    if (diagnosed) return diagnosed;

    if (/^An unexpected error stopped this .+ job\./m.test(String(job.error))) {
      return '任务因程序内部异常而停止。这属于应用或书源程序问题，不是网站拒绝请求；请提交问题反馈。';
    }

    const lines = String(job.error).split('\n').filter(Boolean);
    if (isAdmin) {
      return lines.map(localizeJobMessage).join('\n');
    } else if (lines.length > 0) {
      return localizeJobMessage(lines[lines.length - 1]);
    }
    return '未知错误';
  }, [job, isAdmin]);

  const hasCaptchaFailure = useMemo(() => {
    return CAPTCHA_FAILURES.some((failure) =>
      String(job.error).includes(failure)
    );
  }, [job.error]);

  if (!job.error) {
    return null;
  }

  return (
    <div style={{ margin: '15px 0' }}>
      <pre
        style={{
          fontSize: '0.775rem',
          maxHeight: 300,
          margin: 0,
          marginBottom: 10,
          padding: '10px 20px',
          whiteSpace: 'nowrap',
          overflow: 'auto',
          color: '#6E5125',
          border: '1px solid #967238',
          background: '#F7F1E5',
          borderRadius: 2,
        }}
      >
        {text}
      </pre>
      {hasCaptchaFailure && (
        <div style={{ margin: '15px 0' }}>
          <Alert
            type="warning"
            title={
              <>
                此问题由 Cloudflare CAPTCHA
                验证引起，自动书源无法绕过。请尝试在
                <Link to="/meta/sources?tab=used">其他可用书源</Link>
                中搜索该小说。
              </>
            }
          />
        </div>
      )}
    </div>
  );
};
