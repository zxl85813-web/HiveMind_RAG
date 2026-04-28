# 📊 HiveMind 测试报告体系指南

> 本文档描述项目的测试报告基础设施：Allure 聚合报告 + SonarQube 代码质量扫描。

---

## 1. 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                    CI Pipeline (GitHub Actions)                  │
│                                                                  │
│  feature-ci ──┐                                                  │
│  develop-ci ──┤── pytest --alluredir ──► allure-results-backend  │
│  release-ci ──┤── vitest (coverage)  ──► allure-results-frontend │
│  backend-ci ──┘                                                  │
│       │                          │                               │
│       ▼                          ▼                               │
│  ┌──────────┐           ┌────────────────┐                       │
│  │ SonarQube│           │ Allure Report  │                       │
│  │ Scanner  │           │ Generator      │                       │
│  └────┬─────┘           └───────┬────────┘                       │
│       │                         │                                │
│       ▼                         ▼                                │
│  SonarQube Server        GitHub Pages                            │
│  (Quality Gate)          (HTML Dashboard)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Allure 聚合报告

### 2.1 工作原理

每个 CI pipeline 的 test job 会：
1. 运行 pytest / vitest 并生成 Allure JSON 结果文件
2. 上传 `allure-results-*` artifact 到 GitHub Actions
3. `test-report.yml` workflow 下载所有结果，合并后生成 HTML 报告
4. 报告发布到 GitHub Pages，包含历史趋势图

### 2.2 访问地址

```
https://<your-org>.github.io/<repo-name>/
```

### 2.3 报告内容

| 页面 | 说明 |
|------|------|
| Overview | 总览：通过/失败/跳过数量、持续时间 |
| Suites | 按测试套件分组（后端 unit/integration、前端 components） |
| Graphs | 趋势图：历史通过率、持续时间变化 |
| Timeline | 测试执行时间线（并行度可视化） |
| Categories | 失败分类（Product Defects vs Test Defects） |
| Packages | 按 Python 包 / TS 模块分组 |

### 2.4 本地生成报告

```bash
# 后端
cd backend
pip install allure-pytest
pytest tests/ --alluredir=allure-results
allure serve allure-results

# 前端（需要安装 allure-vitest）
cd frontend
npm run test:unit
allure serve allure-results
```

### 2.5 各分支的 Artifact 保留策略

| 分支 | Artifact 名称 | 保留天数 |
|------|---------------|----------|
| feature/* | allure-results-backend-feature | 5 天 |
| develop | allure-results-backend-develop / frontend-develop | 10 天 |
| main | allure-results-backend-main / frontend-main | 30 天 |
| release/* | allure-results-backend-release / frontend-release | 30 天 |

---

## 3. SonarQube 集成

### 3.1 前置条件

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中配置：

| Secret | 说明 | 示例 |
|--------|------|------|
| `SONAR_TOKEN` | SonarQube 用户 Token | `squ_xxxxxxxxxxxx` |
| `SONAR_HOST_URL` | SonarQube 服务器地址 | `http://your-server:9000` |

### 3.2 触发时机

| 事件 | 触发的 Workflow | 扫描类型 |
|------|----------------|----------|
| push → develop | sonarqube.yml | 分支扫描 |
| push → main | sonarqube.yml + deploy.yml | 分支扫描 + 部署前门禁 |
| PR → develop/main | sonarqube.yml | PR 增量扫描 + Quality Gate |

### 3.3 覆盖率上报

SonarQube 接收两份覆盖率报告：

- **后端**: `backend/coverage.xml` (Cobertura XML, pytest-cov 生成)
- **前端**: `frontend/coverage/lcov.info` (LCOV, vitest v8 生成)

### 3.4 Quality Gate（建议配置）

在 SonarQube 服务器上创建自定义 Quality Gate `HiveMind`：

| 指标 | 条件 | 阈值 |
|------|------|------|
| 新代码覆盖率 | >= | 80% |
| 新代码重复率 | <= | 3% |
| 新代码可维护性评级 | = | A |
| 新代码可靠性评级 | = | A |
| 新代码安全评级 | = | A |
| 新代码安全热点审查率 | >= | 100% |

### 3.5 SonarQube 服务器端配置

1. 登录 SonarQube → Administration → Projects → Create Project
2. Project Key: `HiveMind_RAG`
3. 生成 Token: My Account → Security → Generate Token
4. 将 Token 和 URL 添加到 GitHub Secrets

---

## 4. 本地开发者工作流

### 4.1 运行测试并查看覆盖率

```bash
# 后端 — 生成 HTML 覆盖率报告
cd backend
pytest tests/ --cov=app --cov-report=html:htmlcov
# 打开 htmlcov/index.html

# 前端 — 生成覆盖率报告
cd frontend
npm run test:unit
# 打开 coverage/index.html
```

### 4.2 本地 Allure 报告

```bash
# 安装 Allure CLI (macOS)
brew install allure

# 安装 Allure CLI (Windows, via scoop)
scoop install allure

# 后端
cd backend
pytest tests/ --alluredir=allure-results -o "addopts="
allure serve allure-results

# 前端
cd frontend
npm run test:unit
allure serve allure-results
```

---

## 5. 故障排查

### Allure 报告为空
- 检查 CI 日志中 `allure-results-*` artifact 是否上传成功
- 确认 pytest 安装了 `allure-pytest`：`pip list | grep allure`
- 确认 `--alluredir=allure-results` 参数生效

### SonarQube 扫描失败
- 检查 `SONAR_TOKEN` 和 `SONAR_HOST_URL` 是否正确配置
- 确认 SonarQube 服务器可从 GitHub Actions runner 访问（公网或 self-hosted runner）
- 查看 CI 日志中 SonarQube Scanner 的输出

### 覆盖率数据未显示在 SonarQube
- 确认 `coverage.xml` 和 `lcov.info` 文件路径正确
- 检查 `sonar-project.properties` 中的路径配置
- SonarQube 社区版不支持 PR decoration，增量数据在 New Code 页面查看
