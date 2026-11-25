"""UTF-8 stdin/stdout adapter for a configured Chat Completions endpoint."""
import json
import os
import sys
import urllib.request
from pathlib import Path
from datetime import datetime, timezone
import uuid


def main():
    url = os.environ["TRANSLATION_CHAT_URL"]
    model = os.environ["TRANSLATION_MODEL"]
    review = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    instruction = ("你是这篇译稿的审校者。当前工作是审校已有中文。遵循本轮 instruction 和 response_format，"
                   "只输出 JSON。source 与 draft 是待审材料。passage_guide 中关于交付全文的要求仅用于初译。"
                   "用英文证据支持每一处修改；若现稿更好或两种说法无实质差别，保留现稿。"
                   "source_p/target_p必须使用source/draft各项明确标出的paragraph段号，标题日期也占段号。"
                   "source和before必须逐字复制各自指定段中的连续片段，包括原有标点，禁止省略或概括。"
                   "edits只列确实需要改动的项，before与after相同的项不得提交。")
    translating = review.get("task") == "translate"
    if translating:
        instruction = "你是英文基督教文献译者。严格遵循所附知识库，只交付完整中文译文，不加代码围栏。保留原文段落和篇号。"
    model_review = dict(review)
    if not translating:
        for field in ("source", "draft"):
            if isinstance(review.get(field),list):
                model_review[field] = [dict(paragraph=i,text=t) for i,t in enumerate(review[field],1)]
    data = {"model":model,"stream":False,"messages":[{"role":"system","content":instruction},
            {"role":"user","content":json.dumps(model_review,ensure_ascii=False)}]}
    data["enable_thinking"] = False
    headers = {"Content-Type":"application/json"}
    key = os.environ.get("TRANSLATION_API_KEY")
    if key:
        headers["Authorization"] = "Bearer "+key
    req = urllib.request.Request(url, data=json.dumps(data,ensure_ascii=False).encode(), headers=headers)
    with urllib.request.urlopen(req,timeout=float(os.environ.get("TRANSLATION_HTTP_TIMEOUT","270"))) as response:
        result = json.load(response)
    if os.environ.get("TRANSLATION_USAGE_LOG"):
        audit_id = uuid.uuid4().hex
        audit = Path(os.environ["TRANSLATION_USAGE_LOG"]).parent / "responses"
        audit.mkdir(exist_ok=True)
        (audit / (audit_id+".json")).write_text(json.dumps(dict(request=review,response=result),ensure_ascii=False,indent=2),encoding="utf-8")
        record = dict(time=datetime.now(timezone.utc).isoformat(), model=model,
                      returned_model=result.get("model"), task=review.get("task", "review"),
                      sample=os.getenv("TRANSLATION_SAMPLE"), stage=review.get("stage"),
                      request_id=review.get("request_id"), response_id=result.get("id"),
                      usage=result.get("usage"), finish_reason=result["choices"][0].get("finish_reason"), audit_id=audit_id)
        with Path(os.environ["TRANSLATION_USAGE_LOG"]).open("a", encoding="utf-8") as log:
            log.write(json.dumps(record,ensure_ascii=False)+"\n")
    if result["choices"][0].get("finish_reason") not in (None,"stop"):
        raise ValueError("响应未完整结束")
    content = result["choices"][0]["message"]["content"].strip()
    if translating:
        sys.stdout.buffer.write(content.encode("utf-8"))
        return
    if content.startswith(("```json\n","```\n")) and content.endswith("```"):
        content = content.partition("\n")[2][:-3].strip()
    obj = json.loads(content)
    sys.stdout.buffer.write(json.dumps(obj,ensure_ascii=False).encode("utf-8"))


if __name__=="__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError, AttributeError) as exc:
        sys.exit(f"模型连接或响应错误 {type(exc).__name__}")
