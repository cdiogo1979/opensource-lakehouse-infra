"""Behavioral source tests for Hub token ownership and refresh coordination."""

import asyncio
import base64
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from tornado.testing import AsyncHTTPTestCase

from infra.jupyter.hub import lakehouse_token_broker as broker_module


def make_jwt(expiry: int) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"exp": expiry}).encode()).decode().rstrip("=")
    return f"e30.{payload}.signature"


class FakeAuthStateUser:
    def __init__(self, name, state):
        self.name = name
        self.state = state
        self.spawners = {"": SimpleNamespace(active=True, api_token="server-token")}
        self.get_auth_state = AsyncMock(side_effect=self.read_state)
        self.save_auth_state = AsyncMock(side_effect=self.write_state)

    async def read_state(self):
        return dict(self.state)

    async def write_state(self, state):
        self.state = dict(state)


class FakeTokenRecord:
    def __init__(self, user):
        self.user = user

    @staticmethod
    def match(token):
        return token == "server-token"


class FakeHttpResponse:
    def __init__(self, payload):
        self.code = 200
        self.body = json.dumps(payload).encode()
        self.headers = {"Content-Type": "application/json"}


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def fetch(self, request, **_kwargs):
        self.requests.append(request)
        if isinstance(self.responses[0], BaseException):
            raise self.responses.pop(0)
        response = self.responses.pop(0)
        if request.streaming_callback is not None:
            request.streaming_callback(response.body)
        return SimpleNamespace(code=response.code, body=None, headers=response.headers)


def setup_hub(state):
    user = FakeAuthStateUser("user-subject", state)
    hub = SimpleNamespace(
        db=object(),
        users={user.name: user},
        authenticator=SimpleNamespace(
            client_id="jupyterhub",
            client_secret="client-secret",
            basic_auth=False,
            token_url="http://keycloak:8080/realms/lakehouse/protocol/openid-connect/token",
            userdata_url="http://keycloak:8080/realms/lakehouse/protocol/openid-connect/userinfo",
            username_claim="sub",
            normalize_username=lambda value: value,
        ),
    )
    return hub, user, FakeTokenRecord(user)


class TokenBindingTests(unittest.IsolatedAsyncioTestCase):
    async def test_reuse_is_bound_to_exact_active_server_and_current_admission(self):
        hub, user, token_record = setup_hub(
            {"access_token": make_jwt(5000), "oauth_user": {"groups": ["role-default-developer"]}}
        )
        broker = broker_module.LakehouseTokenBroker(hub, clock=lambda: 1000)
        with patch.object(broker_module.orm.APIToken, "find", return_value=token_record) as lookup:
            token, expiry, username, server, decision = await broker.issue_for_server_token("server-token")
        lookup.assert_called_once_with(hub.db, "server-token", kind="user")
        self.assertEqual((expiry, username, server, decision), (5000, "user-subject", "default", "reused"))
        self.assertEqual(token, user.state["access_token"])

    async def test_invalid_token_and_stopped_server_are_denied(self):
        hub, _user, _record = setup_hub({})
        broker = broker_module.LakehouseTokenBroker(hub)
        with patch.object(broker_module.orm.APIToken, "find", return_value=None):
            with self.assertRaises(broker_module.BrokerError) as raised:
                await broker.issue_for_server_token("invalid-token")
        self.assertEqual(raised.exception.status, 401)

        _hub, user, record = setup_hub({})
        user.spawners[""].active = False
        stopped_broker = broker_module.LakehouseTokenBroker(_hub)
        with patch.object(broker_module.orm.APIToken, "find", return_value=record):
            with self.assertRaises(broker_module.BrokerError):
                await stopped_broker.issue_for_server_token("server-token")

    async def test_token_record_must_match_the_active_server_token(self):
        hub, _user, record = setup_hub({})
        broker = broker_module.LakehouseTokenBroker(hub)
        with patch.object(broker_module.orm.APIToken, "find", return_value=record):
            with self.assertRaises(broker_module.BrokerError) as raised:
                await broker.issue_for_server_token("another-users-token")
        self.assertEqual(raised.exception.status, 401)

    async def test_ineligible_auth_state_fails_closed(self):
        hub, _user, record = setup_hub(
            {"access_token": make_jwt(5000), "oauth_user": {"groups": ["role-default-owner"]}}
        )
        broker = broker_module.LakehouseTokenBroker(hub, clock=lambda: 1000)
        with patch.object(broker_module.orm.APIToken, "find", return_value=record):
            with self.assertRaises(broker_module.BrokerError) as raised:
                await broker.issue_for_server_token("server-token")
        self.assertEqual(raised.exception.code, "current_admission_denied")


class RefreshCoordinationTests(unittest.IsolatedAsyncioTestCase):
    async def test_different_users_are_not_serialized_on_one_lock(self):
        hub, _user, _record = setup_hub({})
        broker = broker_module.LakehouseTokenBroker(hub)
        other_entered = asyncio.Event()

        async with broker._user_lock("user-one"):
            async def enter_other_user():
                async with broker._user_lock("user-two"):
                    other_entered.set()

            await asyncio.wait_for(asyncio.create_task(enter_other_user()), timeout=0.2)
        self.assertTrue(other_entered.is_set())

    async def test_same_user_concurrent_refresh_is_single_flight_and_persisted(self):
        hub, user, record = setup_hub(
            {
                "access_token": make_jwt(1050),
                "refresh_token": "refresh-secret",
                "oauth_user": {"groups": ["role-default-developer"]},
            }
        )
        http = FakeHttpClient(
            [
                FakeHttpResponse(
                    {"access_token": make_jwt(2000), "refresh_token": "rotated-secret", "token_type": "Bearer"}
                ),
                FakeHttpResponse({"sub": "user-subject", "groups": ["role-default-developer"]}),
            ]
        )
        broker = broker_module.LakehouseTokenBroker(hub, http_client=http, clock=lambda: 1000)
        with patch.object(broker_module.orm.APIToken, "find", return_value=record):
            first, second = await asyncio.gather(
                broker.issue_for_server_token("server-token"),
                broker.issue_for_server_token("server-token"),
            )
        self.assertEqual(len(http.requests), 2)  # one refresh plus one membership check
        self.assertEqual(first[0], second[0])
        self.assertEqual(first[4], "refreshed")
        self.assertEqual(second[4], "reused")
        self.assertEqual(user.state["refresh_token"], "rotated-secret")
        self.assertNotIn("_lakehouse_broker_refresh_incomplete", user.state)

    async def test_refresh_timeout_is_not_replayed_and_fails_closed(self):
        hub, _user, record = setup_hub(
            {
                "access_token": make_jwt(1050),
                "refresh_token": "refresh-secret",
                "oauth_user": {"groups": ["role-default-developer"]},
            }
        )
        http = FakeHttpClient([TimeoutError("simulated ambiguous timeout")])
        broker = broker_module.LakehouseTokenBroker(hub, http_client=http, clock=lambda: 1000)
        with patch.object(broker_module.orm.APIToken, "find", return_value=record):
            with self.assertRaises(broker_module.BrokerError) as raised:
                await broker.issue_for_server_token("server-token")
        self.assertEqual(len(http.requests), 1)
        self.assertEqual(raised.exception.code, "reauthentication_required")

    async def test_ambiguous_timeout_with_persisted_incomplete_rotation_fails_closed(self):
        hub, user, record = setup_hub(
            {
                "access_token": make_jwt(1050),
                "refresh_token": "refresh-secret",
                "oauth_user": {"groups": ["role-default-developer"]},
            }
        )

        class RotatingThenTimeoutClient(FakeHttpClient):
            async def fetch(self, request, **_kwargs):
                self.requests.append(request)
                user.state.update(
                    {
                        "access_token": make_jwt(3000),
                        "refresh_token": "rotated-secret",
                        "_lakehouse_broker_refresh_incomplete": True,
                    }
                )
                raise TimeoutError("response lost after token rotation")

        http = RotatingThenTimeoutClient([])
        broker = broker_module.LakehouseTokenBroker(hub, http_client=http, clock=lambda: 1000)
        with patch.object(broker_module.orm.APIToken, "find", return_value=record):
            with self.assertRaises(broker_module.BrokerError) as raised:
                await broker.issue_for_server_token("server-token")
        self.assertEqual(len(http.requests), 1)
        self.assertEqual(user.state["refresh_token"], "rotated-secret")
        self.assertEqual(raised.exception.code, "reauthentication_required")


class BrokerHandlerTests(AsyncHTTPTestCase):
    def get_app(self):
        self.hub, self.user, self.record = setup_hub(
            {"access_token": make_jwt(5000), "oauth_user": {"groups": ["role-default-developer"]}}
        )
        self.broker = broker_module.LakehouseTokenBroker(self.hub, clock=lambda: 1000)
        return broker_module.broker_application(self.broker)

    def test_caller_identity_fields_do_not_change_hub_derived_identity(self):
        with patch.object(broker_module.orm.APIToken, "find", return_value=self.record):
            response = self.fetch(
                "/api/v1/token",
                method="POST",
                headers={"Authorization": "Bearer server-token", "Content-Type": "application/json"},
                body=json.dumps({"username": "somebody-else", "groups": ["role-default-owner"]}),
            )
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.body)["access_token"], self.user.state["access_token"])

    def test_invalid_server_token_response_is_safe_and_correlated(self):
        with patch.object(broker_module.orm.APIToken, "find", return_value=None):
            response = self.fetch(
                "/api/v1/token",
                method="POST",
                headers={"Authorization": "Bearer private-token", "Content-Type": "application/json"},
                body="{}",
            )
        body = json.loads(response.body)
        self.assertEqual(response.code, 401)
        self.assertIn("correlation_id", body)
        self.assertNotIn("private-token", response.body.decode())
        self.assertNotIn("access_token", body)


if __name__ == "__main__":
    unittest.main()
