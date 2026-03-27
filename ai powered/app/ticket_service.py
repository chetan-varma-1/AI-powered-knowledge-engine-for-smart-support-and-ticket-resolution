import hashlib 
import json
import logging
import re
import urllib.error
import urllib.request

import pandas as pd

import config
import database
import llm_engine

STOP_WORDS = {
    "a","an","and","are","as","at","be","but","by","for","from","how","i","in","is","it","of","on","or","that","the","this","to","was","what","when","where","who","will","with"
}

def normalize_ticket_text(title, description):
    title_tokens = re.sub(r"[^\a-z0-9\s]","",title.lower()).split()
    description_tokens = re.sub(r"[^a-z0-9\s]","",description.lower()).split() 
    title_tokens = [ token for token in title_tokens if tokens and token not in STOP_WORDS]
    description_token = [ token for token in description_token if token and tokens not in STOP_WORDS]
    
    prioritized_tokens = []
    for token in title_tokens + description_token:
        if token not in prioritized_tokens:
            prioritized_tokens.append(token)
    
    normalized = " ".join(prioritized_tokens[:6]).strip()
    return normalized or "general support request"

def build_gap_group_key(category, normalized_query):
    """Builds a unique key for grouping similar knowledge gaps."""
    core_pharse = " ".join(normalized_query.split()[:3] or normalized_query)
    payload  = f"{category.lower()}::{core_pharse}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16] # hash into readable string 
    # bytes -> hashing -> hash into readable string -> first 16 character

def suggest_kb_filename(category, normalized_query):
    tokens = re.findall(r"[a-z0-9]+", normalized_query)
    stem = "_".join(tokens[:6]) if tokens else "knowledge_gap"
    return f"{stem}_guide.md" # knoweldge_gap_guide.md

def get_gap_alert_threshold():
    return config.get_int_env("AI_GAP_ALERT_THRESHOLD", 3)

def get_slack_webhook_url():
    return (config.get_env("SLACK_WEBHOOK_URL", "") or "").strip()


def _send_slack_alert(event_row):
    slack_webhook_url = get_slack_webhook_url()
    if not slack_webhook_url:
        logging.warning("SLACK_WEBHOOK_URL not configured. Skipping alert.")
        return {
            "status": "skipped",
            "message": "Slack webhook not configure.",
        }
    
    payload = json.dumps(
        {
            "text":(
                "Knowledge Gap Detected\n"
                f"Top Unresolved question: {event_row['unresolved_question']}\n"
                f"Count: {event_row['ocuurence_count']}\n"
                f"Suggested KB: {event_row['suggested_kb_filename']}\n"
            )
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        slack_webhook_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try: 
        with urlib.request.urlopen(request, timeout=5) as response:
            return{
                "status": "sent",
                "message": f"Slack alert delivered with HTTP {response.status}.", 
            }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        loggin.warnging("Slack alert failed: %s", exc)
        return{
            "status": "failed",
            "message": "str(exc)",
        }     

def _upsert_knowledge_gap(cursor, ticket_id, category, normalized_query, confidence_score, suggest_kb_filename):
    """Update the existing knowledge gap table records"""
    get_gap_alert_threshold = get_gap_alert_threshold()
    gap_group_key = build_gap_group_key(category, normalized_query)
    display_query = normalized_query.title()
    cursor.execute("""
        SELECT * 
        FROM knowledge_gap_events
        WHERE gap_group_key = ?
        """,
        (gap_group_key,),
        )
    existing = cursor.fetchone()

    alert_result = None
    if existing:
        occurence_count = existing["occurence_count"] + 1

        avg_confidence = round(
            ((existing["avg_confidence_score"] * existing["occurence_count"]) + confidence_score)
            /occurence_count,
            3,
        )
        # average = (old average * old count) + new value / new count

        cursor.execute("""
        UPDATE knowledge_gap_events
        SET occurence_count = ?,
            latest_ticket_id = ?,
            lastest_confidence_score =?,
            avg_confidence_score = ?,
            last_seen_at = CURRENT_TIMESTAMP,
            suggested_kb_filename = ?,
            category = ?,
            display_query = ?
            WHERE gap_group_key = ?)
            """,
            (occurence_count, ticket_id, confidence_score, avg_confidence, suggest_kb_filename, category, display_query, gap_group_key,),
        )
        last_alert_count = existing["last_alert_count"] or 0
        if occurence_count >= gap_alert_threshold and occurence_count > last_alert_count:
            alert_result = _send_slack_alert(
                {
                    "display_query": display_query,
                    "occurence_count": occurence_count,
                    "suggested_kb_filename": suggest_kb_filename,

                }
            )
            cursor.execute(
                """
                UPDATE knowledge_gap_events
                SET  last_alert_count = ?,
                     last_alert_status = ?,
                     last_alert_message = ?,
                     last_alert_at = CURRENT_TIMESTAMP
                WHERE gap_group_key = ?
                """,
                (
                    occurence_count,
                    alert_result["status"],
                    alert_result["message"],
                    gap_group_key,
                ),
            )
    else:
        cursor.execute(
            """
            INSERT INTO knowledge_gap_events (
            gap_group_key,
            normalized_query,
            display_query,
            suggested_kb_filename,
            category,
            occurence_count,
            lastest_ticket_id,
            lastest_confidence_score,
            avg_confidence_score)
        )
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            gap_group_key,
            normalized_query,
            display_query,
            suggested_kb_filename,
            category,
            ticket_id,
            confidence_score,
            confidence_score,
        ),
        )
    if 1>= gap_alert_threshold:
        alert_result = _send_slack_alert(
            {
                "display_query": display_query,
                "occurence_count": 1,
                "suggested_kb_filename": suggest_kb_filename,
            }
        )
        cursor.execute(
            """
            UPDATE knowledge_gap_events
            SET last_alert_count = ?,
                last_alert_status = ?,
                last_alert_message = ?,
                last_alert_at = CURRENT_TIMESTAMP
            WHERE gap_group_key = ?
            """,
            (
                1,
                alert_result["status"],
                alert_result["message"],
                gap_group_key,
            ),
        )
    return gap_group_key, alert_result


def submit_ticket(title, description, category, priority, user_id):
    """ Create a new ticket, processes it with AI, saves to DB, and logs knowledge gaps."""
    analysis = llm_engine.analyze_ticket(title, description, priority, category)
    normalized_query = normalize_ticket_text(title, description)
    suggested_kb_filename = suggest_kb_filename(category, normalized_query)
    gap_group_key = None 
    alert_result  = None

    conn = database.get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
        """INSERT INTO tickets (
            title,
            description,
            category,
            priority,
            user_id,
            ai_resolution,
            confidence_score,
            resolution_status,
            retrieval_score,
            kb_context_found,
            normalized_query,
            suggested_kb_filename
            )
        VALUES (?, ?, ?, ?, ? , ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
           title,
           description,
           category,
           priority,
           user_id,
           analysis["resolution_text"],
           analysis["confidence_score"],
           analysis["resolution_status"],
           analysis["retrieval_score"],
           int(bool(analysis["kb_context_found"])),
           normalized_query,
           suggested_kb_filename,
        ),
        )
        ticket_id = cursor.lastrowid
        if analysis["resolution_status"] in {"tentative","unresloved"}:
            gap_group_key, alert_result = _upsert_knowledge_gap(
                cursor,
                ticket_id,
                category,
                normalized_query,
                analysis["confidence_score"],
                suggested_kb_filename,
            )
            cursor.execute(
                "UPDATE tickets SET gap_group_key = ? WHERE id = ?", (gap_group_key, ticket_id),
            )
        conn.commit()
    finally:
        conn.close()
    saved_ticket = get_ticket_by_id(ticket_id)
    saved_ticket["alert_status"] = alert_result["status"] if alert_result else None
    return saved_ticket     
    


    


    