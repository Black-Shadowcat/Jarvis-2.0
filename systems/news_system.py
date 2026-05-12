import asyncio
import feedparser
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

FEEDS_PATH   = os.path.join(os.path.dirname(__file__), "..", "config", "rss_feeds.json")
ARCHIVE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "news_memory.json")

_EMPTY_ARCHIVE: Dict = {
    "articles": [],
    "max_entries": 10000,
    "cleanup_strategy": "FIFO",
    "last_fetch": None,
}


class NewsSystem:
    def __init__(self, config: dict, logger) -> None:
        self._config = config
        self._logger = logger
        self._news_lock = asyncio.Lock()
        self._feeds_lock = asyncio.Lock()

    # ── Feed Config & CRUD ────────────────────────────────────────────────────

    def load_feeds(self) -> List[Dict]:
        """Read rss_feeds.json and return only enabled feeds."""
        try:
            with open(FEEDS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [feed for feed in data.get("feeds", []) if feed.get("enabled", False)]
        except FileNotFoundError:
            self._logger.warning("rss_feeds.json not found — returning empty feed list")
            return []
        except json.JSONDecodeError as e:
            self._logger.error(f"rss_feeds.json corrupt: {e}")
            return []

    def load_all_feeds(self) -> Dict:
        """Read rss_feeds.json and return raw data with ALL feeds (enabled + disabled)."""
        try:
            with open(FEEDS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"feeds": []}
        except json.JSONDecodeError as e:
            self._logger.error(f"rss_feeds.json corrupt: {e}")
            return {"feeds": []}

    def _write_feeds(self, data: Dict) -> None:
        os.makedirs(os.path.dirname(FEEDS_PATH), exist_ok=True)
        with open(FEEDS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def save_feeds(self, feeds_list: List[Dict]) -> bool:
        async with self._feeds_lock:
            try:
                self._write_feeds({"feeds": feeds_list})
                self._logger.info(f"Saved {len(feeds_list)} feeds")
                return True
            except Exception as e:
                self._logger.error(f"save_feeds failed: {e}")
                return False

    async def add_feed(self, name: str, url: str, category: str) -> Dict:
        async with self._feeds_lock:
            data = self.load_all_feeds()
            new_id = "feed_" + hashlib.md5(f"{name}:{url}".encode()).hexdigest()[:8]
            new_feed = {"id": new_id, "name": name.strip(), "url": url.strip(),
                        "category": category.strip(), "enabled": True}
            data["feeds"].append(new_feed)
            self._write_feeds(data)
            self._logger.info(f"Added feed: {name}")
            return new_feed

    async def update_feed(self, feed_id: str, name: str, url: str, category: str) -> bool:
        async with self._feeds_lock:
            data = self.load_all_feeds()
            for feed in data["feeds"]:
                if feed["id"] == feed_id:
                    feed["name"] = name.strip()
                    feed["url"] = url.strip()
                    feed["category"] = category.strip()
                    self._write_feeds(data)
                    self._logger.info(f"Updated feed {feed_id}: {name}")
                    return True
            self._logger.warning(f"update_feed: '{feed_id}' not found")
            return False

    async def toggle_feed(self, feed_id: str) -> Optional[bool]:
        """Toggle enabled state. Returns new state or None if not found."""
        async with self._feeds_lock:
            data = self.load_all_feeds()
            for feed in data["feeds"]:
                if feed["id"] == feed_id:
                    feed["enabled"] = not feed.get("enabled", True)
                    self._write_feeds(data)
                    self._logger.info(f"Toggled feed {feed_id}: enabled={feed['enabled']}")
                    return feed["enabled"]
            self._logger.warning(f"toggle_feed: '{feed_id}' not found")
            return None

    async def delete_feed(self, feed_id: str) -> bool:
        async with self._feeds_lock:
            data = self.load_all_feeds()
            before = len(data["feeds"])
            data["feeds"] = [f for f in data["feeds"] if f["id"] != feed_id]
            if len(data["feeds"]) == before:
                self._logger.warning(f"delete_feed: '{feed_id}' not found")
                return False
            self._write_feeds(data)
            self._logger.info(f"Deleted feed {feed_id}")
            return True

    # ── RSS Fetching ──────────────────────────────────────────────────────────

    async def fetch_rss_feeds(self) -> List[Dict]:
        """Fetch top 10 articles per enabled feed in parallel via executor."""
        feeds = self.load_feeds()
        loop = asyncio.get_event_loop()

        async def _fetch_one(feed: Dict) -> List[Dict]:
            try:
                parsed = await loop.run_in_executor(None, feedparser.parse, feed["url"])
                if parsed.bozo and not parsed.entries:
                    self._logger.warning(
                        f"Feed '{feed['name']}' unreachable: {parsed.get('bozo_exception', 'unknown error')}"
                    )
                    return []
                articles = []
                for entry in parsed.entries[:10]:
                    title = entry.get("title", "").strip()
                    url = entry.get("link", "").strip()
                    if not title or not url:
                        continue
                    published = None
                    if getattr(entry, "published_parsed", None):
                        try:
                            published = datetime(*entry.published_parsed[:6]).isoformat()
                        except Exception:
                            pass
                    articles.append({
                        "id": self._article_id(title, url),
                        "title": title,
                        "url": url,
                        "source": feed["name"],
                        "category": feed.get("category", ""),
                        "published": published or datetime.now().isoformat(),
                        "read": False,
                        "archived_at": datetime.now().isoformat(),
                    })
                return articles
            except Exception as e:
                self._logger.warning(f"Feed '{feed['name']}' unreachable: {e}")
                return []

        results = await asyncio.gather(*[_fetch_one(f) for f in feeds])
        return [article for feed_articles in results for article in feed_articles]

    # ── Dedup ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _article_id(title: str, url: str) -> str:
        """12-char MD5 fingerprint of title+url."""
        return hashlib.md5(f"{title}:{url}".encode()).hexdigest()[:12]

    async def filter_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """Return only articles whose id is not already in the archive."""
        archive = await self.get_archive()
        known_ids = {a["id"] for a in archive.get("articles", [])}
        return [a for a in articles if a["id"] not in known_ids]

    # ── Archive I/O ───────────────────────────────────────────────────────────

    async def get_archive(self) -> Dict:
        """Read news_memory.json; recreate from empty state if missing or corrupt."""
        try:
            with open(ARCHIVE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return json.loads(json.dumps(_EMPTY_ARCHIVE))
        except json.JSONDecodeError:
            self._logger.error("news_memory.json corrupt — resetting to empty archive")
            archive = json.loads(json.dumps(_EMPTY_ARCHIVE))
            self._write_archive(archive)
            return archive

    def _write_archive(self, archive: Dict) -> None:
        os.makedirs(os.path.dirname(ARCHIVE_PATH), exist_ok=True)
        with open(ARCHIVE_PATH, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)

    async def save_to_archive(self, articles: List[Dict]) -> bool:
        """Append new articles under _news_lock; deduplicate and run FIFO cleanup."""
        async with self._news_lock:
            try:
                archive = await self.get_archive()
                known_ids = {a["id"] for a in archive.get("articles", [])}
                new_articles = [a for a in articles if a["id"] not in known_ids]
                if not new_articles:
                    return True
                archive["articles"].extend(new_articles)
                archive["last_fetch"] = datetime.now().isoformat()
                self._apply_fifo_cleanup(archive)
                self._write_archive(archive)
                self._logger.info(
                    f"Archived {len(new_articles)} new articles "
                    f"(total: {len(archive['articles'])})"
                )
                return True
            except Exception as e:
                self._logger.error(f"save_to_archive failed: {e}")
                return False

    async def cleanup_if_needed(self) -> None:
        """Standalone FIFO cleanup — acquires lock, reads, cleans, saves."""
        async with self._news_lock:
            archive = await self.get_archive()
            changed = self._apply_fifo_cleanup(archive)
            if changed:
                self._write_archive(archive)

    def _apply_fifo_cleanup(self, archive: Dict) -> bool:
        """Mutate archive in place; return True if any articles were removed."""
        max_entries = archive.get("max_entries", 10000)
        removed = 0
        while len(archive["articles"]) > max_entries:
            old = archive["articles"].pop(0)
            self._logger.info(
                f"FIFO cleanup: removed '{old.get('title', '')[:60]}' "
                f"({old.get('published', '')[:10]})"
            )
            removed += 1
        return removed > 0

    # ── Search & Read-State ───────────────────────────────────────────────────

    async def search_archive(self, query: str) -> List[Dict]:
        """Case-insensitive substring search over title and url."""
        archive = await self.get_archive()
        q = query.lower()
        return [
            a for a in archive.get("articles", [])
            if q in a.get("title", "").lower() or q in a.get("url", "").lower()
        ]

    async def get_unread_articles(self) -> List[Dict]:
        """Return all articles with read=False, newest first."""
        archive = await self.get_archive()
        unread = [a for a in archive.get("articles", []) if not a.get("read", False)]
        return sorted(unread, key=lambda a: a.get("published", ""), reverse=True)

    async def mark_as_read(self, article_id: str) -> bool:
        """Set read=True for article_id under _news_lock; return False if not found."""
        async with self._news_lock:
            try:
                archive = await self.get_archive()
                for article in archive.get("articles", []):
                    if article["id"] == article_id:
                        article["read"] = True
                        self._write_archive(archive)
                        return True
                self._logger.warning(f"mark_as_read: article '{article_id}' not found")
                return False
            except Exception as e:
                self._logger.error(f"mark_as_read failed: {e}")
                return False
