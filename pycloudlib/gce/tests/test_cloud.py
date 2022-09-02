"""Tests related to pycloudlib.gce.cloud module."""
from io import StringIO
from textwrap import dedent

import mock
import pytest

from pycloudlib.cloud import ImageType
from pycloudlib.gce.cloud import GCE

# mock module path
MPATH = "pycloudlib.gce.cloud."


class TestGCE:
    @pytest.mark.parametrize(
        "release, arch, api_side_effects, expected_filter_calls, expected_image_list",
        [
            ("xenial", "arm64", Exception(), [], []),
            (
                "xenial",
                "x86_64",
                [{"items": [1, 2, 3]}, Exception()],
                [
                    mock.call(
                        project="project-name",
                        filter="name=name-filter",
                        maxResults=500,
                        pageToken="",
                    )
                ],
                [1, 2, 3],
            ),
            (
                "kinetic",
                "arm64",
                [
                    {"items": [1, 2, 3], "nextPageToken": "something"},
                    {"items": [4, 5, 6]},
                    Exception(),
                ],
                [
                    mock.call(
                        project="project-name",
                        filter="(name=name-filter) AND (architecture=ARM64)",
                        maxResults=500,
                        pageToken="",
                    ),
                    mock.call(
                        project="project-name",
                        filter="(name=name-filter) AND (architecture=ARM64)",
                        maxResults=500,
                        pageToken="something",
                    ),
                ],
                [1, 2, 3, 4, 5, 6],
            ),
        ],
    )
    def test_query_image_list(
        self,
        release,
        arch,
        api_side_effects,
        expected_filter_calls,
        expected_image_list,
    ):
        gce = GCE(tag="tag")
        with mock.patch.object(gce, "compute") as m_compute:
            m_execute = mock.MagicMock(
                name="m_execute", side_effect=api_side_effects
            )
            m_executor = mock.MagicMock(name="m_executor")
            m_executor.execute = m_execute
            m_list = mock.MagicMock(name="m_list", return_value=m_executor)
            m_lister = mock.MagicMock(name="m_lister")
            m_lister.list = m_list
            m_images = mock.MagicMock(name="m_images", return_value=m_lister)
            m_compute.images = m_images

            assert expected_image_list == gce._query_image_list(
                release, "project-name", "name-filter", arch
            )
            assert m_list.call_args_list == expected_filter_calls

    @mock.patch(
        MPATH + "GCE._query_image_list",
        return_value=[
            {
                "id": "2",
                "name": "2",
                "creationTimestamp": "2",
            },
            {
                "id": "4",
                "name": "4",
                "creationTimestamp": "4",
            },
            {
                "id": "1",
                "name": "1",
                "creationTimestamp": "1",
            },
            {
                "id": "3",
                "name": "3",
                "creationTimestamp": "3",
            },
        ],
    )
    @mock.patch(MPATH + "GCE._get_name_filter", return_value="name-filter")
    @mock.patch(MPATH + "GCE._get_project", return_value="project-name")
    def test_daily_image_returns_latest_from_query(
        self,
        m_get_project,
        m_get_name_filter,
        m_query_image_list,
    ):
        gce = GCE(tag="tag")
        image = gce.daily_image(
            "jammy", arch="x86_64", image_type=ImageType.GENERIC
        )
        assert m_get_project.call_args_list == [
            mock.call(image_type=ImageType.GENERIC)
        ]
        assert m_get_name_filter.call_args_list == [
            mock.call(release="jammy", image_type=ImageType.GENERIC)
        ]
        assert m_query_image_list.call_args_list == [
            mock.call("jammy", "project-name", "name-filter", "x86_64")
        ]
        assert image == "projects/project-name/global/images/4"
