# RAG 知识库学习线

这个目录用于学习一套从 PDF 到问答知识库的完整 RAG / GraphRAG 流程。

配套设计文档：

- `rag_knowledge_base_design.md`

## 样例文档

后续课程统一使用这份 PDF 作为教学样例：

```text
raw/北京市密云水库防御洪水方案.pdf
```

第一课只检查文件路径和整体架构；第二课开始围绕这份 PDF 做 MinIO 上传和 PyMuPDF 文本解析。

## 学习目标

学完这一组 notebook 后，应该能理解并跑通：

1. PDF 文件如何进入对象存储。
2. PDF 文本如何解析、清洗和切片。
3. Chunk 如何生成 embedding 并写入 ES。
4. 小模型如何抽取实体和三元组。
5. 三元组如何写入 Neo4j。
6. 问答时如何结合 BM25、向量召回和图检索。
7. 如何基于证据包生成可追溯回答。

## 课时规划

- `001-rag-architecture-overview.ipynb`：整体架构、知识转化与知识召回、ES/Neo4j/MinIO 职责边界。
- `002-pdf-to-minio-and-parse.ipynb`：PDF 上传 MinIO，并解析 pages。
- `003-clean-and-chunk-pdf-text.ipynb`：清洗文本并切片。
- `004-summary-and-embedding-to-es.ipynb`：摘要、embedding、写入 ES。
- `005-triple-extraction-with-qwen.ipynb`：使用 `qwen2.5-0.5b-instruct` 抽取三元组。
- `006-write-graph-to-neo4j.ipynb`：把实体关系写入 Neo4j。
- `007-hybrid-retrieval-plus-graph.ipynb`：BM25 + 向量 + 图检索。
- `008-qa-with-evidence-and-validation.ipynb`：基于证据回答并做验证。
- `009-groundedness-check.ipynb`：检查回答里的 claim 是否真的被证据支持。

当前已完成：

- `001-rag-architecture-overview.ipynb`
- `002-pdf-to-minio-and-parse.ipynb`
- `003-clean-and-chunk-pdf-text.ipynb`
- `004-summary-and-embedding-to-es.ipynb`
- `005-triple-extraction-with-qwen.ipynb`
- `006-write-graph-to-neo4j.ipynb`
- `007-hybrid-retrieval-plus-graph.ipynb`
- `008-qa-with-evidence-and-validation.ipynb`
- `009-groundedness-check.ipynb`

## 当前环境

第一版使用这些服务：

- 大模型网关：`http://192.168.102.19:8082/v1`
- embedding：`Conan-embedding-v1`
- reranker：`bge-reranker-base`
- 三元组抽取：`qwen2.5-0.5b-instruct`
- ES：`http://10.20.20.45:9200`
- MinIO：`192.168.102.19:9001`
- Neo4j Browser：`http://192.168.102.19:7474/`

账号密码不要硬编码在 notebook 中，后续课程统一从 `.env` 读取。
