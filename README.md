<div align="center">

# Intelligent Fault QA System Based on Qwen 3.5

面向故障知识文档的可追溯智能问答系统

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-WebUI-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![RAG](https://img.shields.io/badge/RAG-Qwen3.5--4B-7C3AED?style=flat-square)
![FAISS](https://img.shields.io/badge/Vector%20Search-FAISS-0F172A?style=flat-square)

`文档上传` · `知识库构建` · `语义检索` · `流式问答` · `引用溯源`

</div>

---

## ✨ Overview

本项目是一个面向设备维修、实验教学、工程调试和运维支持场景的故障知识问答系统。它不是开放域聊天机器人，而是围绕用户上传的本地故障资料进行检索增强问答，并通过引用标记回查原始文档片段。

系统以用户上传的故障文档为知识来源，完成从文档解析、chunk 切分、向量化、FAISS 检索到 Qwen3.5-4B 回答生成的完整链路。回答中的 `[r数字]` 引用标记可以通过 `chunk_uid` 定位到原文片段，从而让模型回答具备可核查的资料依据。

```text
Upload Documents
      |
      v
Parse / Clean / Chunk
      |
      v
Qwen3-embedding-4B -> FAISS Index
      |
      v
Top-K Retrieval -> Qwen3.5-4B
      |
      v
Streaming Answer + Citation Traceability
```

## ✅ 任务清单

下面记录的是项目已经完成和后续准备完善的关键功能点，方便快速了解当前完成度。

### 🎉 已完成

- ✅ 实现文件解析进度展示
- ✅ 实现点击引用后界面前后淡化的过渡效果
- ✅ 解决 LLM 首次对话响应过慢的问题
- ✅ 解决对话结束后首次点击引用时 WebSocket 未连接的问题
- ✅ 修复上传文件界面 UI 光效错位
- ✅ 修复点击上传文件后队列内文件依然残留的问题
- ✅ 实现文件删除功能
- ✅ 解决重复文件上传问题
- ✅ 关闭 RAG 时自动切换提示词模板
- ✅ 修复多文件上传时单个不支持格式导致全部文件卡住的问题
- ✅ 修复“介绍一下自己”时模型介绍自己的问题
- ✅ 修复标题过长时删除按钮竖排显示的问题
- ✅ 支持手动编辑对话标题
- ✅ 修复多轮上下文返回逻辑
- ✅ 完善小程序端文件引用显示能力
- ✅ 优化后端思考模式输出长度
- ✅ 小程序端引用对话框增加淡入淡出效果
- ✅ 小程序端支持思考模式输出文本单独折叠
- ✅ 修复点击引用后界面出现上下重复文本的问题

### 🚧 待完善

- 🔧 优化 GUI 上传文件列表，在文件数量较多时自动出现滚动区域
- 📝 增加前端 Markdown 渲染能力，优化代码块、列表和结构化回答展示

## 🚀 Features

| 能力 | 说明 |
| --- | --- |
| 多格式文档接入 | 支持 `txt`、`md`、`pdf`、`docx`、`csv`、`xlsx`、`xls`、`html`、`htm`、`pptx`、`ppt` 等文本型电子文档 |
| 动态知识库构建 | 上传后自动完成解析、清洗、切分、向量化和索引构建，无需重新训练大模型 |
| 语义检索增强 | 使用 Qwen3-embedding-4B 将问题和文档片段映射到同一语义向量空间 |
| FAISS 向量检索 | 通过 Top-K 检索召回相关证据片段，缓解关键词不一致导致的漏检 |
| Qwen3.5-4B 问答 | 将检索片段作为上下文输入模型，使回答尽量围绕用户资料展开 |
| WebSocket 流式输出 | 支持回答增量返回、停止生成、心跳检测和引用详情查询 |
| 引用溯源 | 基于 `chunk_uid` 将回答中的引用标记定位到原始文档片段 |
| 文件管理 | 支持上传、状态查询、文件列表、重新预处理和删除文件 |

## 🧩 Architecture

| 模块 | 技术与职责 |
| --- | --- |
| Web 前端 | Vue + Vite，负责文档上传、状态展示、参数配置、流式问答和引用详情展示 |
| 后端服务 | FastAPI，提供 HTTP 文件管理接口和 WebSocket 问答通道 |
| RAG 核心 | 文档解析、chunk 切分、Embedding 编码、FAISS 检索、上下文构造、模型生成 |
| 数据层 | 保存原始文档、chunk 文件、FAISS 索引和 manifest 映射文件 |
| 模型层 | Qwen3.5-4B 负责回答生成，Qwen3-embedding-4B 负责语义向量化 |

## ⚡ Quick Start

### 1. 安装后端依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 中包含后端运行所需的核心依赖，例如 `torch`、`transformers`、`faiss-cpu`、`pymupdf`、`python-docx`、`pandas`、`openpyxl`、`beautifulsoup4` 和 `python-pptx`。

### 2. 放置模型文件

后端默认从以下目录加载模型：

```text
backend/Qwen3.5-4B
backend/Qwen3-embedding-4B
```

对应配置位于 `backend/src/config.py`：

```python
LLM_MODEL_PATH = os.path.join(BASE_DIR, "Qwen3.5-4B")
EMBED_MODEL_PATH = os.path.join(BASE_DIR, "Qwen3-embedding-4B")
```

### 3. 启动后端服务

```bash
python backend/midway/run.py
```

默认后端地址：

```text
http://127.0.0.1:11451
```

### 4. 启动 Web 前端

```bash
cd GUI/WebUI
npm install
npm run dev
```

浏览器打开 Vite 输出的本地地址后，即可上传文档并开始问答。

## 🖥️ Usage

1. 在 Web 页面上传故障文档。
2. 等待文件完成预处理和索引构建。
3. 选择需要参与问答的文档。
4. 输入故障问题，系统通过 WebSocket 流式返回回答。
5. 点击回答中的 `[r数字]` 引用标记，查看对应原文片段。

## 🔌 API

| 类型 | 地址 | 说明 |
| --- | --- | --- |
| HTTP | `/api/upload` | 上传文档并启动后台预处理 |
| HTTP | `/api/files` | 查询已管理文件列表 |
| HTTP | `/api/file/{file_id}/status` | 查询文件处理状态 |
| HTTP | `/api/file/{file_id}/retry-preprocess` | 重新提交文档预处理 |
| HTTP | `/api/file/{file_id}` | 删除文件及其索引信息 |
| WebSocket | `/ws/chat` | 流式问答、停止生成、心跳检测、引用详情查询 |

## 📦 Deployment

这里只说明网页端部署流程，不考虑小程序端。

### 后端端口配置

后端监听地址位于 `backend/midway/run.py`：

```python
uvicorn.run(
    app,
    host="127.0.0.1",
    port=11451,
)
```

如果需要局域网访问，可以将 `host` 改为 `0.0.0.0`。如果端口冲突，可以修改 `port`，例如改为 `8000`。

### 网页端接口地址配置

网页端默认后端地址位于 `GUI/WebUI/src/config/index.js`：

```javascript
http_base_url: 'http://127.0.0.1:11451'
```

如果后端部署在其他机器或端口，需要同步修改这里：

```javascript
http_base_url: 'http://192.168.1.10:8000'
```

WebSocket 地址会根据 `http_base_url` 和 `ws_path` 自动生成，默认路径为 `/ws/chat`。

## 📊 Metrics

以下指标来自论文中的系统测试与结果分析部分。

### 测试环境

| 环境 | 项目 | 配置 |
| --- | --- | --- |
| Linux 端 | 操作系统 | Linux |
| Linux 端 | CPU | 16 vCPU Intel(R) Xeon(R) Platinum 8352V CPU @ 2.10GHz |
| Linux 端 | GPU | NVIDIA GeForce RTX 4080 SUPER |
| Linux 端 | 内存 | 62GB |
| Linux 端 | 后端框架 | FastAPI / WebSocket 服务 |
| Linux 端 | 大语言模型 | Qwen3.5-4B |
| Linux 端 | Embedding 模型 | Qwen3-embedding-4B |
| Linux 端 | 向量检索库 | FAISS |
| Windows 端 | 操作系统 | Windows |
| Windows 端 | CPU | Intel(R) Core(TM) i7-10700K CPU @ 3.80GHz |
| Windows 端 | GPU | NVIDIA GeForce RTX 3060 |
| Windows 端 | 内存 | 32GB |
| Windows 端 | 前端运行环境 | Web 端、微信小程序端 |
| Windows 端 | 测试终端 | Web 端、微信小程序端 |

### 功能测试

| 测试项 | 测试内容 | 测试结果 |
| --- | --- | --- |
| 多格式上传测试 | 上传 txt、md、pdf、docx、csv、xlsx、xls、html、htm、pptx、ppt 文档 | 通过 |
| 文档处理测试 | 完成文本解析、清洗、chunk 切分和索引构建 | 通过 |
| 文件状态测试 | 显示文档处理中、处理完成等状态 | 通过 |
| Web 端问答测试 | 在 Web 端输入问题并接收流式回答 | 通过 |
| 微信小程序端测试 | 在小程序端完成故障问答 | 通过 |
| 引用查看测试 | 点击引用标记并查看原文片段 | 通过 |

### 引用溯源

| 测试内容 | 评价方式 | 测试结果 |
| --- | --- | --- |
| 引用标记显示 | 回答中是否包含引用标记 | 通过 |
| 引用点击响应 | 点击引用后是否发起详情查询 | 通过 |
| 原文片段返回 | 是否返回对应文档片段 | 通过 |
| 来源文件显示 | 是否显示引用片段来源文件 | 通过 |
| 引用定位成功率 | 成功打开引用次数 / 引用总次数 | 93.47% |

### 文档预处理性能

| 测试文档 | 格式 | 文件大小 | chunk 数量 | 预处理耗时 |
| --- | --- | --- | --- | --- |
| 申报指南 | pdf | 287.5 KB | 111 | 1.52 s |
| 手持式测试仪说明书 | docx | 4.60 MB | 51 | 1.17 s |
| 微机保护程序流程 | pptx | 1.02 MB | 31 | 1.43 s |
| 电气自动化课程大纲 | txt | 58.2 KB | 997 | 16.67 s |
| 采购表 | xlsx | 14.7 KB | 1 | 0.22 s |

### 问答性能

| 测试指标 | 测试方式 | 平均结果 |
| --- | --- | --- |
| 首响应时间 | 100 轮问答平均 | 0.54 s |
| 完整回答时间 | 100 轮问答平均 | 13.57 s |
| 引用查询时间 | 100 轮引用查询平均 | 0.072 s |

## 📁 Project Structure

```text
.
├── backend
│   ├── midway
│   │   ├── run.py              # FastAPI 入口
│   │   ├── http_upload.py      # HTTP 文件管理
│   │   └── webSocket_chat.py   # WebSocket 流式问答
│   └── src
│       ├── config.py           # 模型、文档、索引和生成参数配置
│       ├── Communication.py    # RAG 服务编排
│       ├── build_index.py      # 文档索引构建
│       ├── chat_with_doc.py    # 检索、上下文构造与引用解析
│       ├── embedding_model.py  # Embedding 模型封装
│       └── llm_model.py        # LLM 模型封装
├── GUI
│   └── WebUI                   # Vue + Vite 网页端
├── requirements.txt
└── README.md
```

## 💡 Notes

- 系统当前主要处理文本型电子文档；图片文件、扫描版 PDF 和需要 OCR 的资料不作为当前已实现能力。
- RAG 和引用溯源增强的是回答的可追溯性与可验证性，并不代表模型回答一定完全正确。
- 故障文档、索引和问答流程可在本地或内网环境闭环运行，有助于降低敏感资料外传风险。
