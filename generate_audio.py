import os
import asyncio
from pathlib import Path
from bs4 import BeautifulSoup
import edge_tts

# 语音角色配置 (中文女声)
VOICE = "zh-CN-XiaoxiaoNeural"

async def process_module(module_dir: Path):
    """处理单个模块（如 10transport）"""
    html_file = module_dir / "index.html"
    if not html_file.exists():
        return

    print(f"📂 正在处理模块: {module_dir.name}")

    # 1. 确保该模块下有 audio 文件夹
    audio_dir = module_dir / "audio"
    audio_dir.mkdir(exist_ok=True)

    # 2. 读取并解析 HTML
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # 移除脚本和样式
    for script in soup(["script", "style"]):
        script.decompose()

    # 提取所有的段落和标题
    texts = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'div']):
        # 只提取纯文本内容，排除嵌套的空 div
        text = tag.get_text(strip=True)
        if text and len(text) > 3: # 过滤太短的无效文本
            texts.append(text)

    # 去重并保持顺序
    unique_texts = list(dict.fromkeys(texts))

    manifest = {}
    
    # 3. 逐条生成语音
    for i, text in enumerate(unique_texts):
        # 用文本的哈希值或索引作为文件名，避免特殊字符报错
        # 这里使用简单的递增命名：line_0.mp3, line_1.mp3
        filename = f"line_{i}.mp3"
        output_path = audio_dir / filename
        
        manifest[text] = filename

        # 断点续传：如果文件已存在且大于1000字节，跳过
        if output_path.exists() and output_path.stat().st_size > 1000:
            print(f"  ⏭️ 跳过已存在: {filename}")
            continue

        print(f"  🔊 生成中: {filename} -> {text[:15]}...")
        try:
            communicate = edge_tts.Communicate(text, VOICE， rate="-25%")
            await communicate.save(output_path)
            
            # 检查生成的静音bug
            if output_path.stat().st_size < 1000:
                print(f"  ⚠️ 警告: {filename} 文件过小，可能生成失败！")
        except Exception as e:
            print(f"  ❌ 失败: {text[:10]}... 错误: {e}")

    # 4. 生成该模块专属的 tts-manifest.js
    manifest_path = audio_dir / "tts-manifest.js"
    js_content = f"window.TTS_AUDIO = {repr(manifest)};"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"  ✅ 已更新 {manifest_path}\n")

async def main():
    root_dir = Path(".") # 当前仓库根目录
    
    tasks = []
    # 遍历根目录下所有的子文件夹
    for item in root_dir.iterdir():
        # 排除 .git, .github 等隐藏文件夹，以及根目录的 index.html 所在层级
        if item.is_dir() and not item.name.startswith('.') and item.name not in ['audio', 'assets', 'js']:
            tasks.append(process_module(item))
            
    if not tasks:
        print("未找到任何包含 index.html 的模块目录。")
        return

    print(f"找到 {len(tasks)} 个模块，开始自动生成语音...")
    await asyncio.gather(*tasks)
    print("🎉 所有模块语音生成完成！")

if __name__ == "__main__":
    asyncio.run(main())
