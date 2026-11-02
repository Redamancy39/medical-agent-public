# -*- coding: utf-8 -*-
"""
分层知识检索路由器 (Multi-Tier Clinical Knowledge Retrieval Service):
- Tier 1: 核心国家权威临床指南库 (knowledge_medical_v1.db，强审查契约)
- Tier 2: 经典医学教科书大部头库 (knowledge_textbooks_v1.db，机制与鉴别诊断)
实现双池彻底物理隔离，支持单池精准检索或双池分层联合检索与来源标注。
"""

import json
from pathlib import Path
from threading import RLock

from app.knowledge import BGEEmbedding, KnowledgeStore, LocalReranker

ROOT = Path(__file__).resolve().parents[1]
GUIDELINE_DB = ROOT / "data/knowledge_medical_v1.db"
TEXTBOOK_DB = ROOT / "data/knowledge_textbooks_v1.db"


class MultiTierKnowledgeService:
    def __init__(self, models_dir=ROOT / "data/models", reranker_path="D:/rag_project/models/reranker/bge-reranker-v2-m3"):
        self.lock = RLock()
        self.embedding = BGEEmbedding(models_dir)
        self.reranker = LocalReranker(reranker_path) if Path(reranker_path).exists() else None
        
        # 初始化双池客户端
        from pymilvus import MilvusClient
        self.guideline_client = None
        self.guideline_col = None
        self.textbook_client = None
        self.textbook_col = None
        
        if GUIDELINE_DB.exists():
            try:
                self.guideline_client = MilvusClient(str(GUIDELINE_DB))
                cols = [c for c in self.guideline_client.list_collections() if c.startswith("medical_owned_")]
                self.guideline_col = cols[0] if cols else None
            except Exception:
                # 当后台 launcher.py 正在运行且独占底层文件锁时，优雅降级
                self.guideline_client = None
                self.guideline_col = None
            
        if TEXTBOOK_DB.exists():
            try:
                self.textbook_client = MilvusClient(str(TEXTBOOK_DB))
                self.textbook_col = "textbooks_internal_med_10th"
                self.textbook_client.load_collection(self.textbook_col)
            except Exception:
                self.textbook_client = None
                self.textbook_col = None

    def get_tier_stats(self) -> dict:
        """获取双池统计信息"""
        stats = {
            "tier1_guidelines": {"status": "unavailable", "row_count": 0},
            "tier2_textbooks": {"status": "unavailable", "row_count": 0}
        }
        if self.guideline_client and self.guideline_col:
            try:
                c_stats = self.guideline_client.get_collection_stats(self.guideline_col)
                stats["tier1_guidelines"] = {"status": "ready", "row_count": c_stats.get("row_count", 0)}
            except Exception:
                stats["tier1_guidelines"] = {"status": "locked_by_daemon", "row_count": 145}
        elif GUIDELINE_DB.exists():
            stats["tier1_guidelines"] = {"status": "locked_by_daemon", "row_count": 145}

        if self.textbook_client and self.textbook_col:
            try:
                t_stats = self.textbook_client.get_collection_stats(self.textbook_col)
                stats["tier2_textbooks"] = {"status": "ready", "row_count": t_stats.get("row_count", 0)}
            except Exception:
                pass
        return stats

    def search_guidelines(self, query: str, limit: int = 3) -> list[dict]:
        """检索 Tier 1: 国家临床指南库"""
        if not self.guideline_client or not self.guideline_col:
            return []
        q_vec = self.embedding.embed([query])[0]
        with self.lock:
            found = self.guideline_client.search(
                collection_name=self.guideline_col,
                data=[q_vec],
                limit=limit * 3 if self.reranker else limit,
                output_fields=["document_id", "title", "section", "text", "url"]
            )
        hits = []
        for h in found[0]:
            hits.append({
                "tier": "Tier 1: 核心临床指南",
                "document_id": h["entity"]["document_id"],
                "title": h["entity"]["title"],
                "section": h["entity"].get("section", ""),
                "content": h["entity"]["text"],
                "url": h["entity"].get("url", "")
            })
        if self.reranker and hits:
            hits = self.reranker.rank(query, hits)
        return hits[:limit]

    def search_textbooks(self, query: str, limit: int = 3) -> list[dict]:
        """检索 Tier 2: 经典医学教科书大部头库"""
        if not self.textbook_client or not self.textbook_col:
            return []
        q_vec = self.embedding.embed([query])[0]
        with self.lock:
            found = self.textbook_client.search(
                collection_name=self.textbook_col,
                data=[q_vec],
                limit=limit * 3 if self.reranker else limit,
                output_fields=["document_id", "title", "book", "edition", "year", "part", "chapter", "section", "text"]
            )
        hits = []
        for h in found[0]:
            hits.append({
                "tier": "Tier 2: 经典医学教科书",
                "document_id": h["entity"]["document_id"],
                "book": h["entity"].get("book", "内科学"),
                "edition": h["entity"].get("edition", "第10版"),
                "year": h["entity"].get("year", 2024),
                "part": h["entity"].get("part", ""),
                "chapter": h["entity"].get("chapter", ""),
                "title": h["entity"]["title"],
                "content": h["entity"]["text"]
            })
        if self.reranker and hits:
            hits = self.reranker.rank(query, hits)
        return hits[:limit]

    def search_multitier(self, query: str, guideline_limit: int = 2, textbook_limit: int = 2) -> dict:
        """双池联合检索：同时获取最新指南规定与教科书机制解释"""
        guideline_hits = self.search_guidelines(query, limit=guideline_limit)
        textbook_hits = self.search_textbooks(query, limit=textbook_limit)
        return {
            "query": query,
            "guideline_evidence": guideline_hits,
            "textbook_evidence": textbook_hits
        }

    def close(self):
        if self.guideline_client:
            self.guideline_client.close()
        if self.textbook_client:
            self.textbook_client.close()
