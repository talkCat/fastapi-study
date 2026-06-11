# Elasticsearch 混合检索学习计划

这个目录用于学习密云项目里的 Elasticsearch 文档召回与混合检索。

学习重点不是“背 API”，而是理解：

- 为什么 BM25 需要分词器
- 为什么向量检索能补充关键词检索
- 为什么混合检索要做 RRF 融合和 reranker 重排
- 密云项目里 `local_search -> retriever -> MyElasticsearchStore -> CRUDMixin` 的调用链
- 如何用真实 ES 和 embedding 配置做只读验证
- 如何在不直接安装密云项目 LangChain 版本的情况下轻量还原核心检索流程

## 学习顺序

### 001 Hybrid Retrieval

文件：

- `001-hybrid-retrieval.ipynb`

目标：

1. 从密云项目读取真实 ES 与 embedding 默认连接配置
2. 理解 ES index、document、inverted index、analyzer、score 的关系
3. 跑通 `ik_smart` 分词检查
4. 跑通 BM25 检索，观察 `_score`、`highlight` 和命中文档
5. 跑通语义检索，观察向量召回和 BM25 的差异
6. 跑通混合检索：BM25 + 语义检索 + RRF + reranker
7. 对照密云项目源码定位每一步实现在哪个文件

## 真实环境约定

教学默认读取密云项目：

```bash
export MIYUN_PROJECT=/home/dev/bxc/miyun_pro/miyun_pro
```

连接信息优先级：

1. 当前 shell 环境变量，例如 `es_addresses`
2. 密云项目源码里的默认值，例如 `llmos/config.py`
3. notebook 中展示的保底默认值

当前密云项目默认值：

- ES：`http://192.168.102.19:9200`
- embedding/reranker OpenAI-compatible base URL：`http://192.168.102.19:8082/v1`
- ES analyzer：`ik_smart`

教学目录已预置当前 ES 认证：

- `es_user=elastic`
- `es_password=elastic@2024`

如果后续认证变更，可以在运行 notebook 前用环境变量覆盖：

```bash
export es_user=你的ES用户名
export es_password=你的ES密码
```

notebook 会用这组认证直接连接 ES，不再导入密云项目的 `MyElasticsearchStore`。

## 运行方式

推荐在 `fastapi-study` 环境中打开 notebook。

当前轻量还原版只依赖：

- `elasticsearch`，已补充到 `/home/dev/bxc/fastapi-study/requirements.txt`
- `openai`，`fastapi-study` 已有

notebook 会先做连接检查。ES 或模型服务不可达时，仍然可以阅读流程和源码对照，但真实检索单元会报出明确错误。

## 学习原则

1. 先理解“文档为什么能被搜到”，再看 RAG。
2. 先单独看 BM25 和语义检索，再看混合检索。
3. 每一步都要观察输入、输出和排序依据。
4. 不把 score 理解成答案正确率，它只是召回阶段的相关性分数。
5. 混合检索的价值是互补：BM25 抓精确词，语义检索抓相近表达，reranker 做最后排序。

## 密云项目源码索引

- 文档问答入口：`llmos/miyun/intelligent_qa/local_search.py`
- retriever 创建：`llmos/miyun/intelligent_qa/local_search.py`
- ES store：`llmos/common/vectorstores/vectorstores.py`
- BM25、语义、混合检索：`llmos/common/vectorstores/utils.py`
- ES 默认配置：`llmos/config.py`
- embedding 默认配置：`llmos/base/config_base.py`
