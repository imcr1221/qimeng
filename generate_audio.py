import os
import asyncio
import traceback
from pathlib import Path
from bs4 import BeautifulSoup
import edge_tts

VOICE = "zh-CN-XiaoxiaoNeural"

async def process_module(module_dir: Path):
    html_file = module_dir / "index.html"
    if not html_file.exists():
        return

    print(f"\n📂 正在处理模块: {module_dir.name}")

    audio_dir = module_dir / "audio"
    audio_dir.mkdir(exist_ok=True)

    try:
        with open(html_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception as e:
        print(f"  ❌ 读取 HTML 失败: {e}")
        return

    for script in soup(["script", "style"]):
        script.decompose()

    texts = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'div']):
        text = tag.get_text(strip=True)
        if text and len(text) > 3:
            texts.append(text)

    unique_texts = list(dict.fromkeys(texts))
    manifest = {}
    
    # 每次重新生成前，先清空旧的音频（防止静音陷阱）
    for old_file in audio_dir.glob("*.mp3"):
        try:
            old_file.unlink()
        except:
            pass

    for i, text in enumerate(unique_texts):
        filename = f"line_{i}.mp3"
        output_path = audio_dir / filename
        manifest[text] = filename

        print(f"  🔊 生成中: {filename} -> {text[:15]}...")
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate="-10%")
            await communicate.save(output_path)
            
            if output_path.stat().st_size < 1000:
                print(f"  ⚠️ 警告: {filename} 文件过小，可能生成失败！")
                
        except Exception as e:
            print(f"  ❌ 单句失败: {text[:10]}... 错误: {e}")
            # 继续下一句，不中断整个模块

    try:
        manifest_path = audio_dir / "tts-manifest.js"
        js_content = f"window.TTS_AUDIO = {repr(manifest)};"
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(js_content)
        print(f"  ✅ 已更新 {manifest_path.name}")
    except Exception as e:
        print(f"  ❌ 写入 manifest 失败: {e}")

async def main():
    root_dir = Path(".")
    
    tasks = []
    for item in root_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.') and item.name not in ['audio', 'assets', 'js']:
            tasks.append(process_module(item))
            
    if not tasks:
        print("未找到任何包含 index.html 的模块目录。")
        return

    print(f"找到 {len(tasks)} 个模块，开始自动生成语音...")
    # 增加 return_exceptions=True，防止单个模块异常导致全局崩溃
    await asyncio.gather(*tasks, return_exceptions=True)
    print("\n🎉 所有模块语音生成任务完成！")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("🚨 发生全局异常:")
        traceback.print_exc()
        exit(1)
