import logging
from datetime import datetime, timezone
from app.services.supabase_client import insert_message

logger = logging.getLogger(__name__)


def send_message_to_conversation(
    conversation_id: str,
    sender_id: str,
    recipient_id: str,
    content: str
) -> bool:
    """
    Sends a message to the specified conversation by inserting into the cp_messages
    table via Supabase REST API.
    """
    logger.info(
        f"[OUTGOING TWIN MESSAGE] Attempting message delivery. "
        f"Conv: {conversation_id}, Sender: {sender_id}, Recipient: {recipient_id}, Length: {len(content)}"
    )

    try:
        success = insert_message(conversation_id, sender_id, content)
        if success:
            logger.info("Successfully saved message to cp_messages table via Supabase REST.")
            return True
        else:
            logger.error("Failed to insert message via Supabase REST. Logging outgoing message locally.")
            now = datetime.now(timezone.utc).isoformat()
            print(f"[OUTGOING BACKUP LOG] {now} | Conv: {conversation_id} | Sender: {sender_id} | Body: {content}")
            return False

    except Exception as e:
        logger.error(f"Error in message execution transaction: {e}")
        now = datetime.now(timezone.utc).isoformat()
        print(f"[OUTGOING BACKUP LOG] {now} | Conv: {conversation_id} | Sender: {sender_id} | Body: {content}")
        return False
