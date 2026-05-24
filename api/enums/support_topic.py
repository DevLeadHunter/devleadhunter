"""
Support ticket topic enumeration.
"""
from enum import Enum


class SupportTicketTopic(str, Enum):
    """
    Enumeration of predefined support ticket topics.
    """

    CREDITS_BILLING = "credits_billing"
    MISSING_RESULTS = "missing_results"
    BUG_REPORT = "bug_report"
    REFUND_CREDITS = "refund_credits"
    REFUND_PAYMENT = "refund_payment"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


__all__ = ["SupportTicketTopic"]


