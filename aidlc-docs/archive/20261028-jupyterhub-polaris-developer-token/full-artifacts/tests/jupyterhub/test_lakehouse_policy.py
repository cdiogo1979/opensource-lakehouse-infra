"""Unit tests for fail-closed Hub group admission and persistent homes."""

import unittest
from unittest.mock import AsyncMock

from infra.jupyter.hub.lakehouse_policy import (
    DEFAULT_CPU_LIMIT,
    DEFAULT_MEMORY_LIMIT,
    MAX_ACTIVE_SERVERS,
    eligible_group_names,
    attach_data_network,
    cleanup_partial_server,
    persistent_home_volume,
)


class AdmissionTests(unittest.TestCase):
    def test_developer_and_analyst_are_admitted(self):
        self.assertEqual(eligible_group_names(["role-default-developer"]), {"role-default-developer"})
        self.assertEqual(eligible_group_names(["role-default-analyst"]), {"role-default-analyst"})

    def test_both_approved_groups_are_preserved(self):
        self.assertEqual(
            eligible_group_names(["role-default-developer", "role-default-analyst"]),
            {"role-default-developer", "role-default-analyst"},
        )

    def test_unapproved_missing_and_malformed_claims_fail_closed(self):
        for claim in (["role-default-owner"], ["role-default-writer"], None, "role-default-developer", [1]):
            with self.subTest(claim=claim):
                self.assertEqual(eligible_group_names(claim), set())


class HomeAndCapacityTests(unittest.TestCase):
    def test_home_name_is_stable_private_and_subject_specific(self):
        first = persistent_home_volume("keycloak-subject-1")
        self.assertEqual(first, persistent_home_volume("keycloak-subject-1"))
        self.assertNotEqual(first, persistent_home_volume("keycloak-subject-2"))
        self.assertNotIn("keycloak-subject-1", first)

    def test_capacity_defaults_match_approved_profile(self):
        self.assertEqual(MAX_ACTIVE_SERVERS, 2)
        self.assertEqual(DEFAULT_CPU_LIMIT, 1.0)
        self.assertEqual(DEFAULT_MEMORY_LIMIT, "2G")


class SpawnLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_data_network_is_attached_before_helper_returns(self):
        docker_call = AsyncMock()
        await attach_data_network(docker_call, "container-id", "data-access")
        docker_call.assert_awaited_once_with(
            "connect_container_to_network", "container-id", "data-access"
        )

    async def test_network_failure_triggers_partial_server_cleanup(self):
        stop = AsyncMock()
        self.assertTrue(await cleanup_partial_server(stop))
        stop.assert_awaited_once_with(now=True)

    async def test_cleanup_failure_is_reported_without_deleting_home(self):
        stop = AsyncMock(side_effect=RuntimeError("container API failure"))
        self.assertFalse(await cleanup_partial_server(stop))
        self.assertTrue(persistent_home_volume("stable-subject").startswith("lakehouse-jupyter-home-"))


if __name__ == "__main__":
    unittest.main()
