import json
import os
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
DATASET = "allenai/WildChat-1M"
REVISION = "7d6490e462285cf85d91eabea0f9a954fbddcd1f"
SOURCE_FILE = "data/train-00000-of-00014.parquet"
LANGUAGES = {"Russian": "ru", "English": "en"}
TARGETS = (100, 500, 1000)
COUNT = 100
MIN_TOKENS = 70
MAX_TOKENS = 130


def wildchat_rows():
    path = hf_hub_download(DATASET, SOURCE_FILE, repo_type="dataset", revision=REVISION)
    with pq.ParquetFile(path) as parquet:
        for batch in parquet.iter_batches(
            batch_size=256, columns=["conversation_hash", "language", "conversation"]
        ):
            yield from batch.to_pylist()


def main():
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(name, None)
    tokenizer = AutoTokenizer.from_pretrained(
        ROOT / "models/Qwen3-8B", local_files_only=True
    )
    systems = {
        lang: {
            target: (ROOT / f"data/system_prompts/{lang}_{target}.txt")
            .read_text(encoding="utf-8")
            .strip()
            for target in TARGETS
        }
        for lang in LANGUAGES.values()
    }
    selected = {lang: [] for lang in LANGUAGES.values()}
    seen = set()

    for rows_scanned, row in enumerate(wildchat_rows(), start=1):
        if rows_scanned % 1000 == 0:
            print(f"Reading row {rows_scanned}: {selected_counts(selected)}", flush=True)
        lang = LANGUAGES.get(row["language"])
        if lang is None or len(selected[lang]) == COUNT:
            continue
        conversation = row["conversation"]
        last_user = max(
            (i for i, m in enumerate(conversation) if m["role"] == "user"), default=-1
        )
        if last_user < 0 or conversation[last_user]["language"] != row["language"]:
            continue
        messages = [
            {"role": message["role"], "content": message["content"]}
            for message in conversation[:last_user + 1]
        ]
        if any(
            m["role"] not in {"user", "assistant"} or not m["content"].strip()
            for m in messages
        ):
            continue
        key = tuple((m["role"], m["content"]) for m in messages)
        if key in seen:
            continue

        token_counts = {}
        for target, system in systems[lang].items():
            tokens = tokenizer.apply_chat_template(
                [{"role": "system", "content": system}] + messages,
                tokenize=True, return_dict=False, add_generation_prompt=True,
                enable_thinking=False,
            )
            token_counts[target] = len(tokens)
            if not MIN_TOKENS <= len(tokens) <= MAX_TOKENS:
                break
        else:
            selected[lang].append({
                "id": row["conversation_hash"], "messages": messages,
                "token_counts": token_counts,
            })
            seen.add(key)
        if all(len(rows) == COUNT for rows in selected.values()):
            break

    if any(len(rows) < COUNT for rows in selected.values()):
        raise RuntimeError(f"Not enough matching requests: {selected_counts(selected)}")

    output_dir = ROOT / "data/prompts"
    output_dir.mkdir(parents=True, exist_ok=True)
    for lang, rows in selected.items():
        for target, system in systems[lang].items():
            path = output_dir / f"{lang}_{target}.jsonl"
            with path.open("w", encoding="utf-8") as stream:
                for row in rows:
                    record = {
                        "model": "qwen3-8b",
                        "messages": [{"role": "system", "content": system}] + row["messages"],
                        "stream": True,
                        "stream_options": {
                            "include_usage": True, "continuous_usage_stats": True,
                        },
                        "chat_template_kwargs": {"enable_thinking": False},
                    }
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"Saved {path.relative_to(ROOT)}: {len(rows)} requests")

    metadata = {
        "dataset": DATASET, "dataset_revision": REVISION, "source_file": SOURCE_FILE,
        "config": "default", "split": "train", "rows_scanned": rows_scanned,
        "selection": "First 100 distinct matching histories per language, ending with the last user message.",
        "tokenizer": "models/Qwen3-8B", "enable_thinking": False,
        "min_prompt_tokens": MIN_TOKENS, "max_prompt_tokens": MAX_TOKENS,
        "counts": selected_counts(selected),
        "requests": {
            lang: [
                {"id": row["id"], "prompt_tokens": row["token_counts"]}
                for row in rows
            ]
            for lang, rows in selected.items()
        },
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def selected_counts(selected):
    return {lang: len(rows) for lang, rows in selected.items()}


if __name__ == "__main__":
    main()
