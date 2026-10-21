from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from onyx.db.enums import ConnectorCredentialPairStatus
from onyx.db.models import ConnectorCredentialPair


def get_started_cc_pairs_in_repeated_error_state(
    db_session: Session,
) -> list[ConnectorCredentialPair]:
    """Started (non-paused, non-deleting) cc pairs flagged by the indexing
    pipeline as repeatedly failing. The flag is set after several consecutive
    failed attempts and cleared on the next success, so transient failures
    are not reported."""
    stmt = (
        select(ConnectorCredentialPair)
        .options(joinedload(ConnectorCredentialPair.connector))
        .where(
            ConnectorCredentialPair.status.in_(
                ConnectorCredentialPairStatus.active_statuses()
            ),
            ConnectorCredentialPair.in_repeated_error_state.is_(True),
            # connector 0 is the ingestion API default pair; it is never indexed
            ConnectorCredentialPair.connector_id != 0,
        )
        .order_by(ConnectorCredentialPair.id)
    )
    return list(db_session.scalars(stmt).unique().all())
