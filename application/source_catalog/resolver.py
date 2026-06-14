"""Resolve template source defaults with per-user source bindings."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from application.ports import (
    SourceRepository,
    TemplateSourceBindingRepository,
    UserSourceRepository,
    UserSourcePreferenceRepository,
)
from domain.niche import TemplateSourceBinding, UserSource, UserSourcePreference
from domain.source import Source, SourceInput


@dataclass(frozen=True)
class EffectiveSource:
    """A source ready for display or scanning after defaults and overrides apply."""

    source_id: str
    template_source_binding_id: str | None
    locator: str
    source_type: str
    source_family: str
    is_gate_free: bool
    enabled: bool
    muted: bool = False
    user_source_id: str | None = None
    user_source_preference_id: str | None = None
    limit: int | None = None
    scan_frequency: str | None = None
    buyer_voice_verified: bool = False
    options: dict[str, Any] = field(default_factory=dict)
    tier: int | None = None
    priority: int | None = None
    signal_quality_score: float | None = None
    access_mode: str = "unknown"
    requires_proxy: bool = False
    requires_auth: bool = False
    recommended_cadence: str | None = None

    def to_source_input(self) -> SourceInput:
        """Convert the resolved source into a pipeline source input."""
        return SourceInput.create(
            locator=self.locator,
            limit=self.limit,
            options={
                **self.options,
                "source_id": self.source_id,
                "source_type": self.source_type,
                "source_family": self.source_family,
            },
        )


class SourceCatalogResolver:
    """Resolve effective source configuration for a template or adopted niche."""

    def __init__(
        self,
        *,
        source_repository: SourceRepository,
        template_source_binding_repository: TemplateSourceBindingRepository,
        user_source_preference_repository: UserSourcePreferenceRepository | None = None,
        user_source_repository: UserSourceRepository | None = None,
    ) -> None:
        self._source_repository = source_repository
        self._template_source_binding_repository = template_source_binding_repository
        self._user_source_preference_repository = user_source_preference_repository
        self._user_source_repository = user_source_repository

    def list_effective_sources(
        self,
        *,
        template_niche_id: str,
        user_niche_id: str | None = None,
        enabled: bool | None = None,
        include_muted: bool = False,
    ) -> list[EffectiveSource]:
        """List sources with template defaults and optional user preferences applied."""
        bindings = self._template_source_binding_repository.list_template_source_bindings(
            template_niche_id,
        )
        user_sources = {
            user_source.source_id: user_source
            for user_source in (
                self._user_source_repository.list_user_sources(
                    user_niche_id,
                    include_muted=True,
                )
                if self._user_source_repository is not None
                and user_niche_id is not None
                else []
            )
        }
        preferences = {
            preference.source_id: preference
            for preference in (
                self._user_source_preference_repository.list_user_source_preferences(
                    user_niche_id,
                )
                if self._user_source_preference_repository is not None
                and user_niche_id is not None
                else []
            )
        }

        resolved: list[EffectiveSource] = []
        bound_source_ids: set[str] = set()
        for binding in bindings:
            source = self._source_repository.get_source(binding.source_id)
            if source is None:
                continue
            bound_source_ids.add(source.id)
            user_source = user_sources.get(source.id)
            if user_source is not None:
                effective_source = _resolve_user_source(source, binding, user_source)
            else:
                preference = preferences.get(source.id)
                effective_source = _resolve_source(source, binding, preference)
            if enabled is not None and effective_source.enabled != enabled:
                continue
            if effective_source.muted and not include_muted:
                continue
            resolved.append(effective_source)
        for user_source in user_sources.values():
            if user_source.source_id in bound_source_ids:
                continue
            source = self._source_repository.get_source(user_source.source_id)
            if source is None:
                continue
            effective_source = _resolve_user_source(source, None, user_source)
            if enabled is not None and effective_source.enabled != enabled:
                continue
            if effective_source.muted and not include_muted:
                continue
            resolved.append(effective_source)
        return sorted(resolved, key=_effective_source_sort_key)


def _resolve_source(
    source: Source,
    binding: TemplateSourceBinding,
    preference: UserSourcePreference | None,
) -> EffectiveSource:
    enabled = (
        binding.default_enabled
        if preference is None
        else preference.effective_enabled(binding.default_enabled)
    )
    muted = bool(preference.muted) if preference else False
    limit = (
        preference.limit_override
        if preference and preference.limit_override
        else binding.default_limit
    )
    scan_frequency = (
        preference.cadence_override
        if preference and preference.cadence_override
        else binding.default_scan_frequency or binding.recommended_cadence
    )
    options = dict(binding.default_options)
    if preference:
        options.update(preference.options_override)
    return EffectiveSource(
        source_id=source.id,
        template_source_binding_id=binding.id,
        user_source_preference_id=preference.id if preference else None,
        locator=source.locator,
        source_type=source.source_type,
        source_family=source.source_family,
        is_gate_free=source.is_gate_free,
        enabled=enabled and not muted,
        muted=muted,
        limit=limit,
        scan_frequency=scan_frequency,
        buyer_voice_verified=binding.default_buyer_voice_verified,
        options=options,
        tier=binding.tier,
        priority=preference.priority_override if preference else None,
        signal_quality_score=binding.signal_quality_score,
        access_mode=source.access_mode,
        requires_proxy=source.requires_proxy,
        requires_auth=source.requires_auth,
        recommended_cadence=binding.recommended_cadence,
    )


def _resolve_user_source(
    source: Source,
    binding: TemplateSourceBinding | None,
    user_source: UserSource,
) -> EffectiveSource:
    scan_frequency = (
        user_source.cadence
        or (binding.default_scan_frequency if binding else None)
        or (binding.recommended_cadence if binding else None)
    )
    options = dict(binding.default_options) if binding else {}
    options.update(user_source.options)
    return EffectiveSource(
        source_id=source.id,
        template_source_binding_id=(
            user_source.template_source_binding_id
            or (binding.id if binding else None)
        ),
        user_source_id=user_source.id,
        locator=source.locator,
        source_type=source.source_type,
        source_family=source.source_family,
        is_gate_free=source.is_gate_free,
        enabled=user_source.active,
        muted=user_source.muted,
        limit=user_source.limit or (binding.default_limit if binding else None),
        scan_frequency=scan_frequency,
        buyer_voice_verified=(
            binding.default_buyer_voice_verified if binding else False
        ),
        options=options,
        tier=binding.tier if binding else None,
        priority=user_source.priority,
        signal_quality_score=binding.signal_quality_score if binding else None,
        access_mode=source.access_mode,
        requires_proxy=source.requires_proxy,
        requires_auth=source.requires_auth,
        recommended_cadence=binding.recommended_cadence if binding else None,
    )


def _effective_source_sort_key(source: EffectiveSource) -> tuple[int, int, float, str]:
    priority = source.priority if source.priority is not None else 10_000
    tier = source.tier if source.tier is not None else 10_000
    quality = -(source.signal_quality_score or 0.0)
    return (priority, tier, quality, source.locator)
