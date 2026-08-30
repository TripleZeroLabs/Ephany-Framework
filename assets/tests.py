"""
Tests for list ordering and pagination stability.

Pagination slices a query with LIMIT/OFFSET. When rows tie on the sort key, SQL
makes no promise about their relative position between queries, so paging can
show a row twice or skip it entirely while the reported count stays correct —
which is what makes the failure easy to miss.

Django raises UnorderedObjectListWarning for the unordered case, but it cannot
see the subtler one: a client sorting by a non-unique column such as `name`.
Both are pinned here.
"""

import warnings

from django.core.paginator import UnorderedObjectListWarning
from django.test import TestCase, override_settings

from assets.models import Asset, AssetCategory, Manufacturer, Vendor
from ephany_framework.urls import router

OPEN_API = {"API_ALLOW_ANONYMOUS": True}


def page_ids(client, url):
    """Return the ids on one page of a paginated list response."""
    return [row["id"] for row in client.get(url).json()["results"]]


@override_settings(**OPEN_API)
class PaginationStabilityTests(TestCase):
    """Paging must visit every row exactly once, whatever the sort key."""

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Acme")
        category = AssetCategory.objects.create(name="Shelving")
        # Every asset shares a name, so `?ordering=name` is one giant tie and
        # only the tiebreaker decides the order.
        for i in range(10):
            Asset.objects.create(
                type_id=f"TYPE-{i:03d}",
                manufacturer=manufacturer,
                category=category,
                model=f"Model {i}",
                name="Identical Name",
            )

    def _walk_pages(self, base_url, page_size=3, expected_total=10):
        seen = []
        for page in range(1, (expected_total // page_size) + 2):
            seen += page_ids(self.client, f"{base_url}page_size={page_size}&page={page}")
        return seen

    def test_default_ordering_visits_every_row_once(self):
        seen = self._walk_pages("/api/assets/?")

        self.assertEqual(len(seen), 10, "paging returned a different number of rows")
        self.assertEqual(len(set(seen)), 10, "a row appeared on more than one page")
        self.assertEqual(set(seen), set(Asset.objects.values_list("id", flat=True)))

    def test_ordering_by_a_non_unique_field_visits_every_row_once(self):
        """The regression this suite exists for.

        Every asset here has the same name, so without a tiebreaker the
        database is free to order the ties differently for each page query.
        """
        seen = self._walk_pages("/api/assets/?ordering=name&")

        self.assertEqual(len(set(seen)), 10, "a row was duplicated or skipped")

    def test_paging_is_repeatable(self):
        """The same page requested twice returns the same rows."""
        url = "/api/assets/?ordering=name&page_size=3&page=2"
        self.assertEqual(page_ids(self.client, url), page_ids(self.client, url))

    def test_reversing_the_sort_key_still_visits_every_row_once(self):
        """Descending is paged as completely as ascending.

        Note it is not the exact reverse, and should not be: every name here
        ties, so '-name' orders nothing and the appended pk tiebreaker stays
        ascending. Completeness is the property that matters.
        """
        seen = self._walk_pages("/api/assets/?ordering=-name&")

        self.assertEqual(len(set(seen)), 10)

    def test_no_unordered_queryset_warning(self):
        """Django's own signal that a paginated queryset lacks an order."""
        with warnings.catch_warnings():
            warnings.simplefilter("error", UnorderedObjectListWarning)
            self.assertEqual(self.client.get("/api/assets/").status_code, 200)


class EveryListEndpointIsTotallyOrderedTests(TestCase):
    """
    A structural check across the whole router.

    Adding a viewset whose model has no ordering — or an ordering that can tie —
    reintroduces the bug silently on that endpoint. This fails instead.
    """

    def test_every_registered_viewset_orders_by_a_unique_field_last(self):
        offenders = []

        for prefix, viewset, _ in router.registry:
            queryset = viewset.queryset
            model = queryset.model
            ordering = list(queryset.query.order_by or model._meta.ordering or [])

            if not ordering:
                offenders.append(f"/{prefix}/ ({model.__name__}): no ordering at all")
                continue

            last = ordering[-1].lstrip("-")
            fields = {f.name: f for f in model._meta.get_fields() if hasattr(f, "name")}
            is_unique = last in ("pk", model._meta.pk.name) or getattr(
                fields.get(last), "unique", False
            )
            if not is_unique:
                offenders.append(
                    f"/{prefix}/ ({model.__name__}): ordering {ordering} ends in "
                    f"'{last}', which is not unique, so rows can tie"
                )

        self.assertEqual(
            offenders,
            [],
            "These list endpoints can return unstable pages:\n  "
            + "\n  ".join(offenders),
        )


@override_settings(**OPEN_API)
class StableOrderingFilterTests(TestCase):
    """The filter that keeps client-requested sorts total."""

    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(name="Acme")
        cls.vendor = Vendor.objects.create(name="Supplier")

    @staticmethod
    def _ordering_for(query_string, ordering_fields=("name", "id")):
        """Run StableOrderingFilter.get_ordering for a given ?ordering= value."""
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        from ephany_framework.filters import StableOrderingFilter

        class View:
            pass

        view = View()
        view.ordering_fields = list(ordering_fields)

        request = Request(APIRequestFactory().get(f"/api/assets/?{query_string}"))
        return StableOrderingFilter().get_ordering(request, Asset.objects.all(), view)

    def test_tiebreaker_is_appended_to_a_requested_ordering(self):
        self.assertEqual(self._ordering_for("ordering=name"), ["name", "pk"])

    def test_tiebreaker_is_appended_to_a_descending_ordering(self):
        self.assertEqual(self._ordering_for("ordering=-name"), ["-name", "pk"])

    def test_no_duplicate_tiebreaker_when_already_sorting_by_the_pk(self):
        """Sorting by id is already total; nothing should be appended."""
        self.assertEqual(self._ordering_for("ordering=id"), ["id"])

    def test_no_ordering_requested_is_left_alone(self):
        """Returning None lets DRF fall through to the model's Meta.ordering."""
        self.assertIsNone(self._ordering_for(""))

    def test_vendors_paginate_stably_despite_duplicate_names(self):
        """Vendor.name is not unique, unlike most display fields here."""
        for _ in range(6):
            Vendor.objects.create(name="Same Vendor")

        seen = []
        for page in (1, 2, 3, 4):
            seen += page_ids(self.client, f"/api/vendors/?ordering=name&page_size=2&page={page}")

        self.assertEqual(len(set(seen)), Vendor.objects.count())
