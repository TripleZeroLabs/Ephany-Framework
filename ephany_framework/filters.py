"""
Shared filter backends.
"""

from rest_framework.filters import OrderingFilter


class StableOrderingFilter(OrderingFilter):
    """
    OrderingFilter that always produces a total order.

    Pagination slices a query with LIMIT/OFFSET. SQL does not promise that two
    rows tying on the sort key come back in the same relative position from one
    query to the next, so a client sorting by a non-unique column can page
    through a list and see a row twice, or never see it at all. The count stays
    right, which is what makes it hard to notice.

    `?ordering=name` on a catalog where two assets share a name is exactly that
    case, and the UI offers name, model, manufacturer, and category as sort
    options — none of them unique.

    Appending the primary key breaks every tie deterministically, so paging is
    consistent regardless of what the client sorts by.

    Returning None is left alone: DRF then skips ordering entirely and the
    model's Meta.ordering applies. Every paginated model here defines one, and
    each ends in a unique field for the same reason.
    """

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if not ordering:
            return ordering

        ordering = list(ordering)
        pk_name = queryset.model._meta.pk.name
        already_total = any(
            field.lstrip("-") in ("pk", pk_name) for field in ordering
        )
        if not already_total:
            ordering.append("pk")
        return ordering
