# Go + Vue 初始化与验收基线

## 目录原则

只创建真实启动链路需要的目录。默认的模块化单体可以从下面的形态开始，随着业务增长再拆分：

```text
project/
├── AGENTS.md
├── README.md
├── docs/architecture/0001-foundation.md
├── backend/
│   ├── go.mod
│   ├── cmd/server/main.go
│   └── internal/
│       ├── platform/        # 配置、日志、数据库、HTTP 装配
│       └── <domain>/        # handler、service、repository、model 按真实业务增加
└── frontend/
    ├── package.json
    └── src/
        ├── app/             # 入口、路由、全局装配
        ├── features/<domain>/
        └── shared/          # 真正跨业务复用的组件和 API 客户端
```

小项目可以省略 `internal/platform` 的细分包；不要为了“完整架构”生成空的 domain、repository 或 worker。

## 初始化顺序

1. 检查目标目录和用户指令，保留已有文件与未提交改动。
2. 根据确认的模块边界创建 Go Module 和 Vue 项目；版本通过当前工具链核对。
3. 先实现健康检查、配置加载、请求 ID、统一错误响应和最小前端路由。
4. 只有问卷确认需要数据库时才接入 PostgreSQL、连接池和迁移目录。
5. 只有真实业务需要时才接入鉴权、对象存储、异步任务、缓存或第三方 SDK。
6. 写 `AGENTS.md` 和 ADR，记录选择、未选方案和触发条件。

## 依赖方向

```text
frontend feature -> frontend shared API -> HTTP API
HTTP route -> controller/handler -> service -> repository -> model/database
service -> gateway/client -> external provider
```

业务规则不能依赖 HTTP 传输类型；前端不能读取数据库；上游密钥只在服务端配置和 provider 边界内出现。跨模块共享必须经过明确的公共技术包或业务所有者，不能通过复制 DTO 隐式共享。

## 交付检查

### 后端

- `gofmt` 无未格式化文件。
- `go test ./...` 通过；存在并发逻辑时增加 `go test -race ./...`。
- `go vet ./...` 和 `go build ./...` 通过。
- 配置使用 `.env.example` 或配置示例，不能包含真实凭据。
- 数据库写入有事务边界，查询传递 Context，错误响应不泄露 SQL 或堆栈。

### 前端

- 锁文件与 `package.json` 一致。
- 已配置的类型检查、Lint、单元测试和生产构建全部执行并记录结果。
- API 地址来自环境配置；不把服务端密钥打进前端包。
- 关键流程至少有一个可重复的浏览器或组件验证路径。

### 文档

- ADR 包含背景、决策、备选、代价、量化指标和重新评估条件。
- README 说明本地依赖、启动、检查和环境变量。
- 报告中明确“本次没有做什么”。
