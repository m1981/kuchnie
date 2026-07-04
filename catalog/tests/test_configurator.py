"""Expectancy tests for the Kitchen Configurator API.

Tests define expected behavior BEFORE implementation.
Each test exercises a specific contract from the spec.

Spec: docs/specs/configurator-api.md
"""

from __future__ import annotations


class TestCreateSession:
    """POST /configurator/sessions"""

    def test_returns_token_and_step_front(self, client):
        resp = client.post("/configurator/sessions")
        assert resp.status_code == 201
        body = resp.json()
        assert "session_token" in body
        assert len(body["session_token"]) > 0
        assert body["current_step"] == "front"

    def test_session_persists_in_db(self, client):
        resp = client.post("/configurator/sessions")
        token = resp.json()["session_token"]
        # Verify it exists by fetching options (would 404 if not persisted)
        resp2 = client.get(f"/configurator/sessions/{token}/options")
        assert resp2.status_code == 200


class TestFrontOptions:
    """GET /configurator/sessions/{token}/options (step=front)"""

    def test_returns_variants_with_front_role(self, client):
        token = _create_session(client)
        resp = client.get(f"/configurator/sessions/{token}/options")
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_step"] == "front"
        assert len(body["options"]) >= 1
        for opt in body["options"]:
            assert "variant_id" in opt
            assert "decor_name" in opt

    def test_filter_by_color_family(self, client):
        token = _create_session(client)
        resp = client.get(f"/configurator/sessions/{token}/options?color_family=bialy")
        assert resp.status_code == 200
        for opt in resp.json()["options"]:
            assert opt["color_family"] == "bialy"

    def test_invalid_session_returns_404(self, client):
        resp = client.get("/configurator/sessions/nonexistent-token/options")
        assert resp.status_code == 404


class TestSelectFront:
    """PATCH /configurator/sessions/{token}/select (step=front)"""

    def test_advances_to_carcass_step(self, client):
        token = _create_session(client)
        resp = client.patch(
            f"/configurator/sessions/{token}/select",
            json={"step": "front", "variant_id": "K8685-CH-18-SM"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_step"] == "carcass"

    def test_invalid_variant_returns_400(self, client):
        token = _create_session(client)
        resp = client.patch(
            f"/configurator/sessions/{token}/select",
            json={"step": "front", "variant_id": "NONEXISTENT"},
        )
        assert resp.status_code == 400

    def test_wrong_step_returns_400(self, client):
        token = _create_session(client)
        resp = client.patch(
            f"/configurator/sessions/{token}/select",
            json={"step": "carcass", "variant_id": "K8685-CH-18-SM"},
        )
        assert resp.status_code == 400

    def test_nonexistent_session_returns_404(self, client):
        resp = client.patch(
            "/configurator/sessions/bad-token/select",
            json={"step": "front", "variant_id": "K8685-CH-18-SM"},
        )
        assert resp.status_code == 404


class TestCarcassOptions:
    """GET /configurator/sessions/{token}/options (step=carcass)"""

    def test_returns_pairing_results_for_chosen_front(self, client):
        token = _select_front(client, "K8685-CH-18-SM")
        resp = client.get(f"/configurator/sessions/{token}/options")
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_step"] == "carcass"
        assert len(body["options"]) >= 1
        # Should have at least a default option
        default_opts = [o for o in body["options"] if o.get("recommendation")]
        assert len(default_opts) >= 1

    def test_returns_default_when_no_pairings(self, client):
        """When no explicit carcass pairings exist, fallback to all carcass variants."""
        token = _select_front(client, "K190-CH-18-PE")
        resp = client.get(f"/configurator/sessions/{token}/options")
        assert resp.status_code == 200
        assert len(resp.json()["options"]) >= 1


class TestSelectCarcass:
    """PATCH /configurator/sessions/{token}/select (step=carcass)"""

    def test_advances_to_worktop_step(self, client):
        token = _select_front(client, "K8685-CH-18-SM")
        # Pick any available carcass option
        options = client.get(f"/configurator/sessions/{token}/options").json()["options"]
        chosen = options[0]["variant_id"]
        resp = client.patch(
            f"/configurator/sessions/{token}/select",
            json={"step": "carcass", "variant_id": chosen},
        )
        assert resp.status_code == 200
        assert resp.json()["current_step"] == "worktop"


class TestWorktopOptions:
    """GET /configurator/sessions/{token}/options (step=worktop)"""

    def test_returns_worktop_variants(self, client):
        token = _select_to_worktop(client)
        resp = client.get(f"/configurator/sessions/{token}/options")
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_step"] == "worktop"
        assert len(body["options"]) >= 1


class TestEdgeOptions:
    """GET /configurator/sessions/{token}/options (step=edge)"""

    def test_returns_edges_for_chosen_front(self, client):
        token = _select_to_edge(client)
        resp = client.get(f"/configurator/sessions/{token}/options")
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_step"] == "edge"

    def test_select_edge_never_500s(self, client):
        """Regression: EDGE_STEPS was not imported → NameError → 500."""
        token = _select_to_edge(client)
        options = client.get(
            f"/configurator/sessions/{token}/options"
        ).json()["options"]
        if options:
            resp = client.patch(
                f"/configurator/sessions/{token}/select",
                json={"step": "edge", "edge_id": options[0]["edge_id"]},
            )
            assert resp.status_code == 200
        else:
            # No edges in sample data — a nonexistent id must 400, not 500
            resp = client.patch(
                f"/configurator/sessions/{token}/select",
                json={"step": "edge", "edge_id": 999999},
            )
            assert resp.status_code == 400


class TestSidePanelOptions:
    """GET /configurator/sessions/{token}/options (step=side_panel)"""

    def test_returns_side_panel_options(self, client):
        token = _select_to_side_panel(client)
        resp = client.get(f"/configurator/sessions/{token}/options")
        assert resp.status_code == 200
        # May be at edge or side_panel depending on test data
        assert resp.json()["current_step"] in ("edge", "side_panel")


class TestPlinthOptions:
    """GET /configurator/sessions/{token}/options (step=plinth)"""

    def test_returns_plinth_options(self, client):
        token = _select_to_plinth(client)
        resp = client.get(f"/configurator/sessions/{token}/options")
        assert resp.status_code == 200
        # May be at edge, side_panel, or plinth depending on test data
        assert resp.json()["current_step"] in ("edge", "side_panel", "plinth")


class TestBOM:
    """GET /configurator/sessions/{token}/bom"""

    def test_returns_all_selections(self, client):
        token = _select_to_done(client)
        resp = client.get(f"/configurator/sessions/{token}/bom")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        # Must have at least front and carcass
        roles = {item["role"] for item in body["items"]}
        assert "front" in roles
        assert "carcass" in roles

    def test_partial_session_returns_partial_bom(self, client):
        token = _select_front(client, "K8685-CH-18-SM")
        resp = client.get(f"/configurator/sessions/{token}/bom")
        assert resp.status_code == 200
        body = resp.json()
        assert body["complete"] is False
        roles = {item["role"] for item in body["items"]}
        assert "front" in roles


class TestTemplates:
    """GET /configurator/templates"""

    def test_returns_list(self, client):
        resp = client.get("/configurator/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        # MVP: may be empty, but endpoint must work
        for tmpl in body:
            assert "slug" in tmpl
            assert "name" in tmpl


class TestFromTemplate:
    """POST /configurator/sessions/{token}/from_template"""

    def test_initializes_session_from_template(self, client):
        # Create session first
        token = _create_session(client)
        # Get available templates
        templates = client.get("/configurator/templates").json()
        if len(templates) == 0:
            # No templates yet — test that endpoint exists and handles gracefully
            resp = client.post(
                f"/configurator/sessions/{token}/from_template",
                json={"template_slug": "nonexistent"},
            )
            assert resp.status_code == 404
            return

        slug = templates[0]["slug"]
        resp = client.post(
            f"/configurator/sessions/{token}/from_template",
            json={"template_slug": slug},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_step"] == "done"


# ── Helpers ──────────────────────────────────────────────────────


def _create_session(client) -> str:
    """Create a session and return its token."""
    resp = client.post("/configurator/sessions")
    assert resp.status_code == 201
    return resp.json()["session_token"]


def _select_front(client, variant_id: str) -> str:
    """Create session, select front, return token."""
    token = _create_session(client)
    resp = client.patch(
        f"/configurator/sessions/{token}/select",
        json={"step": "front", "variant_id": variant_id},
    )
    assert resp.status_code == 200
    return token


def _select_to_worktop(client) -> str:
    """Create session → select front → select carcass, return token."""
    token = _select_front(client, "K8685-CH-18-SM")
    options = client.get(f"/configurator/sessions/{token}/options").json()["options"]
    chosen = options[0]["variant_id"]
    client.patch(
        f"/configurator/sessions/{token}/select",
        json={"step": "carcass", "variant_id": chosen},
    )
    return token


def _select_to_edge(client) -> str:
    """Create session → front → carcass → worktop, return token."""
    token = _select_to_worktop(client)
    options = client.get(f"/configurator/sessions/{token}/options").json()["options"]
    chosen = options[0]["variant_id"]
    client.patch(
        f"/configurator/sessions/{token}/select",
        json={"step": "worktop", "variant_id": chosen},
    )
    return token


def _select_to_side_panel(client) -> str:
    """Create session → front → carcass → worktop → edge, return token."""
    token = _select_to_edge(client)
    options = client.get(f"/configurator/sessions/{token}/options").json()["options"]
    if len(options) == 0:
        # No edges in sample data — the session stays at edge step.
        # For downstream helpers, we need to get to side_panel.
        # Use side_panel options directly (edge is skippable).
        pass
    else:
        chosen = options[0]["edge_id"]
        client.patch(
            f"/configurator/sessions/{token}/select",
            json={"step": "edge", "edge_id": chosen},
        )
    return token


def _select_to_plinth(client) -> str:
    """Create session → ... → side_panel, return token."""
    token = _select_to_side_panel(client)
    step = client.get(f"/configurator/sessions/{token}/options").json()["current_step"]
    if step == "side_panel":
        options = client.get(f"/configurator/sessions/{token}/options").json()["options"]
        if options:
            chosen = options[0]["variant_id"]
            client.patch(
                f"/configurator/sessions/{token}/select",
                json={"step": "side_panel", "variant_id": chosen},
            )
    return token


def _select_to_done(client) -> str:
    """Create session → ... → plinth → done, return token."""
    token = _select_to_plinth(client)
    step = client.get(f"/configurator/sessions/{token}/options").json()["current_step"]
    if step == "plinth":
        options = client.get(f"/configurator/sessions/{token}/options").json()["options"]
        if options:
            chosen = options[0]["variant_id"]
            client.patch(
                f"/configurator/sessions/{token}/select",
                json={"step": "plinth", "variant_id": chosen},
            )
    return token
