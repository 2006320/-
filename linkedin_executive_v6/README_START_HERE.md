# 独立 LinkedIn 高管链接筛选 APP（不依赖 Replit）

本项目是一套可自行运行的 **Streamlit 网页界面 + PostgreSQL 持久库 + 独立后台 Worker**。可导入 LinkedIn 链接、普通网页链接及 Keenable 搜索结果 JSON；包含历史去重池、任务暂停/恢复、模板、证据与 Excel 导出。**不是无需服务器的永久在线服务**。

## Windows 最简启动
1. 安装 Docker Desktop 并启动。
2. 将 `.env.example` 复制为 `.env`，分别设置两个**不同**的强密码（切勿公开或提交）。
3. 双击 `start_windows.bat`；首次构建可能需要下载镜像与依赖。
4. 打开 `http://localhost:8501`，输入 APP_PASSWORD。
5. 首次历史数据初始化：在本目录终端运行 `docker compose run --rm web python seed_history.py`（一次即可，重复运行不会产生重复链接）。
6. 查看任务处理：`docker compose logs -f worker`。停止：`docker compose down`（不会删除数据库卷）。

## 云端
在自己的 VPS 安装 Docker Compose，配置 `.env`，运行 `docker compose up -d --build`。默认网页仅绑定 `127.0.0.1`，**不会直接暴露公网**。请使用 HTTPS 反向代理、访问控制及备份后再公开服务；需要公开访问时把反向代理指向本机 8501。云端服务器及域名可能收费。

## 功能边界
- 不会直接读取其他 ChatGPT 窗口；需导入 TXT/CSV 历史链接。
- Keenable 插件结果通过 JSON 导入；独立 APP 不自动获得 ChatGPT 插件 API 凭证。
- 没有提供合法、可直接调用的公开搜索 API 时，APP **不会自主无限发现新个人资料**。
- 仅访问允许公开访问的网页，不绕过登录/验证码/反爬；LinkedIn 受限页面需合法授权的资料。
- 搜索摘要不能充当职业年份的已验证证据。年份和职位判定为启发式，合格结果需要人工复核。
- 默认单一共享口令，非多租户权限系统；对外商用前需强化身份认证、访问控制、监控与备份。

## 开发测试
`python -m compileall -q .` 与 `python -m unittest discover -s tests -v`。需要真实 PostgreSQL 的端到端联调，请启动 Docker 环境后验证。
