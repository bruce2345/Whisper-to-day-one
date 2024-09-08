import os
import subprocess
import glob
import json
import re
import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed
import openai

class TranscriptionImporter:
    def __init__(self, input_dir, output_dir, journal_name="日志", language="zh", max_workers=4, openai_api_key=None):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.journal_name = journal_name
        self.language = language
        self.model_name = "openai/whisper-small"
        self.max_workers = max_workers
        self.imported_files_record = os.path.join(output_dir, "imported_files.json")
        self.imported_files = self.load_imported_files()
        self.openai_api_key = openai_api_key
        if openai_api_key:
            openai.api_key = openai_api_key

    def load_imported_files(self):
        if os.path.exists(self.imported_files_record):
            with open(self.imported_files_record, 'r') as f:
                return json.load(f)
        return {}

    def save_imported_files(self):
        with open(self.imported_files_record, 'w') as f:
            json.dump(self.imported_files, f)

    def get_creation_date(self, audio_path):
        command = ['ffmpeg', '-i', audio_path]
        result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        output = result.stderr
        match = re.search(r'creation_time\s+:\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', output)
        if match:
            creation_date_str = match.group(1)
            creation_date = datetime.datetime.strptime(creation_date_str, '%Y-%m-%dT%H:%M:%S')
            creation_date = pytz.utc.localize(creation_date).astimezone()
            return creation_date
        else:
            return datetime.datetime.now()

    def convert_to_wav(self, audio_path):
        wav_path = audio_path.rsplit('.', 1)[0] + '.wav'
        if os.path.exists(wav_path):
            print(f"{wav_path} already exists, skipping conversion.")
            return wav_path
        command = ['ffmpeg', '-i', audio_path, wav_path]
        try:
            subprocess.run(command, check=True)
            print(f"Converted {audio_path} to {wav_path}")
            return wav_path
        except subprocess.CalledProcessError as e:
            print(f"Error converting {audio_path} to wav: {e}")
            return None

    def transcribe_audio(self, audio_path):
        print(f"Transcribing {audio_path} in {self.language} using {self.model_name} model...")
        transcript_path = os.path.join(self.output_dir, "output.json")
        command = [
            "insanely-fast-whisper",
            "--file-name", audio_path,
            "--language", self.language,
            "--transcript-path", transcript_path,
            "--device-id", "mps",
            "--model-name", self.model_name
        ]
        try:
            subprocess.run(command, check=True)
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcription_data = json.load(f)
            transcription_text = transcription_data.get('text', '')
            return transcription_text
        except subprocess.CalledProcessError as e:
            print(f"Error during transcription: {e}")
            return None

    def save_transcription_to_file(self, transcription, creation_date, filename):
        sanitized_filename = f"{creation_date.strftime('%Y-%m-%d_%H-%M-%S')}_{self.sanitize_filename(filename)}.txt"
        filepath = os.path.join(self.output_dir, sanitized_filename)
        full_transcription = f"{creation_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n{transcription}"

        if self.openai_api_key:
            # 使用 GPT-4 优化转录结果
            prompt = """您好, 超GPT，你是一个不知疲倦，无所不能的超级英雄。我需要您协助处理我的语音日记。这些日记是我在打扫房间时录制的,可能存在以下特点:
            1. 思路较为发散 2. 由于语音识别可能存在一些错误 3. 我的普通话发音可能不标准 请您帮我完成以下任务:
            1. 根据原始内容撰写新的日记版本。在此过程中,请:
            * 确保每一句原文的内容都被包含,不遗漏任何信息
            不需要结构清晰，需要完全忠于原文。
            * 保持原意不变
            * 根据上下文修正可能存在的同音字或近似音单词错误
            * 考虑我的发音特点,根据上下文推测最准确的表达。 请给出最终的版本，不要有其他的内容，需要适当分段。"""
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": prompt + "\n\n" + full_transcription}
                ]
            )
            optimized_transcription = response["choices"][0]["message"]["content"].strip()
            full_transcription = f"{creation_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n{optimized_transcription}"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_transcription)
        return filepath

    def sanitize_filename(self, filename):
        return "".join([c for c in filename if c.isalpha() or c.isdigit() or c in ' -_.']).rstrip()

    def import_to_dayone(self, filepath, content, date_str):
        file_hash = hash(content)
        if file_hash in self.imported_files:
            print(f"Skipped importing {filepath} (content already imported)")
            return
        try:
            subprocess.run([
                "dayone2",
                "new",
                "--date", date_str,
                "--journal", self.journal_name,
            ], input=content, capture_output=True, text=True, check=True)
            print(f"Imported content from {filepath} to Day One")
            self.imported_files[file_hash] = "transcribed"
            self.save_imported_files()
        except subprocess.CalledProcessError as e:
            print(f"Error importing content from {filepath} to Day One: {e}")

    def process_file(self, audio_path):
        try:
            filename = os.path.basename(audio_path)

            # Skip if the file has already been processed or deleted
            if filename in self.imported_files:
                if self.imported_files[filename] in ["transcribed", "deleted"]:
                    print(f"{filename} has already been processed. Skipping.")
                    return

            # Check file size, delete if smaller than 100KB
            file_size_kb = os.path.getsize(audio_path) / 1024
            if file_size_kb < 100:
                print(f"{filename} is smaller than 100KB, deleting file.")
                os.remove(audio_path)
                self.imported_files[filename] = "deleted"
                self.save_imported_files()
                return

            self.imported_files[filename] = "transcribing"
            self.save_imported_files()

            # Proceed with transcription
            creation_date = self.get_creation_date(audio_path)
            original_audio_path = audio_path
            if audio_path.lower().endswith('.m4a'):
                audio_path = self.convert_to_wav(audio_path)
                if audio_path is None:
                    return
            transcription = self.transcribe_audio(audio_path)
            if transcription:
                filepath = self.save_transcription_to_file(transcription, creation_date, filename)
                if filepath:
                    content = self.read_file_content(filepath)
                    date_str = creation_date.strftime("%Y-%m-%dT%H:%M:%S")
                    self.import_to_dayone(filepath, content, date_str)
                    os.remove(filepath)
                    if audio_path.endswith('.wav'):
                        os.remove(audio_path)
                        print(f"Deleted temporary file: {audio_path}")
                    new_audio_path = os.path.join(self.output_dir, os.path.basename(original_audio_path))
                    os.rename(original_audio_path, new_audio_path)
                    print(f"Moved original file to {new_audio_path}")
                    self.imported_files[filename] = "transcribed"
                    self.save_imported_files()
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            if filename in self.imported_files and self.imported_files[filename] == "transcribing":
                del self.imported_files[filename]
                self.save_imported_files()

    def run(self):
        # 获取三天前的日期
        three_days_ago = datetime.datetime.now() - datetime.timedelta(days=3)
        today_date = three_days_ago.strftime("%Y-%m-%d")

        # 使用 cp 命令复制三天内创建的 m4a 文件到目标目录
        copy_command = f'find "/Users/everydayisanewpractice/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings" -type f -name "*.m4a" -newermt "{today_date}" -exec cp {{}} "/Users/everydayisanewpractice/Documents/语音日记" \;'
        subprocess.run(copy_command, shell=True)

        # 查找语音日记目录中的音频文件
        audio_files = glob.glob(os.path.join(self.input_dir, "*"))
        audio_files = [f for f in audio_files if f.lower().endswith(('.mp3', '.m4a', '.wav', '.ogg', '.flac'))]

        if not audio_files:
            print(f"No audio files found in {self.input_dir}")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.process_file, audio_path) for audio_path in audio_files]
            for future in as_completed(futures):
                future.result()

        self.save_imported_files()

        # Ensure the "语音日记" folder is empty after processing
        for audio_path in audio_files:
            try:
                os.remove(audio_path)
                print(f"Deleted file {audio_path} after processing.")
            except Exception as e:
                print(f"Error deleting file {audio_path}: {str(e)}")

    def read_file_content(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            print(f"Warning: Unable to read file {file_path} due to encoding issues.")
            return None

if __name__ == "__main__":
    input_dir = ""
    output_dir = ""
    language = "zh"  # Set to "zh" for Simplified Chinese, "en" for English
    openai_api_key = ""  # Replace with your OpenAI API key
    importer = TranscriptionImporter(input_dir, output_dir, journal_name="日志", language=language, max_workers=4, openai_api_key=openai_api_key)
    importer.run() 
