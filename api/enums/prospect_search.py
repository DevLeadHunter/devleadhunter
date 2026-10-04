"""
Enumerations of the objective-driven prospect search.
"""

from enum import Enum


class ProspectSearchStatus(str, Enum):
    """
    Lifecycle of a prospect search.

    Attributes:
        PENDING: Created, the background run has not started yet
        RUNNING: Discovering and verifying candidates on the server
        WAITING_BROWSER: Server work is done, candidates wait for a Facebook page read on a desktop
        COMPLETED: Finished (objective reached or sources exhausted)
        CANCELLED: Stopped by the user, what was found is kept
        FAILED: Stopped by an unexpected error
    """

    PENDING = "pending"
    RUNNING = "running"
    WAITING_BROWSER = "waiting_browser"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ProspectSearchChannel(str, Enum):
    """
    Contact channel the search must make possible.

    Attributes:
        EMAIL: A proven email is required
        SMS: A mobile number is required
        EMAIL_AND_SMS: Both are required (the channel is drawn afterwards)
    """

    EMAIL = "email"
    SMS = "sms"
    EMAIL_AND_SMS = "email_and_sms"


class CandidateStatus(str, Enum):
    """
    Where a candidate stands in the search.

    Attributes:
        DISCOVERED: Found, not verified yet
        NEEDS_BROWSER: Verified, waiting for its Facebook page to be read on a desktop
        KEPT: Meets the objective, saved as a prospect
        SET_ASIDE: Usable on another channel only (mobile without email…), saved as a prospect
        TO_CONFIRM: Has a contact the search could not prove, waits for the user's decision
        REJECTED: Discarded, with a reason
    """

    DISCOVERED = "discovered"
    NEEDS_BROWSER = "needs_browser"
    KEPT = "kept"
    SET_ASIDE = "set_aside"
    TO_CONFIRM = "to_confirm"
    REJECTED = "rejected"


class CandidateRejectReason(str, Enum):
    """
    Why a candidate was discarded.

    Attributes:
        HAS_WEBSITE: Owns a working website
        CLOSED: Permanently or temporarily closed
        HOMONYM: The verification found another business of the same name
        CHAIN: Franchise or chain outlet, the owner does not decide alone
        WRONG_TRADE: Not the searched trade
        LOW_RATING: Rated below the search's floor
        NO_CONTACT: Neither an email nor a mobile number
        ALREADY_KNOWN: Already a prospect of the user
        DO_NOT_CONTACT: Matches a prospect flagged « do not contact »
        PREVIOUSLY_REJECTED: Discarded by an earlier search
        MANUAL: Discarded by the user
    """

    HAS_WEBSITE = "has_website"
    CLOSED = "closed"
    HOMONYM = "homonym"
    CHAIN = "chain"
    WRONG_TRADE = "wrong_trade"
    LOW_RATING = "low_rating"
    NO_CONTACT = "no_contact"
    ALREADY_KNOWN = "already_known"
    DO_NOT_CONTACT = "do_not_contact"
    PREVIOUSLY_REJECTED = "previously_rejected"
    MANUAL = "manual"


class CandidateOrigin(str, Enum):
    """
    Where a candidate was first seen.

    Attributes:
        GOOGLE_LOCAL: Google local results
        FACEBOOK_SEARCH: A Facebook page surfaced by a search engine
        REGISTRY_RGE: ADEME list of RGE-certified companies (France)
        REGISTRY_RBQ: RBQ list of licensed contractors (Québec)
    """

    GOOGLE_LOCAL = "google_local"
    FACEBOOK_SEARCH = "facebook_search"
    REGISTRY_RGE = "registry_rge"
    REGISTRY_RBQ = "registry_rbq"


class EmailProofLevel(str, Enum):
    """
    How well an email is proven to belong to the business.

    Attributes:
        PUBLISHED: Published by the business itself or an official registry
        DIRECTORY: Listed for this business by a third-party page
        GUESSED: Found near the business name, without a clear proof
    """

    PUBLISHED = "a"
    DIRECTORY = "b"
    GUESSED = "c"
