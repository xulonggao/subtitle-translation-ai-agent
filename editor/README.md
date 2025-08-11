# 字幕翻译在线编辑器

这是字幕翻译系统的在线编辑和审核模块，提供完整的协作编辑、版本控制和审核工作流功能。

## 功能特性

### 🎯 核心功能
- **在线编辑器**: 实时协作的字幕编辑界面
- **审核工作流**: 完整的翻译审核和评论系统
- **版本控制**: 文档版本管理和变更跟踪
- **协作编辑**: 多用户同时编辑，实时同步
- **锁定机制**: 防止编辑冲突的条目锁定
- **评论系统**: 审核员评论和建议功能

### ✏️ 编辑功能
- **实时编辑**: 在线修改字幕内容
- **条目锁定**: 编辑时自动锁定条目
- **变更跟踪**: 记录所有编辑历史
- **撤销重做**: 支持编辑操作的撤销
- **批量操作**: 批量编辑和格式化
- **搜索替换**: 全文搜索和替换功能

### 🔍 审核功能
- **评论系统**: 针对特定条目添加评论
- **建议修改**: 提供具体的修改建议
- **严重程度**: 标记问题的严重程度
- **审核状态**: 跟踪审核进度和状态
- **批准流程**: 多级审核和批准机制
- **质量评分**: 翻译质量评估

### 👥 协作功能
- **多用户编辑**: 支持多人同时编辑
- **实时同步**: 编辑内容实时同步
- **用户状态**: 显示在线用户和编辑状态
- **冲突解决**: 自动处理编辑冲突
- **活动历史**: 记录所有协作活动
- **通知系统**: 实时通知和提醒

### 📚 版本控制
- **版本管理**: 创建和管理文档版本
- **变更历史**: 详细的变更记录
- **版本比较**: 对比不同版本的差异
- **版本恢复**: 恢复到历史版本
- **分支合并**: 支持分支和合并操作
- **标签管理**: 为重要版本添加标签

## 技术架构

### 📁 文件结构
```
editor/
├── __init__.py              # 模块初始化
├── models.py                # 数据模型定义
├── editor_manager.py        # 编辑器核心管理
├── web_editor.py           # Streamlit Web界面
├── api_endpoints.py        # FastAPI接口端点
├── test_editor.py          # 功能测试脚本
└── README.md              # 使用文档
```

### 🏗️ 核心组件

#### 数据模型 (models.py)
- **SubtitleEntry**: 字幕条目模型
- **EditDocument**: 编辑文档模型
- **DocumentVersion**: 文档版本模型
- **EditChange**: 编辑变更记录
- **ReviewComment**: 审核评论模型
- **EditSession**: 编辑会话模型
- **CollaborationEvent**: 协作事件模型

#### 编辑器管理器 (editor_manager.py)
- **EditorManager**: 核心管理类
- 文档生命周期管理
- 编辑会话管理
- 协作和同步控制
- 版本控制逻辑
- 数据持久化

#### Web界面 (web_editor.py)
- **WebEditor**: Streamlit界面类
- 直观的编辑界面
- 实时协作显示
- 审核和评论功能
- 版本管理界面
- 统计和监控面板

#### API接口 (api_endpoints.py)
- RESTful API端点
- WebSocket实时通信
- 认证和权限控制
- 数据验证和错误处理
- 事件广播机制

## 快速开始

### 环境要求
- Python 3.8+
- Streamlit 1.28.0+
- FastAPI 0.104.0+
- WebSocket支持

### 安装依赖
```bash
# 进入编辑器目录
cd subtitle-translation-system/editor

# 安装依赖包
pip install streamlit fastapi uvicorn websockets
```

### 启动Web编辑器
```bash
# 启动Streamlit编辑器
streamlit run web_editor.py --server.port 8503
```

### 启动API服务
```bash
# 启动FastAPI服务
uvicorn api_endpoints:router --host 0.0.0.0 --port 8001
```

### 访问地址
- Web编辑器: http://localhost:8503
- API文档: http://localhost:8001/docs

## 使用指南

### 1. 文档管理

#### 创建新文档
1. 在"文档管理"页面点击"创建新文档"
2. 填写文档标题和项目信息
3. 选择源语言和目标语言
4. 输入或导入字幕内容
5. 点击"创建文档"

#### 打开现有文档
1. 在文档列表中找到目标文档
2. 点击"打开"按钮
3. 文档将在编辑器中打开

### 2. 在线编辑

#### 开始编辑
1. 打开文档后，点击"开始编辑"
2. 系统将创建编辑会话
3. 可以看到其他在线用户

#### 编辑字幕条目
1. 点击条目的"编辑"按钮
2. 条目将被锁定，防止冲突
3. 修改译文内容
4. 点击"保存修改"完成编辑
5. 条目自动解锁

#### 搜索和过滤
- 使用搜索框查找特定内容
- 勾选"仅显示有评论的条目"过滤
- 调整每页显示数量

### 3. 审核管理

#### 添加评论
1. 在条目下方点击"添加评论"
2. 输入评论内容和建议
3. 选择严重程度级别
4. 点击"发表评论"

#### 解决评论
1. 查看评论内容和建议
2. 根据建议修改内容
3. 点击"标记为已解决"

#### 更新文档状态
1. 在"审核管理"页面选择新状态
2. 点击"更新状态"
3. 状态变更将通知所有用户

### 4. 版本控制

#### 创建新版本
1. 在"版本控制"页面点击"创建新版本"
2. 输入版本描述
3. 点击"创建版本"
4. 新版本将成为当前版本

#### 查看版本历史
1. 在版本列表中查看所有版本
2. 点击"详情"查看版本信息
3. 点击"恢复"回到历史版本

### 5. 协作历史

#### 查看活动记录
1. 在"协作历史"页面查看所有活动
2. 按时间顺序显示用户操作
3. 包含详细的操作信息

#### 监控用户活动
- 查看当前在线用户
- 跟踪编辑活动
- 监控评论和审核进度

## API接口

### 文档管理接口

#### 创建文档
```http
POST /editor/documents
Content-Type: application/json

{
  "title": "文档标题",
  "project_id": "项目ID",
  "source_language": "en-US",
  "target_language": "zh-CN",
  "entries_data": [...],
  "created_by": "用户ID"
}
```

#### 获取文档列表
```http
GET /editor/documents?project_id=xxx&status=draft
```

#### 获取文档详情
```http
GET /editor/documents/{document_id}
```

### 编辑会话接口

#### 开始编辑会话
```http
POST /editor/sessions
Content-Type: application/json

{
  "document_id": "文档ID",
  "user_id": "用户ID",
  "user_name": "用户名"
}
```

#### 结束编辑会话
```http
DELETE /editor/sessions/{session_id}
```

### 条目编辑接口

#### 锁定条目
```http
POST /editor/sessions/{session_id}/lock
Content-Type: application/json

{
  "entry_id": "条目ID"
}
```

#### 编辑条目
```http
PUT /editor/sessions/{session_id}/entries/{entry_id}
Content-Type: application/json

{
  "field_name": "translated_text",
  "new_value": "新的翻译内容",
  "comment": "编辑说明"
}
```

### 评论接口

#### 添加评论
```http
POST /editor/documents/{document_id}/comments
Content-Type: application/json

{
  "entry_id": "条目ID",
  "reviewer_id": "审核员ID",
  "reviewer_name": "审核员姓名",
  "comment": "评论内容",
  "suggestion": "修改建议",
  "severity": "warning"
}
```

#### 解决评论
```http
PUT /editor/documents/{document_id}/comments/{comment_id}/resolve
Content-Type: application/json

{
  "resolved_by": "解决者ID"
}
```

### WebSocket接口

#### 连接WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8001/editor/ws/{session_id}');

// 订阅文档更新
ws.send(JSON.stringify({
  type: 'subscribe',
  document_id: 'document_id'
}));

// 发送心跳
ws.send(JSON.stringify({
  type: 'heartbeat'
}));
```

## 数据模型

### 字幕条目 (SubtitleEntry)
```python
{
  "id": "条目ID",
  "sequence": 1,
  "start_time": "00:00:01,000",
  "end_time": "00:00:03,000",
  "original_text": "原文",
  "translated_text": "译文",
  "notes": "备注",
  "confidence_score": 0.95,
  "is_locked": false,
  "updated_by": "用户ID"
}
```

### 编辑文档 (EditDocument)
```python
{
  "id": "文档ID",
  "title": "文档标题",
  "project_id": "项目ID",
  "source_language": "en-US",
  "target_language": "zh-CN",
  "status": "draft",
  "current_version": "1.0.0",
  "versions": [...],
  "comments": [...],
  "active_sessions": [...]
}
```

### 审核评论 (ReviewComment)
```python
{
  "id": "评论ID",
  "entry_id": "条目ID",
  "reviewer_id": "审核员ID",
  "reviewer_name": "审核员姓名",
  "comment": "评论内容",
  "suggestion": "修改建议",
  "severity": "warning",
  "is_resolved": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

## 测试

### 运行功能测试
```bash
# 运行编辑器测试
python test_editor.py
```

### 测试覆盖范围
- ✅ 文档创建和管理
- ✅ 编辑会话管理
- ✅ 条目锁定和编辑
- ✅ 评论添加和解决
- ✅ 版本创建和管理
- ✅ 文档状态更新
- ✅ 文档导出功能
- ✅ 协作事件记录
- ✅ 统计信息获取
- ✅ 并发编辑处理
- ✅ 会话清理机制

### 测试结果示例
```
📊 测试结果总结
------------------------------
总测试数: 11
通过: 11
失败: 0
成功率: 100.0%
```

## 部署

### 开发环境
```bash
# 启动Web编辑器
streamlit run web_editor.py --server.port 8503

# 启动API服务
uvicorn api_endpoints:router --reload --port 8001
```

### 生产环境
```bash
# 使用Gunicorn启动API
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api_endpoints:router

# 使用Nginx代理Streamlit
nginx -c nginx.conf
```

### Docker部署
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY editor/ .
EXPOSE 8503 8001

CMD ["streamlit", "run", "web_editor.py", "--server.port", "8503"]
```

## 性能优化

### 建议配置
- 使用Redis缓存会话数据
- 启用WebSocket压缩
- 配置数据库连接池
- 实施内容分页加载
- 启用静态资源缓存

### 监控指标
- 活跃编辑会话数
- 文档编辑频率
- 评论解决率
- 版本创建频率
- WebSocket连接数

## 安全考虑

### 访问控制
- 用户身份验证
- 基于角色的权限
- 文档访问权限
- 操作审计日志

### 数据保护
- 编辑内容加密
- 版本数据备份
- 会话数据清理
- 敏感信息脱敏

## 扩展功能

### 计划功能
- 离线编辑支持
- 移动端适配
- 语音识别集成
- AI辅助翻译
- 高级搜索功能
- 批量导入导出

### 集成接口
- 翻译记忆库集成
- 术语管理系统
- 质量评估工具
- 项目管理系统
- 通知服务集成

## 故障排除

### 常见问题

1. **编辑会话连接失败**
   - 检查WebSocket连接
   - 验证用户权限
   - 确认文档状态

2. **条目锁定冲突**
   - 刷新页面重试
   - 检查其他用户状态
   - 联系管理员解锁

3. **版本创建失败**
   - 确认编辑权限
   - 检查文档状态
   - 验证版本描述

4. **评论无法添加**
   - 检查审核权限
   - 确认条目存在
   - 验证评论内容

### 日志查看
```bash
# 查看编辑器日志
tail -f editor.log

# 查看WebSocket连接日志
grep "WebSocket" editor.log

# 查看错误日志
grep "ERROR" editor.log
```

## 更新日志

### v1.0.0 (当前版本)
- 初始版本发布
- 完整的在线编辑功能
- 审核工作流支持
- 协作编辑实现
- 版本控制系统
- WebSocket实时通信
- 完整的测试覆盖

## 许可证

本软件遵循项目主许可证条款。

## 技术支持

如果遇到问题或需要技术支持，请：
1. 查看本文档的故障排除部分
2. 运行测试脚本验证功能
3. 检查日志文件获取详细信息
4. 联系技术支持团队