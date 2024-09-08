```
## 语音日记导入 Day One 脚本

该 Python 脚本用于自动将语音日记文件（例如，从语音备忘录中导出）转录成文本，并导入到 Day One 应用中。

**功能:**

1. **语音文件查找与复制:** 查找三天内创建的语音文件，并将其复制到指定的输入目录。
2. **格式转换:** 将音频文件转换为 WAV 格式，方便后续转录。
3. **语音转录:** 使用 `insanely-fast-whisper` 库进行语音识别，并将转录结果保存为 JSON 文件。
4. **转录结果优化 (可选):** 使用 OpenAI API (GPT-4) 优化转录结果，修正可能的错误和歧义。
5. **转录文本保存:** 将转录文本与创建时间一起保存到 TXT 文件中。
6. **导入 Day One:** 将 TXT 文件内容导入到 Day One 应用中，并记录已导入的文件，避免重复导入。
7. **文件清理:** 删除临时文件和已处理的语音文件。


**使用方法:**

1. **安装依赖项:**
   ```bash
   pip install insanely-fast-whisper ebooklib openai
   ```
2. **配置变量:**
   - 修改脚本底部 `input_dir`、`output_dir`、`language` 和 `openai_api_key` 变量，以匹配您的文件路径和 OpenAI API 密钥。
3. **安装 Day One 命令行工具:** 确保已安装 Day One 的命令行工具 (`dayone2`)。
4. **运行脚本:**
   ```bash
   python your_script_name.py 
   ```


**注意事项:**

- 脚本默认使用 `openai/whisper-small` 模型进行转录，您可以修改 `model_name` 变量以使用其他模型。
- GPT-4 优化功能需要提供有效的 OpenAI API 密钥。
- 脚本会自动查找三天内创建的语音文件，并将它们复制到输入目录。
- 如果 `imported_files.json` 文件存在，脚本会读取该文件，并跳过已处理的文件。
- 脚本会删除临时文件（WAV 文件）和已处理的语音文件，以保持文件系统整洁。


**配置说明:**

- **`input_dir`:** 语音文件所在的输入目录。
- **`output_dir`:** 转录文本和临时文件的输出目录。
- **`language`:** 语音语言，例如 `zh` 表示简体中文，`en` 表示英语。
- **`openai_api_key`:** OpenAI API 密钥，用于 GPT-4 优化。
- **`journal_name`:** Day One 中的日记本名称。


**脚本核心功能:**

- `TranscriptionImporter` 类：主要类，包含所有功能。
- `load_imported_files`：加载已导入文件记录。
- `save_imported_files`：保存已导入文件记录。
- `get_creation_date`：获取音频文件的创建时间。
- `convert_to_wav`：将音频文件转换为 WAV 格式。
- `transcribe_audio`：使用 `insanely-fast-whisper` 进行语音转录。
- `save_transcription_to_file`：保存转录文本到 TXT 文件。
- `sanitize_filename`：清理文件名，使其符合文件系统要求。
- `import_to_dayone`：将转录文本导入到 Day One。
- `process_file`：处理单个音频文件，包括转录、保存、导入等操作。
- `run`：启动脚本，查找、处理、导入所有音频文件。


希望以上描述能够帮助您更好地理解这个脚本的功能和使用方法。
