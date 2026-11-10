"""Pure NumPy/ONNX output parity and CPU timing helpers for NLI research."""
from __future__ import annotations

import statistics
import time

import numpy as np

def _softmax(array: np.ndarray) -> np.ndarray:
    if array.ndim!=2 or array.shape[1]!=3:
        raise ValueError("Expected three NLI logits per directional pair")
    temp=np.asarray(array,dtype=np.float64)
    temp=temp-np.max(temp,axis=-1,keepdims=True)
    values=np.exp(temp)
    return values/np.sum(values,axis=-1,keepdims=True)


def infer_onnx(session,tokenizer,pairs,*,batch_size=16):
    forward,reverse=[],[]
    wall_ms=[]
    token_count=0
    allowed={"input_ids","attention_mask","token_type_ids"}
    inputs=[item.name for item in session.get_inputs()]
    if not inputs or not set(inputs)<=allowed:
        raise ValueError(f"Unrecognized ONNX inputs: {inputs}")
    for offset in range(0,len(pairs),batch_size):
        chunk=pairs[offset:offset+batch_size]
        left=[item[0] for item in chunk]+[item[1] for item in chunk]
        right=[item[1] for item in chunk]+[item[0] for item in chunk]
        started=time.perf_counter()
        encoded=tokenizer(
            left,right,padding=True,truncation=True,max_length=512,
            return_tensors="np",
        )
        feed={}
        for key in inputs:
            if key not in encoded:
                raise ValueError("Official tokenizer does not supply ONNX input "+key)
            feed[key]=np.asarray(encoded[key],dtype=np.int64)
        token_count+=int(feed["input_ids"].size)
        logits=session.run(None,feed)[0]
        scores=_softmax(np.asarray(logits)).tolist()
        if len(scores)!=len(chunk)*2:
            raise ValueError("ONNX model returned incomplete batched NLI scores")
        forward.extend(scores[:len(chunk)])
        reverse.extend(scores[len(chunk):])
        wall_ms.append((time.perf_counter()-started)*1000)
    return forward,reverse,{
        "directional_inputs":2*len(pairs),
        "forward_batches":len(wall_ms),
        "input_tokens":token_count,
        "total_batch_wall_ms":sum(wall_ms),
        "batch_wall_ms_p50":statistics.median(wall_ms),
        "batch_wall_ms_p95":sorted(wall_ms)[max(0,int(0.95*(len(wall_ms)-1)))],
        "timing_scope":"tokenization+ONNX CPU execution+softmax, warm batch-only",
    }


def compare_predictions(fp: dict, quant: dict) -> dict:
    a=fp["evaluation"]["cases"]
    b=quant["evaluation"]["cases"]
    if len(a)!=318 or len(b)!=318:
        raise ValueError("Both variants must score the exact 318 cases")
    for x,y in zip(a,b,strict=True):
        if (x["case_id"],x["expected"],x["contradiction_id"]) != (
            y["case_id"],y["expected"],y["contradiction_id"]
        ):
            raise ValueError("Unmatched eval cases or original source groups")
    count=sum(x["symmetric_prediction"]==y["symmetric_prediction"]
              for x,y in zip(a,b,strict=True))
    fp_metrics=fp["evaluation"]["metrics"]
    q_metrics=quant["evaluation"]["metrics"]
    quality={
        "agreement_count":count,
        "agreement_rate":count/318,
        "changed_labels":318-count,
        "accuracy_fp32":fp_metrics["accuracy"],
        "accuracy_int8":q_metrics["accuracy"],
        "accuracy_delta_int8_minus_fp32":q_metrics["accuracy"]-fp_metrics["accuracy"],
        "balanced_accuracy_fp32":fp_metrics["balanced_accuracy"],
        "balanced_accuracy_int8":q_metrics["balanced_accuracy"],
        "balanced_accuracy_delta":q_metrics["balanced_accuracy"]-fp_metrics["balanced_accuracy"],
        "conflict_recall_fp32":fp_metrics["contradiction"]["recall"],
        "conflict_recall_int8":q_metrics["contradiction"]["recall"],
        "conflict_recall_delta":q_metrics["contradiction"]["recall"]-fp_metrics["contradiction"]["recall"],
        "false_positive_fp32":fp_metrics["confusion"]["true_non_contradiction_predicted_contradiction"],
        "false_positive_int8":q_metrics["confusion"]["true_non_contradiction_predicted_contradiction"],
    }
    if (quality["accuracy_delta_int8_minus_fp32"] >= -0.02
        and quality["conflict_recall_delta"] >= -0.05):
        quality["engineering_gate"]="PARITY_TOLERANCE_MET_ON_PUBLIC_BENCHMARK_ONLY"
    else:
        quality["engineering_gate"]="QUANTIZED_QUALITY_REGRESSION_NO_GO"
    return quality


