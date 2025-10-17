import requests
import feedparser
import json
import argparse
import sys
import os

def summarize_text(host: str, model: str, text: str) -> str:
    payload = {
        "model": model,
        "prompt": f"Summarize this article briefly:\n\n{text}"
    }
    try:
        with requests.post(f"http://{host}:11434/api/generate", json=payload, stream=True, timeout=120) as r:
            r.raise_for_status()
            summary = ""
            for line in r.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "response" in data:
                    summary += data["response"]
                if data.get("done"):
                    break
            return summary.strip()
    except Exception as e:
        return f"[Error summarizing: {e}]"

def load_summaries(file_path: str):
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_summaries(file_path: str, data: dict):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Error saving summaries: {e}]")

def summarize_rss_feed(rss_url: str, host: str, model: str, summaries: dict, output_file: str):
    feed = feedparser.parse(rss_url)
    feed_title = feed.feed.get('title', rss_url)
    print(f"\n📡 Feed: {feed_title}")
    print(f"Found {len(feed.entries)} entries\n")

    if feed_title not in summaries:
        summaries[feed_title] = []

    known_links = {entry["link"] for entry in summaries[feed_title] if "link" in entry}

    for entry in feed.entries:
        link = entry.get("link")
        title = entry.get("title", "Untitled")

        if not link:
            print(f"Skipping entry with no link: {title}")
            continue

        if link in known_links:
            print(f"⏩ Skipping already summarized: {title}")
            continue

        print(f"🔹 Summarizing: {title}")
        summary_input = entry.get("summary", entry.get("description", ""))
        if not summary_input:
            print("No content to summarize.\n")
            continue

        summary = summarize_text(host, model, summary_input)
        print(f"Summary: {summary}\n")

        summaries[feed_title].append({
            "title": title,
            "link": link,
            "summary": summary
        })

        save_summaries(output_file, summaries)  # Save progress incrementally

def read_urls_from_file(filepath: str):
    try:
        with open(filepath, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[Error reading file: {e}]")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize RSS feeds using a remote Ollama model.")
    parser.add_argument("--url", "-u", help="Single RSS feed URL")
    parser.add_argument("--file", "-f", help="File containing RSS URLs (one per line)")
    parser.add_argument("--model", "-m", default="smollm2:135m", help="Model name on Ollama host (default: smollm2:135m)")
    parser.add_argument("--host", "-H", default="localhost", help="Remote Ollama host (default: localhost)")
    parser.add_argument("--output", "-o", default="/data/summaries.json", help="Output file (default: /data/summaries.json)")
    args = parser.parse_args()

    urls = []
    if args.file:
        urls.extend(read_urls_from_file(args.file))
    if args.url:
        urls.append(args.url)

    if not urls:
        print("Error: You must provide either --url or --file.")
        sys.exit(1)

    summaries = load_summaries(args.output)
    for url in urls:
        summarize_rss_feed(url, args.host, args.model, summaries, args.output)
    print(f"\n✅ Summaries saved to: {args.output}")
