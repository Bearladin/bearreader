
/**
 * 旧数据兼容：历史库存量卷名是 "Volume N" / "Unknown"（抓取时基类默认值
 * 为英文），新数据已是「第 N 卷」。显示层统一转换，不迁移数据库。
 */
export function volumeTitle(title: string | undefined): string {
  if (!title) return '未知卷';
  const legacy = title.match(/^Volume\s+(\d+)$/i);
  if (legacy) return `第 ${legacy[1]} 卷`;
  if (title === 'Unknown') return '未知卷';
  return title;
}
