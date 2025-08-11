# 字幕翻译系统 RESTful API

这是字幕翻译系统的RESTful API，基于FastAPI构建，提供完整的字幕翻译服务接口。

## 功能特性

### 🎯 核心功能
- **项目管理**: 创建、查看、更新、删除翻译项目
- **文件管理**: 上传、下载、删除字幕文件
- **翻译任务**: 创建、监控、取消翻译任务
- **进度监控**: 实时跟踪翻译进度和系统状态
- **用户认证**: JWT令牌认证和权限管理
- **速率限制**: 防止API滥用的速率限制机制

### 🔒 安全特性
- JWT访问令牌和刷新令牌
- 基于角色的权限控制
- 请求速率限制
- IP地址黑白名单
- 文件类型和大小验证
- CORS跨域保护

### 📊 监控特性
- 健康检查端点
- 系统统计信息
- 实时进度跟踪
- 错误日志记录
- 性能指标收集

## 快速开始

### 环境要求
- Python 3.8+
- FastAPI 0.104.0+
- 字幕翻译系统核心组件

### 安装依赖
```bash
# 进入API目录
cd subtitle-translation-system/api

# 安装依赖包
pip install -r requirements.txt
```

### 启动服务

#### 方式1: 使用启动脚本 (推荐)
```bash
python run_api.py
```

#### 方式2: 使用uvicorn直接启动
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 方式3: 生产环境启动
```bash
python run_api.py --host 0.0.0.0 --port 8000 --workers 4
```

### 访问地址
- API服务: http://localhost:8000
- API文档: http://localhost:8000/docs
- ReDoc文档: http://localhost:8000/redoc
- OpenAPI规范: http://localhost:8000/openapi.json

## API文档

### 认证接口

#### 用户登录
```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

响应:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user_info": {
    "user_id": "user_001",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

#### 刷新令牌
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 项目管理接口

#### 创建项目
```http
POST /projects
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "我的翻译项目",
  "description": "项目描述",
  "source_language": "zh-CN",
  "target_languages": ["en-US", "ja-JP"]
}
```

#### 获取项目列表
```http
GET /projects?skip=0&limit=100
Authorization: Bearer <access_token>
```

#### 获取项目详情
```http
GET /projects/{project_id}
Authorization: Bearer <access_token>
```

### 文件管理接口

#### 上传文件
```http
POST /projects/{project_id}/files
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file: <subtitle_file.srt>
```

#### 获取文件列表
```http
GET /projects/{project_id}/files
Authorization: Bearer <access_token>
```

#### 删除文件
```http
DELETE /projects/{project_id}/files/{file_id}
Authorization: Bearer <access_token>
```

### 翻译任务接口

#### 创建翻译任务
```http
POST /translation/tasks
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "project_id": "project_001",
  "file_ids": ["file_001", "file_002"],
  "source_language": "zh-CN",
  "target_languages": ["en-US", "ja-JP"],
  "quality_requirements": {
    "level": "high",
    "enable_context_analysis": true,
    "enable_cultural_adaptation": true,
    "enable_terminology_consistency": true
  },
  "processing_options": {
    "max_concurrent_tasks": 3,
    "retry_attempts": 3,
    "timeout_minutes": 30
  }
}
```

#### 获取任务列表
```http
GET /translation/tasks?project_id=project_001&status=running
Authorization: Bearer <access_token>
```

#### 获取任务详情
```http
GET /translation/tasks/{task_id}
Authorization: Bearer <access_token>
```

### 进度监控接口

#### 获取任务进度
```http
GET /monitoring/progress/{task_id}
Authorization: Bearer <access_token>
```

#### 获取系统统计
```http
GET /monitoring/statistics
Authorization: Bearer <access_token>
```

### 系统接口

#### 健康检查
```http
GET /health
```

#### 系统信息
```http
GET /
```

## 配置选项

### 环境变量
```bash
# 基础配置
APP_NAME="字幕翻译系统 API"
APP_VERSION="1.0.0"
DEBUG=false

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 文件上传配置
MAX_FILE_SIZE=52428800  # 50MB
UPLOAD_DIR=uploads
ALLOWED_FILE_TYPES=srt,vtt,ass,ssa,txt

# 速率限制配置
RATE_LIMIT_ENABLED=true
DEFAULT_RATE_LIMIT_PER_MINUTE=60
DEFAULT_RATE_LIMIT_PER_HOUR=1000
DEFAULT_RATE_LIMIT_PER_DAY=10000

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=api.log

# 数据库配置（可选）
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379
```

### 配置文件
创建 `.env` 文件来设置环境变量:
```bash
cp .env.example .env
# 编辑 .env 文件设置你的配置
```

## 错误处理

### 错误响应格式
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "请求参数验证失败",
  "details": {
    "field": "username",
    "issue": "字段不能为空"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 常见错误代码
- `AUTHENTICATION_FAILED`: 认证失败
- `INVALID_TOKEN`: 无效令牌
- `RATE_LIMIT_EXCEEDED`: 超出速率限制
- `VALIDATION_ERROR`: 参数验证错误
- `NOT_FOUND`: 资源不存在
- `FILE_TOO_LARGE`: 文件过大
- `UNSUPPORTED_LANGUAGE`: 不支持的语言

## 测试

### 运行API测试
```bash
# 启动API服务
python run_api.py

# 在另一个终端运行测试
python test_api.py
```

### 测试覆盖的功能
- 健康检查和基础端点
- 用户认证和令牌管理
- 项目CRUD操作
- 文件上传和管理
- 翻译任务创建和监控
- 系统统计和监控
- 速率限制功能

### 测试结果
测试结果会保存到 `api_test_results.json` 文件中。

## 部署

### Docker部署
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run_api.py", "--host", "0.0.0.0", "--port", "8000"]
```

### 使用Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=your-secret-key
      - DATABASE_URL=postgresql://user:pass@db:5432/subtitle_db
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=subtitle_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:6-alpine
    
volumes:
  postgres_data:
```

### 生产环境部署
1. 设置环境变量
2. 配置反向代理（Nginx）
3. 设置SSL证书
4. 配置日志轮转
5. 设置监控和告警

## 性能优化

### 建议配置
- 使用多个工作进程
- 启用Redis缓存
- 配置数据库连接池
- 启用gzip压缩
- 设置适当的超时时间

### 监控指标
- 请求响应时间
- 错误率
- 并发连接数
- 内存和CPU使用率
- 数据库连接数

## 安全最佳实践

1. **认证安全**
   - 使用强密码策略
   - 定期轮换JWT密钥
   - 设置合理的令牌过期时间

2. **API安全**
   - 启用HTTPS
   - 配置CORS策略
   - 实施速率限制
   - 验证输入参数

3. **文件安全**
   - 限制文件类型和大小
   - 扫描恶意文件
   - 隔离文件存储

4. **网络安全**
   - 使用防火墙
   - 配置IP白名单
   - 监控异常访问

## 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查端口是否被占用
   lsof -i :8000
   
   # 检查依赖是否安装
   pip list | grep fastapi
   ```

2. **认证失败**
   - 检查JWT密钥配置
   - 验证用户凭据
   - 确认令牌未过期

3. **文件上传失败**
   - 检查文件大小限制
   - 验证文件格式
   - 确认上传目录权限

4. **数据库连接失败**
   - 检查数据库服务状态
   - 验证连接字符串
   - 确认网络连通性

### 日志查看
```bash
# 查看API日志
tail -f api.log

# 查看错误日志
grep ERROR api.log

# 查看访问日志
grep "POST\|GET\|PUT\|DELETE" api.log
```

## 开发指南

### 添加新的API端点
1. 在 `main.py` 中定义路由
2. 在 `models.py` 中定义数据模型
3. 添加认证和权限检查
4. 编写测试用例
5. 更新API文档

### 自定义异常处理
1. 在 `exceptions.py` 中定义异常类
2. 在 `main.py` 中注册异常处理器
3. 返回标准化错误响应

### 扩展认证系统
1. 修改 `auth.py` 中的认证逻辑
2. 添加新的权限检查
3. 更新用户模型
4. 测试认证流程

## 更新日志

### v1.0.0 (当前版本)
- 初始版本发布
- 完整的RESTful API接口
- JWT认证和权限管理
- 速率限制和安全防护
- 自动化测试和文档
- 生产环境部署支持

## 许可证

本软件遵循项目主许可证条款。

## 技术支持

如果遇到问题或需要技术支持，请：
1. 查看本文档的故障排除部分
2. 检查API日志信息
3. 运行测试脚本验证功能
4. 联系技术支持团队