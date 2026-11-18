"""Local bilingual similarity screening. The score orders passages for editorial reading."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


def vectors(texts, tokenizer, model):
    # Use the same prefix for the symmetric EN/ZH comparison. Break long
    # paragraphs into pieces so that a low score can reflect their full text.
    encoded=tokenizer.encode_batch(["query: "+t for t in texts],add_special_tokens=False)
    start=tokenizer.token_to_id("<s>")
    end=tokenizer.token_to_id("</s>")
    pad=tokenizer.token_to_id("<pad>")
    chunks=[]
    for i,item in enumerate(encoded):
        for j in range(0,len(item.ids),240):
            chunks.append((i,[start,*item.ids[j:j+240],end]))
    chunks.sort(key=lambda x:len(x[1]))
    vec=np.zeros((len(texts),384),dtype=np.float32)
    for offset in range(0,len(chunks),24):
        batch=chunks[offset:offset+24]
        length=max(len(ids) for _,ids in batch)
        ids=np.full((len(batch),length),pad,dtype=np.int64)
        mask=np.zeros_like(ids)
        for j,(_,tokens) in enumerate(batch):
            ids[j,:len(tokens)]=tokens
            mask[j,:len(tokens)]=1
        result=model.run(None,dict(input_ids=ids,attention_mask=mask,token_type_ids=np.zeros_like(ids)))[0]
        summed=np.einsum("ijk,ij->ik",result,mask,dtype=np.float32,casting="unsafe")
        for j,(i,_) in enumerate(batch):
            vec[i]+=summed[j]
    return vec / np.maximum(np.linalg.norm(vec,axis=1,keepdims=True),1e-9)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("cache",type=Path)
    p.add_argument("model_dir",type=Path)
    args=p.parse_args()
    tokenizer=Tokenizer.from_file(str(args.model_dir/"tokenizer.json"))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    settings=ort.SessionOptions()
    settings.intra_op_num_threads=6
    settings.inter_op_num_threads=1
    model=ort.InferenceSession(str(args.model_dir/"model_qint8_avx512_vnni.onnx"),settings,
                               providers=["CPUExecutionProvider"])
    with closing(sqlite3.connect(args.cache)) as db:
        while True:
            rows=db.execute("SELECT rowid,en,zh FROM corpus WHERE similarity IS NULL ORDER BY rowid LIMIT 256").fetchall()
            if not rows:
                break
            texts=[r[1] for r in rows]+[r[2] for r in rows]
            vec=vectors(texts,tokenizer,model)
            similarities=np.sum(vec[:len(rows)]*vec[len(rows):],axis=1)
            with db:
                db.executemany("UPDATE corpus SET similarity=? WHERE rowid=?",
                               [(float(score),r[0]) for r,score in zip(rows,similarities)])
            print(rows[-1][0],flush=True)


if __name__=="__main__":
    main()
