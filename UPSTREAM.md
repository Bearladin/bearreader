# 上游来源说明

BearReader 是派生项目，不是从零开始的原创项目。以下上游代码构成了本项目的起点：

- 后端：<https://github.com/lncrawl/lightnovel-crawler>，基线提交 `59b0382d51927953aa8120c5de62dab23ce3f731`
- 前端：<https://github.com/rolandng84/lncrawl-web>，基线提交 `81c42a335fb11faa8f219f1c6509a1e4a59d8d6f`
- 许可证：GPL-3.0（沿上游）；前端及其依赖许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
- 上游历史更新日志见 [docs/UPSTREAM_CHANGELOG.md](docs/UPSTREAM_CHANGELOG.md)

上游仅作只读参考，不直接合并。上游修复先在参考克隆中调查，再以 BearReader 自己的提交选择性移植，并在提交说明中记录来源提交。
