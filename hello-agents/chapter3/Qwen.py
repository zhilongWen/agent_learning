# 增加HF_ENDPOINT，避免Connection aborted.
import os

# 国内镜像，解决 huggingface 下载失败
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# 指定模型ID
model_id = "Qwen/Qwen1.5-0.5B-Chat"

if __name__ == '__main__':
    # 设备：Mac 用 mps 加速，比 cpu 快很多！
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"  # 苹果 M1/M2/M3 加速
    else:
        device = "cpu"

    print(f"Using device: {device}")

    # 加载分词器 + 模型（增加 trust_remote_code，防止报错）
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        dtype=torch.float16 if device != "cpu" else torch.float32  # 这里修复了警告
    ).to(device)

    print("模型和分词器加载完成！")

    # 准备对话输入
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你好，请介绍你自己。"}
    ]

    # 格式化输入
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    # 编码
    model_inputs = tokenizer([text], return_tensors="pt").to(device)
    print("编码后的输入文本:")
    print(model_inputs)

    # 生成回答
    generated_ids = model.generate(
        model_inputs.input_ids,
        max_new_tokens=512,
        pad_token_id=tokenizer.eos_token_id  # 修复警告
    )

    # 只保留生成的部分
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    # 解码输出
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    print("\n模型的回答:")
    print(response)
