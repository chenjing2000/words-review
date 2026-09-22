# words_review

一个使用 PySide6 编写的轻量级 IELTS 背单词程序。

## 主要功能

- 启动时自动扫描默认 `wordlist/*.json`，也可以通过【文件夹】临时切换到其它 WordList 文件夹。
- 只扫描所选文件夹直属的 `*.json`；无法按 WordList 格式完整加载的 JSON 会被跳过。
- 每个 WordList 使用同名资源目录保存学习进度和发音资源。
- 学习状态：`UNLEARNED -> UNCERTAIN -> RECOGNIZED -> MASTERED`。
- 复习模式：全部单词、待学习、不懂、认识、熟悉。
- 分类复习采用本轮快照队列；切换复习模式时，以当前 Word 在原 WordList 中的位置为锚点，自动给出最近的建议起始序号。切换后需点击【复习】才会进入新模式。
- 第二行的“从第 [N] 个开始”可直接输入非负整数；N 表示当前复习模式筛选结果中的第几个，超出范围时自动限制到有效范围。
- 【释义】使用 HTML + QTextBrowser 显示词性、英文含义、中文含义、双语例句、同义词、搭配和 Notes。
- 音标右侧提供英音和美音按钮，从 `pronunciation.json` 中查找本地音频并播放。
- 点击【不懂】【认识】【理解】后立即保存进度并进入下一词。
- Progress 与 AppState 使用 `QSaveFile` 原子写入。外部 WordList 文件夹不会跨程序启动自动恢复。
- 窗口首次启动默认为当前可用屏幕宽度的 60%，默认比例 16:9；之后可自由缩放。
- 窗口 geometry 和字体大小使用 `QSettings` 保存。
- 状态栏默认隐藏；出现警告或错误时自动显示，数秒后自动隐藏。

## WordList 与资源目录

假设单词本为 `education.json`，其资源目录固定为同目录下的 `education/`：

```text
wordlist/
├── education.json
└── education/
    ├── progress.json
    ├── pronunciation.json
    └── audio/
        ├── pedagogy_uk.mp3
        ├── pedagogy_us.mp3
        └── ...
```

`progress.json` 由 Words Review 自动维护。`pronunciation.json` 和 `audio/` 由用户维护；缺少它们不会影响普通复习功能。

程序沿用音频提取工具生成的 `pronunciation.json` 格式：

```json
{
  "schema_version": 1,
  "words": {
    "pedagogy": {
      "uk": ["audio/pedagogy_uk.mp3"],
      "us": ["audio/pedagogy_us.mp3"]
    }
  }
}
```

当同一口音存在多个候选文件时，程序按顺序播放第一个实际存在的文件。

## 项目结构

```text
words_review/
├── main.py
├── pyproject.toml
├── .gitignore
├── resources/
│   ├── icons/
│   │   ├── app.svg
│   │   ├── app.ico
│   │   ├── speaker_uk.svg
│   │   ├── speaker_us.svg
│   │   └── chevron-down.svg
│   └── styles/
│       └── light.qss
├── wordlist/
│   └── example.json
├── data/
├── skills/
│   └── ielts-wordlist-generator/
│       └── SKILL.md
├── app/
│   ├── models/
│   ├── repositories/
│   ├── pronunciation.py
│   ├── review_session.py
│   └── main_window.py
└── tests/
```

## 安装与运行

推荐使用 `uv`：

```bash
uv sync
uv run python main.py
```

项目自带 `wordlist/example.json`，安装依赖后即可启动查看界面。

## 运行核心逻辑测试

```bash
uv run python -m unittest discover -s tests -v
```

核心复习、WordList 与 pronunciation 数据逻辑测试本身不依赖 PySide6，也可以直接运行：

```bash
python -m unittest discover -s tests -v
```

## 生成新的 WordList

`skills/ielts-wordlist-generator/SKILL.md` 描述了 ChatGPT 应如何生成符合程序格式的 IELTS WordList。把该 Skill 与需要处理的单词列表交给 ChatGPT，即可生成可直接放入 `wordlist/` 的 JSON 文件。

## 设计原则

- 不使用数据库。
- 不增加额外 Service 层。
- 不使用复杂依赖注入、异步框架、复杂泛型或元编程。
- 数据模型、文件读写、复习逻辑和 UI 分离，但不过度抽象。
- 业务逻辑保持简单稳定，界面样式集中放在 `resources/styles/light.qss` 中维护。
