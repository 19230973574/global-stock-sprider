# 全球股票爬虫

专业的多市场股票数据爬虫系统，支持美股、A股、港股等市场的数据获取。

## ✨ 功能特性

| 功能 | 状态 | 说明 |
|------|------|------|
| 📦 股票列表 | ✅ | 支持多市场股票列表获取 |
| 📋 标的基础信息 | ✅ | LongPort static_info，批量拉取名称/股本/财务指标 |
| ⚡ 实时行情 | ✅ | 支持实时行情更新 |
| 🕯️ K线历史 | ✅ | 支持多种周期的K线数据（默认 120 日） |
| 🔍 K线补数 | ✅ | 检测最新日缺失/滞后，仅对缺口标的增量拉取 |
| 💾 数据存储 | ✅ | Redis(实时数据) + MongoDB(历史数据) |
| 🏗️ 多市场架构 | ✅ | 清晰的架构设计，支持扩展 |

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行爬虫

```bash
# 启动实时行情（持续运行）
python3 main.py

# 运行单个任务
python3 main.py stock_list  # 获取股票列表
python3 main.py static_info # 获取标的基础信息（需先有股票列表）
python3 main.py realtime   # 获取实时行情（单次）
python3 main.py kline      # 获取K线数据（全量 120 日）
python3 main.py kline_gap  # 检测并补全缺失/滞后的 K 线
python3 main.py kline_gap check  # 仅扫描缺口，不拉取
```

## 📁 项目结构

```
global-stock-sprider/
├── main.py                 # 主入口
├── scheduler.py            # 任务调度器
├── config.py               # 配置管理
├── requirements.txt        # 依赖
├── config.json            # 配置文件
├── README.md              # 本文档
│
├── models/                # 数据模型
│   ├── stock.py           # 股票信息
│   ├── quote.py           # 实时行情
│   └── kline.py           # K线数据
│
├── storage/               # 存储层
│   ├── redis_manager.py   # Redis 管理
│   └── mongodb_manager.py # MongoDB 管理
│
├── datasources/           # 数据源
│   └── longport_client.py # 长桥 API 客户端
│
└── tasks/                # 任务层
    ├── base_task.py       # 任务基类
    ├── stock_list_task.py # 股票列表任务
    ├── static_info_task.py # 标的基础信息任务
    ├── realtime_quote_task.py # 实时行情任务
    └── kline_history_task.py  # K线历史任务
```

## 🗂️ 文件命名规范

| 类别 | 命名规范 | 示例 |
|------|----------|------|
| **模型** | 名词单数 | `stock.py`, `quote.py`, `kline.py` |
| **管理器** | `*_manager` | `redis_manager.py`, `mongodb_manager.py` |
| **客户端** | `*_client` | `longport_client.py` |
| **任务** | `*_task` | `stock_list_task.py`, `realtime_quote_task.py` |
| **公共模块** | 功能描述 | `config.py`, `scheduler.py` |

## 📊 数据存储

### Redis (热点数据)

```
market:stock:list:US            # 美股股票列表
market:quote:latest:AAPL        # AAPL 实时行情
```

### MongoDB (历史数据)

所有MongoDB集合都带有市场前缀：

| 集合名称 | 说明 |
|---------|------|
| us_stock_info | 美股股票基本信息 |
| us_kline_today | 美股当日K线数据 |
| us_kline_history | 美股历史K线数据 |
| a_stock_info | A股股票基本信息 |
| a_kline_today | A股当日K线数据 |
| a_kline_history | A股历史K线数据 |
| hk_stock_info | 港股股票基本信息 |
| hk_kline_today | 港股当日K线数据 |
| hk_kline_history | 港股历史K线数据 |

## 🏗️ 架构设计

### 数据流向

```
DataSource (LongPortClient)
    ↓
Task (RealtimeQuoteTask)
    ↓
Storage (RedisManager/MongoDBManager)
```

### 支持的市场

| 市场 | 代码 | 状态 |
|------|------|------|
| 美股 | US | ✅ |
| A股 | A | 🔜 |
| 港股 | HK | 🔜 |

## 📚 扩展指南

### 添加新市场

1. 在 `models/` 中确保市场字段支持
2. 在 `datasources/` 中添加新的数据客户端
3. 在 `tasks/` 中添加对应任务

### 添加新数据源

1. 创建 `datasources/*_client.py`
2. 实现对应的 API 方法
3. 在 `config.py` 中添加配置

---

**Happy Crawling! 🚀**
