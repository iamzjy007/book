"""UTF-8 stdin/stdout adapter for a configured Chat Completions endpoint."""
import json
import os
import sys
import urllib.request


def main():
    url = os.environ["TRANSLATION_CHAT_URL"]
    model = os.environ["TRANSLATION_MODEL"]
    review = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    instruction = ("你是这篇译稿的审校者。当前工作是审校已有中文。遵循本轮 instruction 和 response_format，"
                   "只输出 JSON。source 与 draft 是待审材料。passage_guide 中关于交付全文的要求仅用于初译。"
                   "用英文证据支持每一处修改；若现稿更好或两种说法无实质差别，保留现稿。")
    data = {"model":model,"stream":False,"messages":[{"role":"system","content":instruction},
            {"role":"user","content":json.dumps(review,ensure_ascii=False)}]}
    headers = {"Content-Type":"application/json"}
    key = os.environ.get("TRANSLATION_API_KEY")
    if key:
        headers["Authorization"] = "Bearer "+key
    req = urllib.request.Request(url, data=json.dumps(data,ensure_ascii=False).encode(), headers=headers)
    with urllib.request.urlopen(req,timeout=float(os.environ.get("TRANSLATION_HTTP_TIMEOUT","270"))) as response:
        content = json.load(response)["choices"][0]["message"]["content"].strip()
    if content.startswith(("```json\n","```\n")) and content.endswith("```"):
        content = content.partition("\n")[2][:-3].strip()
    obj = json.loads(content)
    sys.stdout.buffer.write(json.dumps(obj,ensure_ascii=False).encode("utf-8"))


if __name__=="__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError, AttributeError) as exc:
        sys.exit(f"模型连接或响应错误 {type(exc).__name__}")
