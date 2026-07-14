"""Central list of active sources.

Adding a v2 source (deprecations, egress pricing, GCP/Azure, etc.) is a
one-line change here plus the new module — nothing else in the pipeline needs
to know. This is the whole point of the `Source`/`FetchResult` contract.
"""

from __future__ import annotations

from typing import List

from .sources.base import Source
from .sources.health_events import HealthEventsSource
from .sources.service_terms import ServiceTermsSource
from .sources.sla_pages import ec2_sla, s3_sla, sla_index


def active_sources() -> List[Source]:
    return [
        ServiceTermsSource(),
        HealthEventsSource(),
        sla_index(),
        ec2_sla(),
        s3_sla(),
    ]
