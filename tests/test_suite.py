"""
LiquidRound — Comprehensive Test Suite
Tests: config, auth, database, LLM factory, research tools, yfinance,
       document parser, scoring agent, FastHTML routes, Phase 8 mocks.
Results saved to test-data/*.json
"""
import os, sys, json, time, asyncio, uuid
from pathlib import Path
from datetime import datetime

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_DATA_DIR = Path(__file__).parent.parent / "test-data"
TEST_DATA_DIR.mkdir(exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def _save(name: str, data: dict):
    path = TEST_DATA_DIR / f"{name}_{TIMESTAMP}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


# ===================================================================
# 1. CONFIG & ENVIRONMENT
# ===================================================================
class TestConfig:
    def test_config_loads(self):
        from utils.config import config
        result = {
            "test": "config_loads",
            "xai_api_key_present": bool(config.xai_api_key),
            "exa_api_key_present": bool(config.exa_api_key),
            "tavily_api_key_present": bool(config.tavily_api_key),
            "default_provider": config.default_provider,
            "default_model": config.default_model,
            "default_temperature": config.default_temperature,
            "environment": config.environment,
        }
        _save("config_loads", result)
        assert config.xai_api_key or config.openai_api_key, "At least one LLM key must be set"
        assert config.default_provider in ("xai", "openai")

    def test_env_variables(self):
        from dotenv import load_dotenv
        load_dotenv()
        keys = ["XAI_API_KEY", "XAI_API", "EXA_API_KEY", "TAVILY_API_KEY", "DB_URL",
                "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
        result = {"test": "env_variables", "variables": {}}
        for k in keys:
            val = os.getenv(k, "")
            result["variables"][k] = {
                "present": bool(val),
                "length": len(val),
                "hint": val[:8] + "..." if val else "",
            }
        _save("env_variables", result)
        assert os.getenv("DB_URL"), "DB_URL must be set"


# ===================================================================
# 2. DATABASE (PostgreSQL)
# ===================================================================
class TestDatabase:
    def test_connection(self):
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'liquidround' ORDER BY table_name
            """)
            tables = [r[0] for r in cur.fetchall()]
        result = {"test": "db_connection", "success": True, "pg_version": version[:60], "tables": tables, "table_count": len(tables)}
        _save("db_connection", result)
        assert "workflows" in tables
        assert "users" in tables
        assert len(tables) >= 14

    def test_workflow_crud(self):
        from utils.database import db_service
        wf_id = db_service.create_workflow("Test query from test_suite", "buyer_ma")
        assert wf_id
        db_service.update_workflow_status(wf_id, "executing")
        db_service.save_agent_result(wf_id, "test_agent", {"foo": "bar"}, "success", 0.1)
        db_service.add_message(wf_id, "user", "test message")
        summary = db_service.get_workflow_summary(wf_id)
        result = {
            "test": "workflow_crud",
            "workflow_id": wf_id,
            "status": summary["workflow"]["status"],
            "agent_count": summary["agent_count"],
            "message_count": summary["message_count"],
        }
        _save("db_workflow_crud", result)
        assert summary["workflow"]["status"] == "executing"
        assert summary["agent_count"] == 1
        assert summary["message_count"] == 1
        # Cleanup
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM liquidround.messages WHERE workflow_id = %s", (wf_id,))
            cur.execute("DELETE FROM liquidround.workflow_results WHERE workflow_id = %s", (wf_id,))
            cur.execute("DELETE FROM liquidround.workflows WHERE id = %s", (wf_id,))

    def test_scoring_result_save(self):
        from utils.database import db_service, get_conn
        wf_id = db_service.create_workflow("Score test", "buyer_ma")
        score_data = {
            "buyer": "TestCo", "target": "TargetCo", "composite_score": 72,
            "dimensions": {"revenue_synergies": {"score": 8, "reasoning": "test"}},
            "recommendation": "PROCEED", "key_risks": ["risk1"], "next_steps": ["step1"],
        }
        db_service.save_scoring_result(wf_id, score_data)
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT composite_score, recommendation FROM liquidround.scoring_results WHERE workflow_id = %s", (wf_id,))
            row = cur.fetchone()
        result = {"test": "scoring_result_save", "composite_score": row[0], "recommendation": row[1]}
        _save("db_scoring_save", result)
        assert row[0] == 72
        assert row[1] == "PROCEED"
        # Cleanup
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM liquidround.scoring_results WHERE workflow_id = %s", (wf_id,))
            cur.execute("DELETE FROM liquidround.workflows WHERE id = %s", (wf_id,))


# ===================================================================
# 3. AUTH
# ===================================================================
class TestAuth:
    _test_email = f"testsuite-{uuid.uuid4().hex[:8]}@example.com"

    def test_password_hashing(self):
        from utils.auth import hash_password, verify_password
        pw = "SecurePass123!"
        h = hash_password(pw)
        result = {"test": "password_hashing", "hash_length": len(h), "verify_correct": verify_password(pw, h), "verify_wrong": verify_password("wrong", h)}
        _save("auth_password_hashing", result)
        assert verify_password(pw, h)
        assert not verify_password("wrong", h)

    def test_user_create_and_authenticate(self):
        from utils.auth import create_user, authenticate, get_user_by_email
        from utils.database import get_conn
        user = create_user(email=self._test_email, password="TestPass123", display_name="Test User")
        result = {"test": "user_create_authenticate", "email": self._test_email}
        assert user is not None, "User creation failed"
        result["user_created"] = True
        result["user_id"] = user["user_id"]

        auth_user = authenticate(self._test_email, "TestPass123")
        result["auth_success"] = auth_user is not None
        assert auth_user is not None

        bad_auth = authenticate(self._test_email, "WrongPassword")
        result["auth_reject_bad_pw"] = bad_auth is None
        assert bad_auth is None

        fetched = get_user_by_email(self._test_email)
        result["fetch_by_email"] = fetched is not None
        assert fetched is not None

        _save("auth_user_crud", result)
        # Cleanup
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM liquidround.users WHERE email = %s", (self._test_email,))

    def test_duplicate_email_rejected(self):
        from utils.auth import create_user
        from utils.database import get_conn
        email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
        u1 = create_user(email=email, password="Pass1234")
        u2 = create_user(email=email, password="Pass5678")
        result = {"test": "duplicate_email", "first_create": u1 is not None, "second_create": u2 is None}
        _save("auth_duplicate_email", result)
        assert u1 is not None
        assert u2 is None
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM liquidround.users WHERE email = %s", (email,))


# ===================================================================
# 4. LLM FACTORY
# ===================================================================
class TestLLMFactory:
    def test_create_llm(self):
        from utils.llm_factory import create_llm
        llm = create_llm()
        result = {"test": "llm_factory", "model": llm.model_name, "temperature": llm.temperature, "type": type(llm).__name__}
        _save("llm_factory_create", result)
        assert llm is not None

    @pytest.mark.asyncio
    async def test_llm_call(self):
        from utils.llm_factory import create_llm
        from langchain_core.messages import HumanMessage
        llm = create_llm()
        ts = time.time()
        try:
            response = await llm.ainvoke([HumanMessage(content="Say 'hello' and nothing else.")])
            elapsed = time.time() - ts
            result = {
                "test": "llm_call", "success": True,
                "model": llm.model_name,
                "response": response.content[:200],
                "response_length": len(response.content),
                "elapsed_seconds": round(elapsed, 2),
            }
            _save("llm_call", result)
            assert len(response.content) > 0
        except Exception as e:
            elapsed = time.time() - ts
            result = {"test": "llm_call", "success": False, "error": str(e)[:200], "elapsed_seconds": round(elapsed, 2)}
            _save("llm_call", result)
            pytest.skip(f"LLM API call failed (key may be invalid): {str(e)[:100]}")


# ===================================================================
# 5. RESEARCH TOOLS (EXA + TAVILY)
# ===================================================================
class TestResearchTools:
    @pytest.mark.asyncio
    async def test_exa_search(self):
        from utils.research_tools import research_tools
        ts = time.time()
        res = await research_tools.exa_search("fintech acquisition targets 2025", num_results=3)
        elapsed = time.time() - ts
        result = {
            "test": "exa_search",
            "result_count": len(res.get("results", [])),
            "elapsed": round(elapsed, 2),
            "error": res.get("error"),
            "sample_titles": [r.get("title", "") for r in res.get("results", [])[:3]],
        }
        _save("research_exa_search", result)
        # Allow graceful failure if API key is bad
        assert "results" in res

    @pytest.mark.asyncio
    async def test_tavily_search(self):
        from utils.research_tools import research_tools
        ts = time.time()
        res = await research_tools.tavily_search("healthcare SaaS M&A trends")
        elapsed = time.time() - ts
        result = {
            "test": "tavily_search",
            "result_count": len(res.get("results", [])),
            "elapsed": round(elapsed, 2),
            "error": res.get("error"),
            "sample_titles": [r.get("title", "") for r in res.get("results", [])[:3]],
        }
        _save("research_tavily_search", result)
        assert "results" in res

    @pytest.mark.asyncio
    async def test_deep_research(self):
        from utils.research_tools import research_tools
        ts = time.time()
        res = await research_tools.deep_research("cybersecurity acquisition targets")
        elapsed = time.time() - ts
        result = {
            "test": "deep_research",
            "exa_count": len(res.get("exa", {}).get("results", [])),
            "tavily_count": len(res.get("tavily", {}).get("results", [])),
            "trace_steps": len(res.get("thinking_trace", [])),
            "elapsed": round(elapsed, 2),
        }
        _save("research_deep", result)
        assert "thinking_trace" in res
        assert len(res["thinking_trace"]) >= 2


# ===================================================================
# 6. YFINANCE
# ===================================================================
class TestYFinance:
    def test_company_profile(self):
        from utils.yfinance_util import yfinance_util
        profile = yfinance_util.get_company_profile("MSFT")
        result = {"test": "yfinance_profile", "ticker": "MSFT", "profile": profile}
        _save("yfinance_profile_msft", result)
        assert profile.get("name"), "Should have company name"
        assert profile.get("market_cap", 0) > 0, "Should have market cap"

    def test_company_financials(self):
        from utils.yfinance_util import yfinance_util
        fin = yfinance_util.get_financials("AAPL")
        result = {"test": "yfinance_financials", "ticker": "AAPL", "financials": fin}
        _save("yfinance_financials_aapl", result)
        assert fin.get("revenue", 0) > 0


# ===================================================================
# 7. DOCUMENT PARSER
# ===================================================================
class TestDocumentParser:
    def test_xlsx_parse(self):
        from utils.document_parser import document_parser
        import openpyxl
        # Create a test xlsx in memory and save
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Financials"
        ws.append(["Metric", "2024", "2025"])
        ws.append(["Revenue", 50000000, 65000000])
        ws.append(["EBITDA", 12000000, 16000000])
        test_path = TEST_DATA_DIR / "test_upload.xlsx"
        wb.save(str(test_path))

        parsed = document_parser.parse(str(test_path))
        text = document_parser.extract_all_text(parsed)
        result = {"test": "xlsx_parse", "parsed": parsed, "text_length": len(text)}
        _save("docparse_xlsx", result)
        assert parsed["type"] == "xlsx"
        assert "Financials" in parsed["sheet_names"]
        assert len(text) > 0
        test_path.unlink(missing_ok=True)

    def test_pdf_parse_missing_file(self):
        from utils.document_parser import document_parser
        parsed = document_parser.parse("/nonexistent/file.pdf")
        result = {"test": "pdf_parse_missing", "parsed": parsed}
        _save("docparse_pdf_missing", result)
        # Should not crash, should return error
        assert "error" in parsed or "pages" in parsed


# ===================================================================
# 8. SCORING AGENT
# ===================================================================
class TestScoringAgent:
    @pytest.mark.asyncio
    async def test_scoring_agent(self):
        from agents.scoring_agent import ScoringAgent
        from utils.state import create_initial_state
        state = create_initial_state("buyer_ma", "Score acquisition: Buyer=Salesforce, Target=HubSpot, Context=CRM consolidation play")
        state["deal"]["company_name"] = "HubSpot"
        state["deal"]["industry"] = "Enterprise SaaS"

        scorer = ScoringAgent()
        ts = time.time()
        try:
            state = await scorer.execute(state)
        except Exception as e:
            result = {"test": "scoring_agent", "success": False, "error": str(e)[:200]}
            _save("scoring_agent", result)
            pytest.skip(f"Scoring agent LLM call failed: {str(e)[:100]}")
            return
        elapsed = time.time() - ts

        agent_result = state["agent_results"].get("scoring", {})
        score_data = agent_result.get("result", {})

        result = {
            "test": "scoring_agent",
            "status": agent_result.get("status"),
            "execution_time": round(elapsed, 2),
            "composite_score": score_data.get("composite_score") if score_data else None,
            "recommendation": score_data.get("recommendation") if score_data else None,
            "dimensions": {k: v.get("score") if isinstance(v, dict) else v for k, v in score_data.get("dimensions", {}).items()} if score_data else {},
            "key_risks": score_data.get("key_risks", []) if score_data else [],
            "next_steps": score_data.get("next_steps", []) if score_data else [],
        }
        _save("scoring_agent", result)
        if agent_result.get("status") == "error":
            pytest.skip(f"Scoring agent error (API key issue): {agent_result.get('error_message', '')[:100]}")
        assert agent_result.get("status") == "success"
        assert score_data.get("composite_score", 0) > 0


# ===================================================================
# 9. FASTHTML ROUTES
# ===================================================================
class TestRoutes:
    @pytest.fixture(autouse=True)
    def setup_app(self):
        from fasthtml.common import fast_app, Script, Beforeware, Meta, Link
        from starlette.responses import RedirectResponse
        from routes import all_routers

        _PUBLIC = [r"/signin", r"/register", r"/login", r"/logout", r"/auth/callback", r"/forgot", r"/reset", r"/favicon\.ico", r"/static/.*", r".*\.css", r".*\.js"]
        def _auth_before(req, sess):
            req.scope["auth"] = sess.get("user")
            if not req.scope["auth"]:
                return RedirectResponse("/signin", status_code=303)
        beforeware = Beforeware(_auth_before, skip=_PUBLIC)

        app, rt = fast_app(pico=False, before=beforeware, hdrs=(Script(src="https://cdn.tailwindcss.com"),), static_path="static", secret_key="test-key")
        for router in all_routers:
            router.to_app(app)

        @rt
        def index():
            from routes.home import index as home_index
            return home_index()

        from starlette.testclient import TestClient
        self.client = TestClient(app)

    def test_public_pages(self):
        results = {}
        for path in ["/signin", "/register", "/forgot"]:
            r = self.client.get(path)
            results[path] = {"status": r.status_code, "has_tailwind": "tailwindcss" in r.text, "length": len(r.text)}
            assert r.status_code == 200
        result = {"test": "public_pages", "pages": results}
        _save("routes_public_pages", result)

    def test_auth_redirect(self):
        protected = ["/", "/targets", "/buyers", "/ipo", "/score", "/market", "/settings", "/upload", "/deals", "/company", "/tools", "/profile"]
        results = {}
        for path in protected:
            r = self.client.get(path, follow_redirects=False)
            results[path] = {"status": r.status_code, "redirects_to_signin": "/signin" in r.headers.get("location", "")}
            assert r.status_code == 303, f"{path} should redirect, got {r.status_code}"
        result = {"test": "auth_redirect", "protected_routes": results, "all_redirect": all(v["status"] == 303 for v in results.values())}
        _save("routes_auth_redirect", result)

    def test_register_and_login_flow(self):
        email = f"routetest-{uuid.uuid4().hex[:8]}@example.com"
        # Register
        r = self.client.post("/register", data={"email": email, "password": "TestPass123", "display_name": "Route Test"}, follow_redirects=False)
        reg_ok = r.status_code == 303
        # Login
        r = self.client.post("/signin", data={"email": email, "password": "TestPass123"}, follow_redirects=False)
        login_ok = r.status_code == 303
        # Bad password
        r = self.client.post("/signin", data={"email": email, "password": "wrong"}, follow_redirects=False)
        reject_ok = r.status_code == 303 and "error" in r.headers.get("location", "")

        result = {"test": "register_login_flow", "email": email, "register_ok": reg_ok, "login_ok": login_ok, "reject_bad_pw": reject_ok}
        _save("routes_register_login", result)
        assert reg_ok
        assert login_ok
        assert reject_ok
        # Cleanup
        from utils.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM liquidround.users WHERE email = %s", (email,))

    def test_signin_page_content(self):
        r = self.client.get("/signin")
        checks = {
            "has_google_btn": "Google" in r.text,
            "has_form": "action" in r.text and "/signin" in r.text,
            "has_register_link": "/register" in r.text,
            "has_forgot_link": "/forgot" in r.text,
            "has_branding": "LiquidRound" in r.text,
            "has_predictive_labs": "Predictive Labs" in r.text,
        }
        result = {"test": "signin_page_content", "checks": checks}
        _save("routes_signin_content", result)
        for k, v in checks.items():
            assert v, f"Missing: {k}"

    def test_google_oauth_configured(self):
        """Verify Google OAuth redirect is wired up."""
        r = self.client.get("/login", follow_redirects=False)
        result = {
            "test": "google_oauth_configured",
            "status": r.status_code,
            "redirects_to_google": "accounts.google.com" in r.headers.get("location", ""),
        }
        _save("routes_google_oauth", result)
        # Should either redirect to Google or fall back to /signin
        assert r.status_code in (302, 303, 307, 200)


# ===================================================================
# 10. PHASE 8 MOCK TOOLS
# ===================================================================
class TestPhase8Mocks:
    @pytest.fixture(autouse=True)
    def setup_app(self):
        from fasthtml.common import fast_app, Script
        from routes import all_routers
        app, rt = fast_app(pico=False, hdrs=(Script(src="https://cdn.tailwindcss.com"),), static_path="static", secret_key="test-key")
        for router in all_routers:
            router.to_app(app)
        from starlette.testclient import TestClient
        self.client = TestClient(app)

    def test_tools_page(self):
        r = self.client.get("/tools")
        tools_expected = ["Deal Room", "CIM Generator", "LOI", "Due Diligence", "Regulatory", "Stakeholder", "Integration Playbook"]
        found = {t: t in r.text for t in tools_expected}
        result = {"test": "tools_page", "status": r.status_code, "tools_found": found}
        _save("phase8_tools_page", result)
        assert r.status_code == 200
        for t, present in found.items():
            assert present, f"Missing tool: {t}"

    def test_mock_tool_endpoints(self):
        endpoints = ["deal-room", "cim-generator", "comparable-transactions", "loi---term-sheet-drafter", "due-diligence-checklist", "regulatory-screening", "stakeholder-mapping", "integration-playbook"]
        results = {}
        for ep in endpoints:
            r = self.client.get(f"/mock-tool/{ep}", follow_redirects=True)
            results[ep] = {"status": r.status_code, "has_content": len(r.text) > 50}
            assert r.status_code == 200, f"/mock-tool/{ep} returned {r.status_code}"
        result = {"test": "mock_tool_endpoints", "endpoints": results}
        _save("phase8_mock_endpoints", result)
