# RAG 知识转化与知识召回问答知识库设计

## 1. 目标

在 `notebooks/rag` 下设计一套教学型问答知识库，覆盖从 PDF 到可问答知识库的完整链路：

```text
PDF 文件
-> 对象存储
-> PDF 解析
-> 文本清洗
-> 文本切片
-> 可选摘要
-> 三元组抽取
-> ES 向量与关键词索引
-> Neo4j 图谱入库
-> 多路召回 + 图检索
-> 证据融合
-> 问答生成
```

这套设计的重点不是一次性做成生产平台，而是用一组可运行、可观察、可逐步扩展的 notebook，把知识库系统拆成清晰的教学阶段。

## 2. 设计边界

第一版支持：

- 文本型 PDF 解析。
- MinIO 保存原始 PDF 和中间产物。
- Elasticsearch 保存 chunk、摘要、embedding，并支持 BM25 与向量检索。
- Neo4j 保存文档、chunk、实体、关系和证据。
- 向量模型使用 `Conan-embedding-v1`。
- 三元组抽取使用 OpenAI-compatible 大模型网关：
  - base URL: `http://192.168.102.19:8082/v1`
  - model: `qwen2.5-0.5b-instruct`
- reranker 使用同一网关：
  - model: `bge-reranker-base`
- 问答阶段支持：
  - BM25 召回
  - 向量召回
  - 图谱召回
  - RRF 融合
  - 证据型回答

第一版暂不支持：

- OCR 扫描版 PDF。
- 复杂表格结构还原。
- 图片、图表语义解析。
- 多租户权限隔离。
- 增量更新任务队列。
- 生产级实体消歧。
- 图谱自动纠错。
- 大规模异步任务调度。

这些能力可以作为后续高级课时。

## 2.1 教学样例文档

后续 notebook 统一使用下面这份 PDF 作为样例文档：

```text
raw/北京市密云水库防御洪水方案.pdf
```

该文件用于贯穿完整教学链路：

```text
PDF 路径检查
-> 上传 MinIO
-> PyMuPDF 解析 pages
-> 文本清洗和 chunk 切片
-> embedding 入 ES
-> qwen2.5-0.5b-instruct 抽取三元组
-> Neo4j 入图
-> BM25 + 向量 + 图检索问答
```

## 2.2 本地教学环境配置

后续 notebook 不应把账号密码硬编码在代码里，而是统一从环境变量读取。

建议 `.env` 配置项：

```env
# OpenAI-compatible 大模型网关
RAG_MODEL_BASE_URL=http://192.168.102.19:8082/v1
RAG_CHAT_MODEL=qwen2.5-0.5b-instruct
RAG_EMBEDDING_MODEL=Conan-embedding-v1
RAG_RERANKER_MODEL=bge-reranker-base

# Elasticsearch
RAG_ES_ADDRESSES=http://10.20.20.45:9200
RAG_ES_USER=elastic
RAG_ES_PASSWORD=elastic@2024

# MinIO
RAG_MINIO_ENDPOINT=192.168.102.19:9001
RAG_MINIO_ACCESS_KEY=minioadmin
RAG_MINIO_SECRET_KEY=minioadmin
RAG_MINIO_SECURE=false
RAG_MINIO_BUCKET=rag-documents

# Neo4j
RAG_NEO4J_URI=bolt://192.168.102.19:7687
RAG_NEO4J_BROWSER=http://192.168.102.19:7474/
RAG_NEO4J_USER=neo4j
RAG_NEO4J_PASSWORD=neo4j@2025
```

Neo4j 浏览器地址是 `http://192.168.102.19:7474/`，但 Python driver 通常使用 Bolt 协议连接，因此 notebook 默认使用：

```text
bolt://192.168.102.19:7687
```

如果服务端没有开放 Bolt 端口，需要先在 Neo4j 配置中确认 `7687` 是否可访问。

## 3. 总体架构

```text
                   +-------------------+
                   |      PDF File      |
                   +---------+---------+
                             |
                             v
                   +-------------------+
                   |       MinIO       |
                   | raw / parsed JSON |
                   +---------+---------+
                             |
                             v
                   +-------------------+
                   |    PDF Parser     |
                   |  PyMuPDF / pages  |
                   +---------+---------+
                             |
                             v
                   +-------------------+
                   | Cleaner + Chunker |
                   +----+---------+----+
                        |         |
                        |         v
                        |  +----------------+
                        |  | Summary Model  |
                        |  | optional       |
                        |  +----------------+
                        |
          +-------------+--------------+
          |                            |
          v                            v
+-------------------+        +---------------------+
| Elasticsearch     |        | Triple Extractor    |
| BM25 + vectors    |        | qwen2.5-0.5b        |
+---------+---------+        +----------+----------+
          |                             |
          |                             v
          |                  +---------------------+
          |                  | Neo4j               |
          |                  | entities + triples  |
          |                  +----------+----------+
          |                             |
          +-------------+---------------+
                        |
                        v
              +----------------------+
              | Retrieval Orchestrator|
              | BM25 + vector + graph |
              +----------+-----------+
                         |
                         v
              +----------------------+
              | Evidence QA Answer   |
              +----------------------+
```

## 4. 中间件职责

### 4.1 MinIO

MinIO 只负责对象存储，不负责检索和推理。

建议 bucket：

```text
rag-documents
```

建议对象路径：

```text
raw/{doc_id}.pdf
parsed/{doc_id}/pages.json
chunks/{doc_id}/chunks.json
summaries/{doc_id}/summaries.json
triples/{doc_id}/triples.json
```

这样设计的原因：

- 原始 PDF 可以长期保留。
- 解析结果可以复用。
- ES 或 Neo4j 索引损坏时，可以从 MinIO 中间产物重建。
- notebook 每一步都有可观察产物。

### 4.2 Elasticsearch

ES 负责两类召回：

- 关键词召回：BM25 / `match` 查询。
- 语义召回：`dense_vector` + kNN 查询。

建议索引：

```text
rag_chunks
```

建议文档结构：

```json
{
  "doc_id": "doc_001",
  "chunk_id": "doc_001_chunk_0001",
  "file_name": "demo.pdf",
  "page_start": 1,
  "page_end": 2,
  "text": "原始 chunk 文本",
  "summary": "可选 chunk 摘要",
  "vector": [0.01, 0.02],
  "metadata": {
    "source_object": "raw/doc_001.pdf"
  }
}
```

`vector` 字段维度以 `Conan-embedding-v1` 的实际返回维度为准，不在设计文档里硬编码。

### 4.3 Neo4j

Neo4j 负责表达跨文档、跨 chunk 的逻辑关系。

建议节点：

```text
(:Document {doc_id, file_name, source_object})
(:Chunk {chunk_id, doc_id, page_start, page_end, text, summary})
(:Entity {name, type})
```

建议关系：

```text
(:Document)-[:HAS_CHUNK]->(:Chunk)
(:Chunk)-[:MENTIONS]->(:Entity)
(:Entity)-[:RELATION {
  type,
  evidence_chunk_id,
  evidence,
  confidence,
  doc_id
}]->(:Entity)
```

关系必须保留证据，不能只保留结论。

错误示例：

```text
密云水库 -> 发布 -> 泄洪通知
```

推荐示例：

```text
(:Entity {name: "密云水库管理处"})
  -[:RELATION {
    type: "发布",
    evidence: "密云水库管理处发布泄洪通知",
    evidence_chunk_id: "doc_001_chunk_0003",
    confidence: 0.95
  }]->
(:Entity {name: "泄洪通知"})
```

## 5. 数据模型

### 5.1 Page

```json
{
  "doc_id": "doc_001",
  "file_name": "demo.pdf",
  "page_no": 1,
  "text": "页面文本"
}
```

### 5.2 Chunk

```json
{
  "doc_id": "doc_001",
  "chunk_id": "doc_001_chunk_0001",
  "page_start": 1,
  "page_end": 2,
  "text": "chunk 原文",
  "summary": "可选摘要",
  "metadata": {
    "file_name": "demo.pdf",
    "source_object": "raw/doc_001.pdf"
  }
}
```

### 5.3 Triple

```json
{
  "subject": "密云水库管理处",
  "predicate": "发布",
  "object": "泄洪通知",
  "subject_type": "组织机构",
  "object_type": "文件",
  "evidence": "密云水库管理处发布泄洪通知",
  "confidence": 0.95,
  "doc_id": "doc_001",
  "chunk_id": "doc_001_chunk_0003"
}
```

## 6. PDF 解析与切片

第一版使用 PyMuPDF 解析文本型 PDF。

解析策略：

```text
PDF -> pages
page.get_text("text", sort=True)
```

清洗策略：

- 合并多余空白。
- 去除连续空行。
- 保留页码。
- 不做复杂版面重建。

切片策略：

```text
chunk_size: 500-800 中文字符
overlap: 80-120 中文字符
```

切片结果必须保留来源页码：

```text
chunk_id
doc_id
page_start
page_end
text
```

## 7. 摘要设计

摘要在第一版中是可选增强能力，不是核心依赖。

摘要阶段放在切片之后：

```text
PDF 解析
-> 文本清洗
-> Chunk 切片
-> Chunk 摘要
-> Embedding / Triple Extraction
```

摘要用途：

- 快速预览 chunk 内容。
- 后续做文档级、章节级、项目级摘要检索。
- 多文档问答时压缩上下文。
- Neo4j 节点上挂简短说明。

第一版建议：

```text
embedding 使用原始 chunk text
三元组抽取使用原始 chunk text
summary 只作为辅助字段存储
```

不要用摘要替代原文证据。

## 8. 三元组抽取设计

### 8.1 模型选择

第一版使用已部署的本地小模型：

```text
qwen2.5-0.5b-instruct
http://192.168.102.19:8082/v1/chat/completions
```

选择原因：

- 已在本机可访问。
- OpenAI-compatible 接口调用简单。
- 适合教学阶段观察 prompt、JSON 输出和校验流程。
- Qwen2.5 系列提供 0.5B 到 72B 的模型，后续可以平滑升级到 1.5B、3B 或更大模型。

约束：

- 0.5B 模型能力有限。
- 必须使用严格 prompt、few-shot 示例和 JSON 校验。
- 不应直接相信模型输出。

### 8.2 抽取 Prompt 目标

要求模型输出固定 JSON：

```json
{
  "triples": [
    {
      "subject": "",
      "predicate": "",
      "object": "",
      "evidence": "",
      "confidence": 0.0
    }
  ]
}
```

规则：

- `subject`、`predicate`、`object` 必须来自原文，或由原文中的指代直接消解得到。
- `evidence` 必须是原文中的短句。
- 没有三元组时输出 `{"triples": []}`。
- 每条三元组必须带 `chunk_id` 和 `doc_id` 后再入库。

### 8.3 校验策略

入库前必须校验：

- JSON 可解析。
- `subject` 非空。
- `predicate` 非空。
- `object` 非空。
- `evidence` 非空。
- `confidence` 可转为数字。
- `confidence >= 0.5` 才进入图谱。
- `evidence` 最好能在当前 chunk 中找到。

## 9. 入库设计

### 9.1 ES 入库

每个 chunk 一条 ES 文档。

写入字段：

```text
doc_id
chunk_id
file_name
page_start
page_end
text
summary
vector
metadata
```

查询方式：

- BM25：`match` 查询 `text`。
- 向量：使用 `Conan-embedding-v1` 生成 query vector，然后执行 kNN。

### 9.2 Neo4j 入库

建议唯一约束：

```cypher
CREATE CONSTRAINT document_id IF NOT EXISTS
FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;

CREATE CONSTRAINT chunk_id IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;

CREATE CONSTRAINT entity_name IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE;
```

写入策略：

```text
MERGE Document
MERGE Chunk
MERGE Entity(subject)
MERGE Entity(object)
MERGE Document-HAS_CHUNK-Chunk
MERGE Chunk-MENTIONS-Entity
MERGE Entity-RELATION-Entity
```

## 10. 召回设计

### 10.1 多路召回

用户问题进入后，先执行三路召回：

```text
1. BM25 召回
2. 向量召回
3. 图谱召回
```

BM25 适合：

- 精确词。
- 文件名、机构名、项目名。
- 法规条款、编号。

向量召回适合：

- 语义相近表达。
- 用户描述和文档表述不完全一致的情况。

图谱召回适合：

- 跨文档关系。
- 主体关联。
- 事件链路。
- 谁发布、谁负责、谁影响谁。

### 10.2 图谱召回

图谱召回建议先做简单版：

```text
问题 -> 抽取查询实体
查询 Neo4j 中同名实体
查一跳关系
查相关 chunk evidence
```

示例 Cypher：

```cypher
MATCH (e:Entity {name: $entity_name})-[r:RELATION]-(other:Entity)
RETURN e, r, other
LIMIT 20
```

后续扩展：

```text
两跳路径
按关系类型过滤
按 confidence 过滤
按 doc_id / 时间过滤
```

### 10.3 融合策略

文本召回结果使用 RRF 融合：

```text
BM25 docs + vector docs -> RRF fused docs
```

图谱结果不直接混入 RRF 排名，而是作为结构化证据补充：

```text
fused_docs
+ graph_evidence
-> evidence package
```

原因：

- BM25 / vector 结果是 chunk 排名。
- 图谱结果是关系和路径。
- 两者分数体系不同，不应强行混成一个分数。

## 11. 问答生成设计

回答生成时，模型不直接看全量文档，而是看证据包。

证据包结构：

```json
{
  "question": "用户问题",
  "text_evidence": [
    {
      "chunk_id": "doc_001_chunk_0003",
      "page_start": 3,
      "text": "..."
    }
  ],
  "graph_evidence": [
    {
      "subject": "密云水库管理处",
      "predicate": "发布",
      "object": "泄洪通知",
      "evidence": "密云水库管理处发布泄洪通知",
      "chunk_id": "doc_001_chunk_0003"
    }
  ]
}
```

回答约束：

- 只能基于证据回答。
- 结论后附来源。
- 证据不足时明确说明。
- 不允许编造没有证据的关系。

## 12. 教学 Notebook 规划

### 001-rag-architecture-overview.ipynb

目标：

- 解释普通 RAG、Hybrid RAG、GraphRAG 的区别。
- 解释为什么多路召回不能解决所有跨文档逻辑问题。
- 介绍本课程的总链路。

输出：

- 架构图。
- 数据流说明。

### 002-pdf-to-minio-and-parse.ipynb

目标：

- 上传 PDF 到 MinIO。
- 从 MinIO 下载验证。
- 使用 PyMuPDF 解析文本。
- 生成 pages JSON。

输出：

- `pages` 列表。
- `parsed/{doc_id}/pages.json`。

### 003-clean-and-chunk-pdf-text.ipynb

目标：

- 清洗 PDF 文本。
- 按字符长度和 overlap 切片。
- 保留页码和来源。

输出：

- `chunks` 列表。
- `chunks/{doc_id}/chunks.json`。

### 004-summary-and-embedding-to-es.ipynb

目标：

- 可选生成 chunk 摘要。
- 使用 `Conan-embedding-v1` 生成向量。
- 创建 ES index mapping。
- 写入 chunk 文档。
- 验证 BM25 和 kNN 查询。

输出：

- ES `rag_chunks` 索引。
- BM25 查询样例。
- 向量查询样例。

### 005-triple-extraction-with-qwen.ipynb

目标：

- 使用 `qwen2.5-0.5b-instruct` 抽取三元组。
- 学习 few-shot prompt。
- 学习 JSON 解析和字段校验。

输出：

- `triples` 列表。
- `triples/{doc_id}/triples.json`。

### 006-write-graph-to-neo4j.ipynb

目标：

- 创建 Neo4j 约束。
- 写入 Document、Chunk、Entity、Relation。
- 查询一跳关系。

输出：

- Neo4j 图谱数据。
- 基础 Cypher 查询样例。

### 007-hybrid-retrieval-plus-graph.ipynb

目标：

- BM25 召回。
- 向量召回。
- RRF 融合。
- 查询实体识别。
- Neo4j 图检索。
- 合并文本证据和图证据。

输出：

- `text_evidence`
- `graph_evidence`
- `evidence_package`

### 008-qa-with-evidence-and-validation.ipynb

目标：

- 基于证据生成回答。
- 输出引用 chunk_id / 页码。
- 检查回答是否有证据支持。

输出：

- 带引用的问答结果。
- 简单验证函数。

## 13. 推荐依赖

第一版可能需要新增：

```text
minio
pymupdf
neo4j
```

当前已有：

```text
httpx
openai
elasticsearch
python-dotenv
```

如果后续改成本地直接加载 Qwen 模型，而不是调用 `http://192.168.102.19:8082/v1` 网关，则还需要：

```text
transformers
torch
accelerate
```

第一版已经有本地模型服务，因此不建议 notebook 里直接加载模型，先通过 HTTP 调用即可。

## 14. 错误处理与验证

每个阶段都要有可验证输出：

```text
MinIO: 文件是否上传成功，是否可下载
PDF: 每页是否抽取到文本
Chunk: chunk 数量、最大长度、页码范围
Embedding: 向量维度是否一致
ES: 文档数量、BM25 查询、kNN 查询
Triple: JSON 是否可解析，字段是否完整
Neo4j: 节点数量、关系数量、一跳查询
Retrieval: 三路召回是否都有结果
QA: 回答是否引用证据
```

关键原则：

- 不让模型输出直接入库。
- 不让摘要替代原文证据。
- 不让图谱关系脱离 evidence。
- 不让问答结果脱离证据包。

## 15. 后续扩展方向

第一版完成后，可以继续扩展：

- OCR 支持。
- 表格抽取。
- 实体归一化。
- 同义词词典。
- 关系类型白名单。
- 图谱路径推理。
- reranker 精排。
- 权限过滤。
- 增量索引。
- FastAPI 接口化。
- 后台任务队列。

## 16. 参考资料

- MinIO Python SDK: https://docs.min.io/aistor/developers/sdk/python/api/
- PyMuPDF 文本抽取: https://pymupdf.readthedocs.io/en/latest/recipes-text.html
- PyMuPDF 基础 PDF 抽取: https://pymupdf.readthedocs.io/en/latest/the-basics.html
- Elasticsearch kNN Search: https://www.elastic.co/docs/solutions/search/vector/knn
- Elasticsearch dense_vector: https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/dense-vector
- Neo4j Vector Indexes: https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/
- Neo4j Vector Search Guide: https://neo4j.com/developer/genai-ecosystem/vector-search/
- Qwen2.5-0.5B-Instruct: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct
- Qwen2.5-1.5B-Instruct: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct
