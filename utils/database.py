"""
Database service layer for LiquidRound workflow management.
PostgreSQL backend using the liquidround schema.
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from .logging import get_logger
from .config import config

logger = get_logger("database")

DB_URL = None


def _get_db_url():
    global DB_URL
    if DB_URL is None:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        DB_URL = os.getenv("DB_URL")
        if not DB_URL:
            raise ValueError("DB_URL environment variable is not set")
    return DB_URL


@contextmanager
def get_conn():
    """Get a PostgreSQL connection with auto-close."""
    conn = psycopg2.connect(_get_db_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class DatabaseService:
    """Database service for managing workflows and results (PostgreSQL)."""

    def __init__(self):
        try:
            # Verify connectivity at startup
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM liquidround.workflows LIMIT 0")
            logger.info("Database connection verified (liquidround schema)")
        except Exception as e:
            logger.warning(f"Database not ready: {e}")

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------
    def create_workflow(self, user_query: str, workflow_type: str = "unknown") -> str:
        workflow_id = str(uuid.uuid4())
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.workflows (id, user_query, workflow_type, status)
                VALUES (%s, %s, %s, 'pending')
            """, (workflow_id, user_query, workflow_type))
        logger.info(f"Created workflow {workflow_id}: {user_query[:50]}...")
        return workflow_id

    def update_workflow_status(self, workflow_id: str, status: str, workflow_type: str = None):
        with get_conn() as conn:
            cur = conn.cursor()
            if workflow_type:
                cur.execute("""
                    UPDATE liquidround.workflows
                    SET status = %s, workflow_type = %s, updated_at = NOW()
                    WHERE id = %s
                """, (status, workflow_type, workflow_id))
            else:
                cur.execute("""
                    UPDATE liquidround.workflows
                    SET status = %s, updated_at = NOW()
                    WHERE id = %s
                """, (status, workflow_id))
        logger.info(f"Workflow {workflow_id} -> {status}")

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT id, user_query, workflow_type, status, created_at, updated_at
                FROM liquidround.workflows WHERE id = %s
            """, (workflow_id,))
            row = cur.fetchone()
            if row:
                return {k: str(v) if isinstance(v, (datetime, uuid.UUID)) else v for k, v in dict(row).items()}
        return None

    def get_recent_workflows(self, limit: int = 10) -> List[Dict[str, Any]]:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT id, user_query, workflow_type, status, created_at, updated_at
                FROM liquidround.workflows
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            return [{k: str(v) if isinstance(v, (datetime, uuid.UUID)) else v for k, v in dict(r).items()} for r in rows]

    # ------------------------------------------------------------------
    # Agent Results
    # ------------------------------------------------------------------
    def save_agent_result(self, workflow_id: str, agent_name: str, result_data: Dict[Any, Any],
                          status: str = "success", execution_time: float = None):
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.workflow_results (workflow_id, agent_name, result_data, status, execution_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (workflow_id, agent_name, json.dumps(result_data, default=str), status, execution_time))
        logger.info(f"Saved {agent_name} result for {workflow_id}")

    def get_workflow_results(self, workflow_id: str) -> List[Dict[str, Any]]:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT agent_name, result_data, status, execution_time, created_at
                FROM liquidround.workflow_results
                WHERE workflow_id = %s
                ORDER BY created_at ASC
            """, (workflow_id,))
            results = []
            for row in cur.fetchall():
                d = dict(row)
                rd = d.get("result_data")
                if isinstance(rd, str):
                    try:
                        rd = json.loads(rd)
                    except Exception:
                        pass
                d["result_data"] = rd
                d["created_at"] = str(d["created_at"])
                results.append(d)
            return results

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------
    def add_message(self, workflow_id: str, role: str, content: str):
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.messages (workflow_id, role, content)
                VALUES (%s, %s, %s)
            """, (workflow_id, role, content))

    def get_messages(self, workflow_id: str) -> List[Dict[str, Any]]:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT role, content, timestamp
                FROM liquidround.messages
                WHERE workflow_id = %s
                ORDER BY timestamp ASC
            """, (workflow_id,))
            return [{"role": r["role"], "content": r["content"], "timestamp": str(r["timestamp"])} for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Conversations (chat history)
    # ------------------------------------------------------------------
    def create_conversation(self, user_id: str, title: str) -> str:
        """Create a new conversation (workflow_type='conversation')."""
        conv_id = str(uuid.uuid4())
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.workflows (id, user_id, user_query, workflow_type, status, conversation_title)
                VALUES (%s, %s, %s, 'conversation', 'active', %s)
            """, (conv_id, user_id, title[:200], title[:200]))
        return conv_id

    def get_user_conversations(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent conversations for a user."""
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT id, conversation_title, user_query, created_at, updated_at
                FROM liquidround.workflows
                WHERE user_id = %s AND workflow_type = 'conversation'
                ORDER BY updated_at DESC
                LIMIT %s
            """, (user_id, limit))
            return [{k: str(v) if isinstance(v, (datetime, uuid.UUID)) else v for k, v in dict(r).items()} for r in cur.fetchall()]

    def search_conversations(self, user_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search conversations by title."""
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT id, conversation_title, user_query, created_at, updated_at
                FROM liquidround.workflows
                WHERE user_id = %s AND workflow_type = 'conversation'
                  AND conversation_title ILIKE %s
                ORDER BY updated_at DESC
                LIMIT %s
            """, (user_id, f"%{query}%", limit))
            return [{k: str(v) if isinstance(v, (datetime, uuid.UUID)) else v for k, v in dict(r).items()} for r in cur.fetchall()]

    def update_conversation_timestamp(self, conv_id: str):
        """Touch the updated_at timestamp on a conversation."""
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE liquidround.workflows SET updated_at = NOW() WHERE id = %s", (conv_id,))

    # ------------------------------------------------------------------
    # Pipeline items
    # ------------------------------------------------------------------
    def add_pipeline_item(self, user_id: str, pipeline_type: str, company_name: str,
                          stage: str, score: int = None, workflow_id: str = None,
                          metadata: dict = None) -> str:
        item_id = str(uuid.uuid4())
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.pipeline_items
                    (id, user_id, pipeline_type, company_name, stage, score, workflow_id, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (item_id, user_id, pipeline_type, company_name, stage, score,
                  workflow_id, json.dumps(metadata or {})))
        return item_id

    def get_pipeline_items(self, user_id: str, pipeline_type: str) -> List[Dict[str, Any]]:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT id, pipeline_type, company_name, stage, score, workflow_id, metadata, created_at, updated_at
                FROM liquidround.pipeline_items
                WHERE user_id = %s AND pipeline_type = %s
                ORDER BY updated_at DESC
            """, (user_id, pipeline_type))
            results = []
            for r in cur.fetchall():
                d = dict(r)
                d["id"] = str(d["id"])
                if d.get("workflow_id"): d["workflow_id"] = str(d["workflow_id"])
                if isinstance(d.get("metadata"), str):
                    try: d["metadata"] = json.loads(d["metadata"])
                    except: pass
                d["created_at"] = str(d["created_at"])
                d["updated_at"] = str(d["updated_at"])
                results.append(d)
            return results

    def move_pipeline_item(self, item_id: str, user_id: str, new_stage: str):
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE liquidround.pipeline_items
                SET stage = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
            """, (new_stage, item_id, user_id))

    def delete_pipeline_item(self, item_id: str, user_id: str):
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM liquidround.pipeline_items WHERE id = %s AND user_id = %s", (item_id, user_id))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        return self.get_workflow_summary(workflow_id)

    def get_workflow_summary(self, workflow_id: str) -> Dict[str, Any]:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {}
        results = self.get_workflow_results(workflow_id)
        messages = self.get_messages(workflow_id)
        return {
            "workflow": workflow,
            "results": results,
            "messages": messages,
            "agent_count": len(results),
            "message_count": len(messages),
        }

    # ------------------------------------------------------------------
    # Scoring results (new)
    # ------------------------------------------------------------------
    def save_scoring_result(self, workflow_id: str, score_data: dict):
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.scoring_results
                    (workflow_id, buyer, target, composite_score, dimensions, recommendation, key_risks, next_steps)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                workflow_id,
                score_data.get("buyer", ""),
                score_data.get("target", ""),
                score_data.get("composite_score", 0),
                json.dumps(score_data.get("dimensions", {})),
                score_data.get("recommendation", ""),
                json.dumps(score_data.get("key_risks", [])),
                json.dumps(score_data.get("next_steps", [])),
            ))

    # ------------------------------------------------------------------
    # Research results (new)
    # ------------------------------------------------------------------
    def save_research_result(self, workflow_id: str, research_data: dict):
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.research_results
                    (workflow_id, query, exa_results, tavily_results, thinking_trace, summary)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                workflow_id,
                research_data.get("query", ""),
                json.dumps(research_data.get("exa", {})),
                json.dumps(research_data.get("tavily", {})),
                json.dumps(research_data.get("thinking_trace", [])),
                research_data.get("summary", ""),
            ))

    # ------------------------------------------------------------------
    # Documents (new)
    # ------------------------------------------------------------------
    def save_document(self, filename: str, file_type: str, file_size: int,
                      file_path: str, parsed_data: dict, deal_id: str = None) -> str:
        doc_id = str(uuid.uuid4())
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.documents (id, filename, file_type, file_size, file_path, parsed_data, deal_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (doc_id, filename, file_type, file_size, file_path, json.dumps(parsed_data, default=str), deal_id))
        return doc_id

    # ------------------------------------------------------------------
    # IPO data
    # ------------------------------------------------------------------
    def insert_ipo_data(self, ipo_records: List[Dict]) -> int:
        if not ipo_records:
            return 0
        count = 0
        with get_conn() as conn:
            cur = conn.cursor()
            for rec in ipo_records:
                try:
                    cur.execute("""
                        INSERT INTO liquidround.ipo_data
                            (ticker, company_name, sector, industry, exchange, ipo_date,
                             ipo_price, current_price, market_cap, price_change_since_ipo,
                             volume, last_updated)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (ticker) DO UPDATE SET
                            current_price = EXCLUDED.current_price,
                            market_cap = EXCLUDED.market_cap,
                            price_change_since_ipo = EXCLUDED.price_change_since_ipo,
                            volume = EXCLUDED.volume,
                            last_updated = EXCLUDED.last_updated
                    """, (
                        rec["ticker"], rec["company_name"], rec["sector"], rec["industry"],
                        rec["exchange"], rec["ipo_date"], rec["ipo_price"], rec["current_price"],
                        rec["market_cap"], rec["price_change_since_ipo"], rec["volume"], rec["last_updated"],
                    ))
                    count += 1
                except Exception as e:
                    logger.error(f"IPO insert error ({rec.get('ticker')}): {e}")
        logger.info(f"Upserted {count} IPO records")
        return count

    def get_ipo_data(self, year: int = None, exchange: str = None,
                     sector: str = None, limit: int = None):
        import pandas as pd
        query = "SELECT * FROM liquidround.ipo_data WHERE 1=1"
        params = []
        if year:
            query += " AND EXTRACT(YEAR FROM ipo_date) = %s"
            params.append(year)
        if exchange:
            query += " AND exchange = %s"
            params.append(exchange)
        if sector:
            query += " AND sector = %s"
            params.append(sector)
        query += " ORDER BY market_cap DESC"
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        with get_conn() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        return df

    def log_ipo_refresh(self, refresh_type: str, status: str, records_processed: int = 0,
                        error_message: str = None, started_at: str = None) -> int:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO liquidround.ipo_refresh_log
                    (refresh_type, status, records_processed, error_message, started_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (refresh_type, status, records_processed, error_message, started_at or datetime.now().isoformat()))
            return cur.fetchone()[0]

    def get_last_ipo_refresh(self) -> Optional[Dict]:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM liquidround.ipo_refresh_log
                ORDER BY completed_at DESC LIMIT 1
            """)
            row = cur.fetchone()
            return dict(row) if row else None


# Global database instance
db_service = DatabaseService()
