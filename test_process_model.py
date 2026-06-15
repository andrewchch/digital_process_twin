"""
test_process_model.py
=====================
Tests for process_model.py — covering WorkItem, Event, EventBus, DataObject,
Actor, Step, Process, and the DocumentApprovalProcess example including the
new event-driven primitives added in the refactor.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from enum import Enum
from typing import Any, Type
from unittest.mock import patch

from process_model import (
    AccessPolicy,
    AccessPolicyLevel,
    Actor,
    AdminActor,
    ApproverActor,
    AuthorActor,
    CreateDraft,
    DataObject,
    Document,
    DocumentApprovalProcess,
    DocumentState,
    EditAndFinaliseDraft,
    Event,
    EventBus,
    Notification,
    Process,
    PublishDocument,
    ReviewDocument,
    SetAccessPolicy,
    Step,
    SubmitForApproval,
    SystemActor,
    WorkItem,
    WorkItemStatus,
    WorkItemType,
    _camel_to_label,
    _is_not_implemented,
)


# ===========================================================================
# WorkItem
# ===========================================================================

class TestWorkItem(unittest.TestCase):

    def _make(self, **kwargs) -> WorkItem:
        defaults = dict(
            id="WI-001",
            type=WorkItemType.GAP,
            description="Something is missing.",
            raised_by="TestProcess",
            linked_to="SomeStep",
        )
        defaults.update(kwargs)
        return WorkItem(**defaults)

    def test_default_status_is_open(self):
        wi = self._make()
        self.assertEqual(wi.status, WorkItemStatus.OPEN)

    def test_resolve_sets_status_and_fields(self):
        wi = self._make()
        wi.resolve("Fixed by adding logic.", owner="dev")
        self.assertEqual(wi.status, WorkItemStatus.RESOLVED)
        self.assertEqual(wi.resolution, "Fixed by adding logic.")
        self.assertEqual(wi.owner, "dev")

    def test_propose_sets_proposed_status(self):
        wi = self._make()
        wi.propose("Maybe add a fallback step.", owner="ai_agent")
        self.assertEqual(wi.status, WorkItemStatus.PROPOSED)
        self.assertEqual(wi.owner, "ai_agent")
        self.assertEqual(wi.resolution, "Maybe add a fallback step.")

    def test_str_contains_id_type_and_description(self):
        wi = self._make()
        s = str(wi)
        self.assertIn("WI-001", s)
        self.assertIn("GAP", s)
        self.assertIn("Something is missing.", s)

    def test_str_includes_owner_when_set(self):
        wi = self._make()
        wi.resolve("done", owner="alice")
        self.assertIn("alice", str(wi))


# ===========================================================================
# Event
# ===========================================================================

class TestEvent(unittest.TestCase):

    def test_event_fields(self):
        e = Event(name="doc_submitted", source="Author", payload={"doc_id": 42})
        self.assertEqual(e.name, "doc_submitted")
        self.assertEqual(e.source, "Author")
        self.assertEqual(e.payload["doc_id"], 42)

    def test_event_timestamp_is_datetime(self):
        e = Event(name="x", source="y")
        self.assertIsInstance(e.timestamp, datetime)

    def test_str_contains_name_and_source(self):
        e = Event(name="my_event", source="MyActor")
        s = str(e)
        self.assertIn("my_event", s)
        self.assertIn("MyActor", s)

    def test_default_payload_is_empty_dict(self):
        e = Event(name="a", source="b")
        self.assertEqual(e.payload, {})


# ===========================================================================
# EventBus
# ===========================================================================

class TestEventBus(unittest.TestCase):

    def _make_echo_actor(self, received: list) -> Actor:
        """Return a minimal Actor that records events it receives."""
        class EchoActor(Actor):
            name = "Echo"
            subscriptions = ["ping"]
            publishes = []

            def perform(self, action, context):
                return context

            def notify(self, message, context):
                pass

            def on_event(self, event, bus, context):
                received.append(event)
                return context

        return EchoActor()

    def test_subscribe_and_publish(self):
        received = []
        bus = EventBus()
        actor = self._make_echo_actor(received)
        bus.subscribe("ping", actor)
        event = Event("ping", "test")
        bus.publish(event, {})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].name, "ping")

    def test_unsubscribed_event_is_ignored(self):
        received = []
        bus = EventBus()
        actor = self._make_echo_actor(received)
        bus.subscribe("ping", actor)
        bus.publish(Event("pong", "test"), {})
        self.assertEqual(received, [])

    def test_history_records_all_published_events(self):
        bus = EventBus()
        bus.publish(Event("e1", "src"), {})
        bus.publish(Event("e2", "src"), {})
        history = bus.history
        self.assertEqual([e.name for e in history], ["e1", "e2"])

    def test_history_returns_copy(self):
        bus = EventBus()
        bus.publish(Event("e1", "src"), {})
        h1 = bus.history
        h1.append(Event("extra", "src"))
        self.assertEqual(len(bus.history), 1)

    def test_context_threads_through_handlers(self):
        """Each handler receives and returns the updated context."""
        class IncActor(Actor):
            name = "Inc"
            subscriptions = ["tick"]
            publishes = []

            def perform(self, action, context):
                return context

            def notify(self, message, context):
                pass

            def on_event(self, event, bus, context):
                context["count"] = context.get("count", 0) + 1
                return context

        bus = EventBus()
        a1, a2 = IncActor(), IncActor()
        bus.subscribe("tick", a1)
        bus.subscribe("tick", a2)
        ctx = bus.publish(Event("tick", "src"), {})
        self.assertEqual(ctx["count"], 2)

    def test_multiple_subscribers_to_same_event(self):
        received = []

        class RecordActor(Actor):
            name = "Rec"
            subscriptions = ["go"]
            publishes = []

            def perform(self, action, context):
                return context

            def notify(self, message, context):
                pass

            def on_event(self, event, bus, context):
                received.append(self)
                return context

        bus = EventBus()
        a, b = RecordActor(), RecordActor()
        bus.subscribe("go", a)
        bus.subscribe("go", b)
        bus.publish(Event("go", "src"), {})
        self.assertEqual(len(received), 2)


# ===========================================================================
# DataObject state machines
# ===========================================================================

class TestDocument(unittest.TestCase):

    def test_initial_state_is_draft(self):
        doc = Document("Title", "Content")
        self.assertEqual(doc.state, DocumentState.DRAFT)

    def test_valid_transition_draft_to_submitted(self):
        doc = Document()
        doc.transition(DocumentState.SUBMITTED)
        self.assertEqual(doc.state, DocumentState.SUBMITTED)

    def test_invalid_transition_raises_value_error(self):
        doc = Document()
        with self.assertRaises(ValueError):
            doc.transition(DocumentState.APPROVED)  # DRAFT cannot go to APPROVED

    def test_full_happy_path_transitions(self):
        doc = Document("Doc", "Body")
        doc.transition(DocumentState.SUBMITTED)
        doc.transition(DocumentState.IN_REVIEW)
        doc.transition(DocumentState.APPROVED)
        doc.transition(DocumentState.PUBLISHED)
        doc.transition(DocumentState.ARCHIVED)
        self.assertEqual(doc.state, DocumentState.ARCHIVED)

    def test_rejection_path(self):
        doc = Document()
        doc.transition(DocumentState.SUBMITTED)
        doc.transition(DocumentState.IN_REVIEW)
        doc.transition(DocumentState.REJECTED)
        doc.transition(DocumentState.DRAFT)
        self.assertEqual(doc.state, DocumentState.DRAFT)

    def test_history_records_all_states(self):
        doc = Document()
        doc.transition(DocumentState.SUBMITTED)
        states = [s for s, _ in doc.history]
        self.assertEqual(states, [DocumentState.DRAFT, DocumentState.SUBMITTED])

    def test_history_returns_copy(self):
        doc = Document()
        h = doc.history
        h.append((DocumentState.APPROVED, datetime.now()))
        self.assertEqual(len(doc.history), 1)  # original unaffected


class TestAccessPolicy(unittest.TestCase):

    def test_initial_state_is_internal(self):
        ap = AccessPolicy()
        self.assertEqual(ap.state, AccessPolicyLevel.INTERNAL)

    def test_transition_between_levels(self):
        ap = AccessPolicy()
        ap.transition(AccessPolicyLevel.PUBLIC)
        self.assertEqual(ap.state, AccessPolicyLevel.PUBLIC)

    def test_invalid_transition_to_same_state_raises(self):
        ap = AccessPolicy()
        with self.assertRaises(ValueError):
            ap.transition(AccessPolicyLevel.INTERNAL)  # same state not in transitions


class TestNotification(unittest.TestCase):

    def test_initial_state_is_pending(self):
        n = Notification("alice", "Subject", "Body")
        self.assertEqual(n.state, Notification.NotificationState.PENDING)

    def test_valid_transition_pending_to_sent(self):
        n = Notification()
        n.transition(Notification.NotificationState.SENT)
        self.assertEqual(n.state, Notification.NotificationState.SENT)

    def test_invalid_transition_pending_to_delivered(self):
        n = Notification()
        with self.assertRaises(ValueError):
            n.transition(Notification.NotificationState.DELIVERED)


# ===========================================================================
# AuthorActor
# ===========================================================================

class TestAuthorActor(unittest.TestCase):

    def _ctx(self, **kwargs) -> dict:
        base = {"user_id": "alice", "title": "My Doc", "content": "Hello."}
        base.update(kwargs)
        return base

    def test_perform_create_draft(self):
        ctx = self._ctx()
        actor = AuthorActor()
        result = actor.perform("create_draft", ctx)
        self.assertIn("document", result)
        self.assertIsInstance(result["document"], Document)
        self.assertEqual(result["document"].state, DocumentState.DRAFT)

    def test_perform_create_draft_sets_author(self):
        ctx = self._ctx(user_id="carol")
        actor = AuthorActor()
        result = actor.perform("create_draft", ctx)
        self.assertEqual(result["document"].author, "carol")

    def test_perform_edit_draft_increments_version(self):
        actor = AuthorActor()
        ctx = actor.perform("create_draft", self._ctx())
        ctx["new_content"] = "Updated content."
        ctx = actor.perform("edit_draft", ctx)
        self.assertEqual(ctx["document"].version, 2)

    def test_perform_submit_transitions_to_submitted(self):
        actor = AuthorActor()
        ctx = actor.perform("create_draft", self._ctx())
        ctx = actor.perform("submit", ctx)
        self.assertEqual(ctx["document"].state, DocumentState.SUBMITTED)

    def test_perform_unknown_action_raises(self):
        actor = AuthorActor()
        with self.assertRaises(NotImplementedError):
            actor.perform("unknown_action", {})

    def test_notify_raises_not_implemented(self):
        actor = AuthorActor()
        with self.assertRaises(NotImplementedError):
            actor.notify("hello", {})

    def test_subscriptions_declared(self):
        self.assertIn("document_creation_requested", AuthorActor.subscriptions)
        self.assertIn("document_rejected", AuthorActor.subscriptions)

    def test_publishes_declared(self):
        self.assertIn("document_submitted", AuthorActor.publishes)

    def test_on_event_document_creation_requested(self):
        bus = EventBus()
        # Absorb any downstream events by subscribing a no-op to document_submitted
        bus.subscribe("document_submitted", _NoOpActor())
        actor = AuthorActor()
        ctx = self._ctx()
        result = actor.on_event(Event("document_creation_requested", "System"), bus, ctx)
        self.assertIn("document", result)
        self.assertEqual(result["document"].state, DocumentState.SUBMITTED)

    def test_on_event_document_rejected_revises_and_resubmits(self):
        bus = EventBus()
        bus.subscribe("document_submitted", _NoOpActor())
        actor = AuthorActor()
        # Set up a document already in REJECTED state
        ctx = self._ctx()
        ctx = actor.perform("create_draft", ctx)
        ctx = actor.perform("submit", ctx)
        ctx["document"].transition(DocumentState.IN_REVIEW)
        ctx["document"].transition(DocumentState.REJECTED)
        result = actor.on_event(Event("document_rejected", "Approver"), bus, ctx)
        self.assertEqual(result["document"].state, DocumentState.SUBMITTED)

    def test_on_event_unknown_event_raises(self):
        actor = AuthorActor()
        with self.assertRaises(NotImplementedError):
            actor.on_event(Event("unknown", "src"), EventBus(), {})


# ===========================================================================
# ApproverActor
# ===========================================================================

class TestApproverActor(unittest.TestCase):

    def _ctx_with_submitted_doc(self) -> dict:
        author = AuthorActor()
        ctx = {"user_id": "alice", "title": "T", "content": "C"}
        ctx = author.perform("create_draft", ctx)
        ctx = author.perform("submit", ctx)
        return ctx

    def test_perform_approve_transitions_to_approved(self):
        ctx = self._ctx_with_submitted_doc()
        ctx["document"].transition(DocumentState.IN_REVIEW)
        actor = ApproverActor()
        ctx["approver_id"] = "bob"
        ctx = actor.perform("approve", ctx)
        self.assertEqual(ctx["document"].state, DocumentState.APPROVED)

    def test_perform_reject_requires_reason(self):
        ctx = self._ctx_with_submitted_doc()
        ctx["document"].transition(DocumentState.IN_REVIEW)
        actor = ApproverActor()
        with self.assertRaises(ValueError):
            actor.perform("reject", ctx)

    def test_perform_reject_with_reason(self):
        ctx = self._ctx_with_submitted_doc()
        ctx["document"].transition(DocumentState.IN_REVIEW)
        ctx["rejection_reason"] = "Too short."
        actor = ApproverActor()
        ctx = actor.perform("reject", ctx)
        self.assertEqual(ctx["document"].state, DocumentState.REJECTED)

    def test_perform_request_changes_raises_not_implemented(self):
        actor = ApproverActor()
        with self.assertRaises(NotImplementedError):
            actor.perform("request_changes", {})

    def test_perform_unknown_action_raises(self):
        actor = ApproverActor()
        with self.assertRaises(NotImplementedError):
            actor.perform("magic", {})

    def test_notify_raises_not_implemented(self):
        actor = ApproverActor()
        with self.assertRaises(NotImplementedError):
            actor.notify("hello", {})

    def test_on_event_approve_path(self):
        bus = EventBus()
        bus.subscribe("document_approved", _NoOpActor())
        actor = ApproverActor()
        author = AuthorActor()
        ctx = {"user_id": "u", "title": "T", "content": "C"}
        ctx = author.perform("create_draft", ctx)
        ctx = author.perform("submit", ctx)
        ctx["approval_decision"] = "approve"
        ctx["approver_id"] = "bob"
        result = actor.on_event(Event("document_assigned_for_review", "System"), bus, ctx)
        self.assertEqual(result["document"].state, DocumentState.APPROVED)

    def test_on_event_reject_path(self):
        bus = EventBus()
        bus.subscribe("document_rejected", _NoOpActor())
        actor = ApproverActor()
        author = AuthorActor()
        ctx = {"user_id": "u", "title": "T", "content": "C"}
        ctx = author.perform("create_draft", ctx)
        ctx = author.perform("submit", ctx)
        ctx["approval_decision"] = "reject"
        ctx["rejection_reason"] = "Insufficient detail."
        result = actor.on_event(Event("document_assigned_for_review", "System"), bus, ctx)
        self.assertEqual(result["document"].state, DocumentState.REJECTED)

    def test_on_event_unknown_decision_raises(self):
        actor = ApproverActor()
        author = AuthorActor()
        ctx = {"user_id": "u", "title": "T", "content": "C"}
        ctx = author.perform("create_draft", ctx)
        ctx = author.perform("submit", ctx)
        # Leave document in SUBMITTED state; on_event will transition it to IN_REVIEW
        ctx["approval_decision"] = "maybe"
        with self.assertRaises(NotImplementedError):
            actor.on_event(Event("document_assigned_for_review", "Sys"), EventBus(), ctx)

    def test_on_event_unknown_event_raises(self):
        actor = ApproverActor()
        with self.assertRaises(NotImplementedError):
            actor.on_event(Event("unrecognised", "src"), EventBus(), {})


# ===========================================================================
# SystemActor
# ===========================================================================

class TestSystemActor(unittest.TestCase):

    def _approved_doc_ctx(self) -> dict:
        author = AuthorActor()
        ctx = {"user_id": "u", "title": "T", "content": "C", "approver_id": "bob"}
        ctx = author.perform("create_draft", ctx)
        ctx = author.perform("submit", ctx)
        ctx["document"].transition(DocumentState.IN_REVIEW)
        ctx["document"].approver = "bob"
        ctx["document"].transition(DocumentState.APPROVED)
        return ctx

    def test_perform_publish(self):
        ctx = self._approved_doc_ctx()
        actor = SystemActor()
        ctx = actor.perform("publish", ctx)
        self.assertEqual(ctx["document"].state, DocumentState.PUBLISHED)
        self.assertIn("published_url", ctx)

    def test_perform_route_to_approver_raises(self):
        actor = SystemActor()
        with self.assertRaises(NotImplementedError):
            actor.perform("route_to_approver", {})

    def test_perform_apply_access_policy_raises(self):
        actor = SystemActor()
        with self.assertRaises(NotImplementedError):
            actor.perform("apply_access_policy", {})

    def test_perform_archive(self):
        ctx = self._approved_doc_ctx()
        actor = SystemActor()
        ctx = actor.perform("publish", ctx)
        ctx = actor.perform("archive", ctx)
        self.assertEqual(ctx["document"].state, DocumentState.ARCHIVED)

    def test_notify_prints_message(self):
        actor = SystemActor()
        with patch("builtins.print") as mock_print:
            actor.notify("hello world", {})
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        self.assertIn("hello world", call_args)

    def test_on_event_document_submitted_routes_to_approver(self):
        bus = EventBus()
        bus.subscribe("document_assigned_for_review", _NoOpActor())
        actor = SystemActor()
        author = AuthorActor()
        ctx = {"user_id": "u", "title": "T", "content": "C"}
        ctx = author.perform("create_draft", ctx)
        ctx = author.perform("submit", ctx)
        ctx["approver_id"] = "bob"
        result = actor.on_event(Event("document_submitted", "Author"), bus, ctx)
        self.assertEqual(result["assigned_approver"], "bob")

    def test_on_event_access_policy_set_publishes(self):
        bus = EventBus()
        bus.subscribe("document_published", _NoOpActor())
        actor = SystemActor()
        ctx = self._approved_doc_ctx()
        result = actor.on_event(Event("access_policy_set", "Admin"), bus, ctx)
        self.assertEqual(result["document"].state, DocumentState.PUBLISHED)

    def test_on_event_unknown_event_raises(self):
        actor = SystemActor()
        with self.assertRaises(NotImplementedError):
            actor.on_event(Event("unknown", "src"), EventBus(), {})


# ===========================================================================
# AdminActor
# ===========================================================================

class TestAdminActor(unittest.TestCase):

    def test_perform_raises_not_implemented(self):
        actor = AdminActor()
        with self.assertRaises(NotImplementedError):
            actor.perform("any_action", {})

    def test_notify_raises_not_implemented(self):
        actor = AdminActor()
        with self.assertRaises(NotImplementedError):
            actor.notify("msg", {})

    def test_on_event_document_approved_sets_policy(self):
        bus = EventBus()
        bus.subscribe("access_policy_set", _NoOpActor())
        actor = AdminActor()
        result = actor.on_event(Event("document_approved", "Approver"), bus, {})
        self.assertIn("access_policy", result)
        self.assertIsInstance(result["access_policy"], AccessPolicy)

    def test_on_event_unknown_event_raises(self):
        actor = AdminActor()
        with self.assertRaises(NotImplementedError):
            actor.on_event(Event("unknown", "src"), EventBus(), {})


# ===========================================================================
# Process.validate()
# ===========================================================================

class TestProcessValidate(unittest.TestCase):

    def test_document_approval_process_validates_and_returns_work_items(self):
        process = DocumentApprovalProcess()
        items = process.validate()
        self.assertIsInstance(items, list)
        self.assertTrue(len(items) > 0)

    def test_all_returned_items_are_work_items(self):
        process = DocumentApprovalProcess()
        for item in process.validate():
            self.assertIsInstance(item, WorkItem)

    def test_validate_detects_unimplemented_handle(self):
        """SetAccessPolicy.handle() is intentionally not implemented — must be flagged."""
        process = DocumentApprovalProcess()
        process.validate()
        descriptions = [wi.description for wi in process.work_items]
        gap_steps = [wi.linked_to for wi in process.work_items if "handle()" in wi.description]
        self.assertIn("SetAccessPolicy", gap_steps)

    def test_validate_clears_previous_items_on_re_run(self):
        process = DocumentApprovalProcess()
        process.validate()
        first_count = len(process.work_items)
        process.validate()
        second_count = len(process.work_items)
        self.assertEqual(first_count, second_count)

    def test_actor_with_subscriptions_but_no_on_event_is_flagged(self):
        """An actor declaring subscriptions without implementing on_event is a gap."""

        class BrokenActor(Actor):
            name = "Broken"
            subscriptions = ["some_event"]
            publishes = []

            def perform(self, action, context):
                return context

            def notify(self, message, context):
                pass

            def on_event(self, event, bus, context):
                raise NotImplementedError

        class MinimalStep(Step):
            actor = BrokenActor
            inputs = []
            outputs = []
            preconditions = ["pre"]
            postconditions = ["post"]

            def handle(self, context):
                return context

            def on_error(self, context, error):
                return context

        class TestProcess(Process):
            name = "Test"
            description = ""

            def actors(self):
                return [BrokenActor]

            def steps(self):
                return [MinimalStep]

        proc = TestProcess()
        proc.validate()
        linked = [wi.linked_to for wi in proc.work_items]
        self.assertIn("BrokenActor", linked)

    def test_actor_with_no_steps_and_no_subscriptions_raises_question(self):
        class OrphanActor(Actor):
            name = "Orphan"
            subscriptions = []
            publishes = []

            def perform(self, action, context):
                return context

            def notify(self, message, context):
                pass

        class OneStep(Step):
            actor = AuthorActor
            inputs = []
            outputs = []
            preconditions = ["pre"]
            postconditions = ["post"]

            def handle(self, context):
                return context

            def on_error(self, context, error):
                return context

        class TestProcess(Process):
            name = "Test"
            description = ""

            def actors(self):
                return [AuthorActor, OrphanActor]

            def steps(self):
                return [OneStep]

        proc = TestProcess()
        proc.validate()
        questions = [wi for wi in proc.work_items if wi.type == WorkItemType.QUESTION]
        orphan_questions = [wi for wi in questions if wi.linked_to == "OrphanActor"]
        self.assertTrue(len(orphan_questions) > 0)

    def test_open_work_items_excludes_resolved(self):
        process = DocumentApprovalProcess()
        process.validate()
        # Resolve the first item
        process.work_items[0].resolve("fixed")
        open_ids = {wi.id for wi in process.open_work_items}
        self.assertNotIn(process.work_items[0].id, open_ids)


# ===========================================================================
# Process.raise_gap()
# ===========================================================================

class TestProcessRaiseGap(unittest.TestCase):

    def test_raise_gap_increments_counter(self):
        process = DocumentApprovalProcess()
        wi1 = process.raise_gap("first", "Test", "SomeStep")
        wi2 = process.raise_gap("second", "Test", "OtherStep")
        self.assertEqual(wi1.id, "WI-001")
        self.assertEqual(wi2.id, "WI-002")

    def test_raise_gap_returns_work_item(self):
        process = DocumentApprovalProcess()
        wi = process.raise_gap("desc", "Test", "Step", WorkItemType.QUESTION)
        self.assertIsInstance(wi, WorkItem)
        self.assertEqual(wi.type, WorkItemType.QUESTION)


# ===========================================================================
# Process.run() — sequential execution
# ===========================================================================

class TestProcessRun(unittest.TestCase):

    def _base_ctx(self, decision="approve") -> dict:
        return {
            "user_id": "alice@example.com",
            "title": "Test Doc",
            "content": "Content.",
            "approval_decision": decision,
            "approver_id": "bob@example.com",
        }

    def test_run_approve_path_returns_published_document(self):
        process = DocumentApprovalProcess()
        ctx = self._base_ctx("approve")
        with patch("builtins.print"):
            result = process.run(ctx)
        self.assertIn("document", result)
        self.assertEqual(result["document"].state, DocumentState.PUBLISHED)

    def test_run_reject_path_leaves_document_submitted_on_resubmit(self):
        """With a rejection decision the step loop stops at ReviewDocument (rejected)."""
        process = DocumentApprovalProcess()
        ctx = self._base_ctx("reject")
        ctx["rejection_reason"] = "Not good enough."
        with patch("builtins.print"):
            result = process.run(ctx)
        # After rejection the document is REJECTED; SetAccessPolicy is a gap so it
        # raises NotImplementedError which process.run() skips.
        self.assertIn("document", result)
        self.assertIn(result["document"].state, [DocumentState.REJECTED, DocumentState.SUBMITTED])

    def test_run_returns_context_dict(self):
        process = DocumentApprovalProcess()
        with patch("builtins.print"):
            result = process.run(self._base_ctx())
        self.assertIsInstance(result, dict)


# ===========================================================================
# Process.run_event_driven()
# ===========================================================================

class TestProcessRunEventDriven(unittest.TestCase):

    def _base_ctx(self, decision="approve") -> dict:
        return {
            "user_id": "alice@example.com",
            "title": "Event Doc",
            "content": "Event content.",
            "approval_decision": decision,
            "approver_id": "bob@example.com",
        }

    def test_approve_path_publishes_document(self):
        process = DocumentApprovalProcess()
        ctx = self._base_ctx("approve")
        event = Event("document_creation_requested", "System")
        with patch("builtins.print"):
            result = process.run_event_driven(event, ctx)
        self.assertIn("document", result)
        self.assertEqual(result["document"].state, DocumentState.PUBLISHED)

    def test_approve_path_sets_published_url(self):
        process = DocumentApprovalProcess()
        ctx = self._base_ctx("approve")
        event = Event("document_creation_requested", "System")
        with patch("builtins.print"):
            result = process.run_event_driven(event, ctx)
        self.assertIn("published_url", result)

    def test_reject_then_approve_path(self):
        """Verify the reject → revise → resubmit → approve cycle works end-to-end."""

        class CountingApprover(ApproverActor):
            def on_event(self, event, bus, context):
                count = context.get("review_count", 0) + 1
                context["review_count"] = count
                context["approval_decision"] = "reject" if count == 1 else "approve"
                if count == 1:
                    context["rejection_reason"] = "Too brief."
                else:
                    context["revised_content"] = "Full content."
                return super().on_event(event, bus, context)

        class TestProcess(DocumentApprovalProcess):
            def actors(self):
                return [AuthorActor, CountingApprover, AdminActor, SystemActor]

        process = TestProcess()
        ctx = {
            "user_id": "carol",
            "title": "Annual Review",
            "content": "Draft.",
            "rejection_reason": "Too brief.",
            "approver_id": "dave",
        }
        event = Event("document_creation_requested", "System")
        with patch("builtins.print"):
            result = process.run_event_driven(event, ctx)
        self.assertEqual(result["document"].state, DocumentState.PUBLISHED)
        self.assertEqual(result["review_count"], 2)

    def test_returns_context(self):
        process = DocumentApprovalProcess()
        ctx = self._base_ctx()
        with patch("builtins.print"):
            result = process.run_event_driven(Event("document_creation_requested", "Sys"), ctx)
        self.assertIsInstance(result, dict)


# ===========================================================================
# Process.register_actors()
# ===========================================================================

class TestRegisterActors(unittest.TestCase):

    def test_actors_with_subscriptions_are_registered(self):
        process = DocumentApprovalProcess()
        bus = EventBus()
        process.register_actors(bus)
        # AuthorActor subscribes to document_creation_requested
        subscribers = bus._subscribers.get("document_creation_requested", [])
        actor_types = [type(a).__name__ for a in subscribers]
        self.assertIn("AuthorActor", actor_types)

    def test_all_subscribing_actors_are_registered(self):
        process = DocumentApprovalProcess()
        bus = EventBus()
        process.register_actors(bus)
        registered_types = {
            type(actor).__name__
            for actors in bus._subscribers.values()
            for actor in actors
        }
        self.assertIn("AuthorActor", registered_types)
        self.assertIn("ApproverActor", registered_types)
        self.assertIn("SystemActor", registered_types)
        self.assertIn("AdminActor", registered_types)


# ===========================================================================
# Process.generate_mermaid() and generate_event_mermaid()
# ===========================================================================

class TestDiagramGeneration(unittest.TestCase):

    def test_generate_mermaid_returns_string(self):
        process = DocumentApprovalProcess()
        diagram = process.generate_mermaid()
        self.assertIsInstance(diagram, str)

    def test_generate_mermaid_starts_with_flowchart(self):
        process = DocumentApprovalProcess()
        diagram = process.generate_mermaid()
        self.assertTrue(diagram.startswith("flowchart TD"))

    def test_generate_mermaid_contains_all_step_names(self):
        process = DocumentApprovalProcess()
        diagram = process.generate_mermaid()
        for step_cls in process.steps():
            self.assertIn(step_cls.__name__, diagram)

    def test_generate_mermaid_contains_start_and_end(self):
        process = DocumentApprovalProcess()
        diagram = process.generate_mermaid()
        self.assertIn("START", diagram)
        self.assertIn("END", diagram)

    def test_generate_event_mermaid_returns_string(self):
        process = DocumentApprovalProcess()
        diagram = process.generate_event_mermaid()
        self.assertIsInstance(diagram, str)

    def test_generate_event_mermaid_contains_actor_names(self):
        process = DocumentApprovalProcess()
        diagram = process.generate_event_mermaid()
        for actor_cls in process.actors():
            self.assertIn(actor_cls.__name__, diagram)

    def test_generate_event_mermaid_contains_event_labels(self):
        process = DocumentApprovalProcess()
        diagram = process.generate_event_mermaid()
        self.assertIn("document_submitted", diagram)
        self.assertIn("document_approved", diagram)

    def test_generate_event_mermaid_external_events_link_from_start(self):
        """Events with no actor publisher should originate from START."""
        process = DocumentApprovalProcess()
        diagram = process.generate_event_mermaid()
        self.assertIn("START", diagram)
        # document_creation_requested is not published by any actor in the process
        self.assertIn("document_creation_requested", diagram)


# ===========================================================================
# _is_not_implemented helper
# ===========================================================================

class TestIsNotImplemented(unittest.TestCase):

    def test_bare_raise_detected(self):
        class Stub:
            def method(self):
                raise NotImplementedError

        self.assertTrue(_is_not_implemented(Stub, "method"))

    def test_raise_with_message_detected(self):
        class Stub:
            def method(self):
                raise NotImplementedError("not done")

        self.assertTrue(_is_not_implemented(Stub, "method"))

    def test_implemented_method_not_flagged(self):
        class Stub:
            def method(self):
                return 42

        self.assertFalse(_is_not_implemented(Stub, "method"))

    def test_branched_raise_not_flagged(self):
        """A method with a branch that raises NotImplementedError is implemented."""
        class Stub:
            def method(self, action):
                if action == "ok":
                    return True
                else:
                    raise NotImplementedError("unknown action")

        self.assertFalse(_is_not_implemented(Stub, "method"))

    def test_pass_body_detected(self):
        class Stub:
            def method(self):
                pass

        self.assertTrue(_is_not_implemented(Stub, "method"))

    def test_missing_method_returns_true(self):
        class Stub:
            pass

        self.assertTrue(_is_not_implemented(Stub, "nonexistent"))

    def test_docstring_only_method_with_raise_not_flagged_incorrectly(self):
        """Method with docstring + real logic is not flagged."""
        class Stub:
            def method(self):
                """Do something."""
                return "done"

        self.assertFalse(_is_not_implemented(Stub, "method"))

    def test_docstring_then_bare_raise_is_flagged(self):
        class Stub:
            def method(self):
                """Not yet done."""
                raise NotImplementedError

        self.assertTrue(_is_not_implemented(Stub, "method"))


# ===========================================================================
# _camel_to_label helper
# ===========================================================================

class TestCamelToLabel(unittest.TestCase):

    def test_single_word_unchanged(self):
        self.assertEqual(_camel_to_label("Document"), "Document")

    def test_two_word_camel(self):
        self.assertEqual(_camel_to_label("CreateDraft"), "Create Draft")

    def test_three_word_camel(self):
        self.assertEqual(_camel_to_label("EditAndFinaliseDraft"), "Edit And Finalise Draft")

    def test_all_uppercase_unchanged(self):
        # No lowercase → uppercase boundary, so no spaces inserted
        self.assertEqual(_camel_to_label("ABC"), "ABC")


# ===========================================================================
# Helpers used across tests
# ===========================================================================

class _NoOpActor(Actor):
    """An actor that silently consumes any event — used to absorb downstream events."""
    name = "NoOp"
    subscriptions = []
    publishes = []

    def perform(self, action, context):
        return context

    def notify(self, message, context):
        pass

    def on_event(self, event, bus, context):
        return context


if __name__ == "__main__":
    unittest.main()
