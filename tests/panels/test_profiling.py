from __future__ import absolute_import, unicode_literals

import unittest

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import six

from ..base import BaseTestCase
from ..views import listcomp_view, regular_view


@override_settings(
    DEBUG_TOOLBAR_PANELS=["debug_toolbar.panels.profiling.ProfilingPanel"]
)
class ProfilingPanelTestCase(BaseTestCase):
    panel_id = "ProfilingPanel"

    def test_regular_view(self):
        self._get_response = lambda request: regular_view(request, "profiling")
        response = self.panel.process_request(self.request)
        self.panel.generate_stats(self.request, response)
        self.assertIn("func_list", self.panel.get_stats())
        self.assertIn("regular_view", self.panel.content)

    def test_insert_content(self):
        """
        Test that the panel only inserts content after generate_stats and
        not the process_request.
        """
        self._get_response = lambda request: regular_view(request, "profiling")
        response = self.panel.process_request(self.request)
        # ensure the panel does not have content yet.
        self.assertNotIn("regular_view", self.panel.content)
        self.panel.generate_stats(self.request, response)
        # ensure the panel renders correctly.
        self.assertIn("regular_view", self.panel.content)
        self.assertValidHTML(self.panel.content)

    @unittest.skipIf(six.PY2, "list comprehension not listed on Python 2")
    def test_listcomp_escaped(self):
        self._get_response = lambda request: listcomp_view(request)
        response = self.panel.process_request(self.request)
        self.panel.generate_stats(self.request, response)
        self.assertNotIn(
            '<span class="djdt-func"><listcomp></span>', self.panel.content
        )
        self.assertIn(
            '<span class="djdt-func">&lt;listcomp&gt;</span>', self.panel.content
        )

    def test_generate_stats_no_profiler(self):
        """
        Test generating stats with no profiler.
        """
        response = HttpResponse()
        self.assertIsNone(self.panel.generate_stats(self.request, response))

    def test_generate_stats_no_root_func(self):
        """
        Test generating stats using profiler without root function.
        """
        response = self.panel.process_request(self.request)
        self.panel.profiler.clear()
        self.panel.profiler.enable()
        self.panel.profiler.disable()
        self.panel.generate_stats(self.request, response)
        self.assertNotIn("func_list", self.panel.get_stats())


@override_settings(
    DEBUG=True, DEBUG_TOOLBAR_PANELS=["debug_toolbar.panels.profiling.ProfilingPanel"]
)
class ProfilingPanelIntegrationTestCase(TestCase):
    def test_view_executed_once(self):
        self.assertEqual(User.objects.count(), 0)

        response = self.client.get("/new_user/")
        self.assertContains(response, "Profiling")
        self.assertEqual(User.objects.count(), 1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                response = self.client.get("/new_user/")
        self.assertEqual(User.objects.count(), 1)
