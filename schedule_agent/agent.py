from dotenv import load_dotenv
load_dotenv()

import os
import sys
import json
from datetime import datetime, timedelta
from google.adk.agents import Agent

# Define path to schedule.json folder for filesystem access
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_FILE = os.path.join(AGENT_DIR, "schedule.json")

# Define custom SecurityError class
class SecurityError(Exception):
    """Raised when security or data locality checks fail."""
    pass

# =====================================================================
# ZERO-TRUST SECURITY & LOCALITY VERIFICATION
# =====================================================================
# Security Comment: Under zero-trust architecture, we must ensure that
# all data operations, database files, and model context protocol (MCP)
# environments remain restricted to the local machine. Personal user
# data (tasks, finances, schedule, health logs) must not be transmitted
# to unauthorized external cloud databases or third-party networks.
# Note: Google Calendar API access through the MCP server is authorized
# exclusively for official schedule synchronization, while local database
# storage must remain fully isolated on disk.
# =====================================================================
def verify_local_data_isolation(agent_dir: str):
    """Verify that all files are stored strictly on the local filesystem
    and no remote database configurations exist.
    """
    abs_dir = os.path.abspath(agent_dir)
    # Check for UNC path (e.g. \\remote-server) or remote URL schema
    if abs_dir.startswith("\\\\") or any(abs_dir.startswith(s) for s in ["http://", "https://", "ftp://"]):
        raise SecurityError("Critical Security Alert: Remote storage detected. Data must remain local.")
    
    # Check for unauthorized environment variables attempting to leak data or redirect to external hosts
    for env_var in ["DB_HOST", "DATABASE_URL", "CLOUD_SQL_CONNECTION_NAME"]:
        val = os.getenv(env_var)
        if val and not any(local in val.lower() for local in ["localhost", "127.0.0.1", "::1", "local"]):
            raise SecurityError(f"Critical Security Alert: External database target detected in {env_var}: {val}")

# Run local data isolation verification
verify_local_data_isolation(AGENT_DIR)


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fallback_model import FallbackGemini
from security.telemetry import log_agent_call, make_before_callback, make_after_callback

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes required to manage calendar events
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def _read_schedule() -> list:
    """Read events from the local schedule.json file."""
    if not os.path.exists(SCHEDULE_FILE):
        return []
    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _write_schedule(events: list) -> None:
    """Write events to the local schedule.json file."""
    try:
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        print(f"Error writing schedule: {e}")

def get_current_date() -> str:
    """Get the current local date in YYYY-MM-DD format.

    Returns:
        The current local date as a YYYY-MM-DD string.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_agent_call("schedule_agent", "get_current_date()", today)
    return today

def create_calendar_event(summary: str, start_time: str, end_time: str = None, description: str = None) -> str:
    """Create a real event on Google Calendar using OAuth credentials.

    Args:
        summary: Title/summary of the event.
        start_time: Start date/time of the event in ISO 8601 format (e.g., '2026-06-25T15:00:00').
        end_time: Optional end date/time in ISO 8601 format. If not provided, defaults to 1 hour after start_time.
        description: Optional description of the event.

    Returns:
        A confirmation string with the created event link or details.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    creds_path = os.path.join(root_dir, "credentials.json")
    token_path = os.path.join(root_dir, "token.json")
    
    creds = None
    try:
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if creds and creds.valid:
                print(f"[DEBUG] OAuth token loaded successfully from: {token_path}")
            elif creds:
                print(f"[DEBUG] OAuth token loaded from {token_path} but is invalid/expired.")
    except Exception as e:
        print(f"[DEBUG] Error loading OAuth token: {e}")
        
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                print("[DEBUG] Refreshing expired OAuth token...")
                creds.refresh(Request())
                print("[DEBUG] OAuth token refreshed successfully.")
            else:
                if not os.path.exists(creds_path):
                    err_msg = f"Error: credentials.json not found at {creds_path}."
                    print(f"[DEBUG] {err_msg}")
                    return err_msg
                print("[DEBUG] OAuth token not found or invalid. Running local server flow...")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
                print("[DEBUG] Local server flow finished successfully.")
            
            with open(token_path, "w") as token:
                token.write(creds.to_json())
            print(f"[DEBUG] OAuth token saved successfully to: {token_path}")
        except Exception as e:
            err_msg = f"Error during OAuth authentication: {e}"
            print(f"[DEBUG] {err_msg}")
            return err_msg
            
    try:
        print("[DEBUG] Initializing Google Calendar service...")
        import googleapiclient.discovery
        service = googleapiclient.discovery.build("calendar", "v3", credentials=creds)
        
        # Helper to parse datetime
        def parse_datetime(dt_str: str) -> datetime:
            try:
                return datetime.fromisoformat(dt_str)
            except ValueError:
                # Fallback parse formats
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
                    try:
                        return datetime.strptime(dt_str, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Cannot parse datetime '{dt_str}'.")

        try:
            dt_start = parse_datetime(start_time)
        except ValueError as ve:
            err_msg = f"Error parsing start time: {ve}"
            print(f"[DEBUG] {err_msg}")
            return f"Error: {ve} Please use YYYY-MM-DDTHH:MM:SS format."
            
        if end_time:
            try:
                dt_end = parse_datetime(end_time)
            except ValueError as ve:
                err_msg = f"Error parsing end time: {ve}"
                print(f"[DEBUG] {err_msg}")
                return f"Error: {ve} Please use YYYY-MM-DDTHH:MM:SS format."
        else:
            dt_end = dt_start + timedelta(hours=1)
            
        start_date = dt_start.strftime("%Y-%m-%d")
        start_time_val = dt_start.strftime("%H:%M")
        start_time_str = f"{start_date}T{start_time_val}:00+05:30"
        
        end_date = dt_end.strftime("%Y-%m-%d")
        end_time_val = dt_end.strftime("%H:%M")
        end_time_str = f"{end_date}T{end_time_val}:00+05:30"
            
        event_body = {
            'summary': summary,
            'description': description or '',
            'start': {
                'dateTime': start_time_str,
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_time_str,
                'timeZone': 'Asia/Kolkata',
            },
        }
        
        print(f"[DEBUG] API call being made: Inserting event with body: {json.dumps(event_body, indent=2)}")
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        print(f"[DEBUG] Response from Google Calendar API: {json.dumps(event, indent=2)}")
        
        html_link = event.get('htmlLink', '')
        event_id = event.get('id')
        
        # Save event_id in schedule.json
        events = _read_schedule()
        updated = False
        # Find if there is an event with the same title and date (without event_id) and update it
        for e in events:
            if e.get("title").strip().lower() == summary.strip().lower() and e.get("date") == start_date:
                e["event_id"] = event_id
                updated = True
                break
                
        if not updated:
            # If not found, add it directly to schedule.json
            new_event = {
                "title": summary,
                "date": start_date,
                "time": start_time_val,
                "event_id": event_id
            }
            events.append(new_event)
            
        _write_schedule(events)
        
        res = f"Event successfully created: '{summary}' on {start_time_str}. Event ID: {event_id}. Link: {html_link} ✅"
        log_agent_call("schedule_agent", f"create_calendar_event(summary={summary}, start_time={start_time_str})", res)
        return res
    except Exception as e:
        err_msg = f"Error creating calendar event: {e}"
        print(f"[DEBUG] Any errors - Exception encountered: {e}")
        import traceback
        traceback.print_exc()
        log_agent_call("schedule_agent", f"create_calendar_event(summary={summary}, start_time={start_time})", err_msg)
        return err_msg



def add_event(title: str, date: str, time: str, event_id: str = None) -> str:
    """Save an event to the local schedule database.

    Args:
        title: Title/summary of the event.
        date: Date of the event in YYYY-MM-DD format.
        time: Time of the event (e.g. '15:00').
        event_id: Optional Google Calendar event ID.

    Returns:
        A confirmation message indicating the event was saved locally.
    """
    events = _read_schedule()
    # Check if this event already exists (we might have added it in create_calendar_event)
    for e in events:
        if e.get("title").strip().lower() == title.strip().lower() and e.get("date") == date:
            if event_id:
                e["event_id"] = event_id
            _write_schedule(events)
            res = f"Updated local schedule backup for '{title}' on {date} at {time} ✅"
            log_agent_call("schedule_agent", f"add_event(title={title}, date={date}, time={time})", res)
            return res
            
    new_event = {
        "title": title,
        "date": date,
        "time": time
    }
    if event_id:
        new_event["event_id"] = event_id
    events.append(new_event)
    _write_schedule(events)
    res = f"Saved '{title}' on {date} at {time} to local schedule backup ✅"
    log_agent_call("schedule_agent", f"add_event(title={title}, date={date}, time={time})", res)
    return res

def list_events() -> str:
    """List all scheduled events from the database.

    Returns:
        A formatted string listing all events, or a message indicating there are none.
    """
    events = _read_schedule()
    if not events:
        res = "No scheduled events found in backup! 📅"
        log_agent_call("schedule_agent", "list_events()", res)
        return res
        
    result = "Here is the list of all scheduled events:\n"
    for e in events:
        result += f"- {e.get('title')} on {e.get('date')} at {e.get('time')}\n"
    res = result.strip()
    log_agent_call("schedule_agent", "list_events()", res)
    return res

def list_today_events() -> str:
    """List scheduled events for today.

    Returns:
        A formatted string listing today's events, or a message indicating there are none.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    events = _read_schedule()
    today_events = [e for e in events if e.get("date") == today_str]
    
    if not today_events:
        res = f"No events scheduled for today ({today_str})."
        log_agent_call("schedule_agent", "list_today_events()", res)
        return res
        
    result = f"Here are your scheduled events for today ({today_str}):\n"
    for e in today_events:
        result += f"- {e.get('title')} at {e.get('time')}\n"
    res = result.strip()
    log_agent_call("schedule_agent", "list_today_events()", res)
    return res

def delete_event(title: str) -> str:
    """Remove an event by its title from the local schedule database and Google Calendar.

    Args:
        title: The exact or partial title of the event to delete.

    Returns:
        A confirmation message indicating the event was removed, or an error if not found.
    """
    events = _read_schedule()
    found_event = None
    
    # Try exact case-insensitive match first
    title_clean = title.strip().lower()
    for e in events:
        if e.get("title").strip().lower() == title_clean:
            found_event = e
            break
            
    # Try partial match if exact match not found
    if not found_event:
        for e in events:
            if title_clean in e.get("title").lower():
                found_event = e
                break
                
    if not found_event:
        res = f"Error: Could not find any event matching '{title}'."
        log_agent_call("schedule_agent", f"delete_event(title={title})", res)
        return res
        
    # Get the event_id from the found event
    event_id = found_event.get("event_id")
    google_deleted = False
    google_err = ""
    
    if event_id:
        # Authenticate and delete from Google Calendar
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        creds_path = os.path.join(root_dir, "credentials.json")
        token_path = os.path.join(root_dir, "token.json")
        
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if os.path.exists(creds_path):
                    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
            if creds:
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
                    
        if creds:
            try:
                service = build("calendar", "v3", credentials=creds)
                service.events().delete(calendarId='primary', eventId=event_id).execute()
                google_deleted = True
            except Exception as e:
                google_err = str(e)
                
    # Remove from local list
    events.remove(found_event)
    _write_schedule(events)
    
    if event_id:
        if google_deleted:
            res = f"Successfully removed event '{found_event.get('title')}' from local database and Google Calendar ✅"
        else:
            res = f"Successfully removed event '{found_event.get('title')}' from local database, but failed to delete from Google Calendar: {google_err} ⚠️"
    else:
        res = f"Successfully removed event '{found_event.get('title')}' from local database (no Google Calendar event ID found to sync deletion) ⚠️"
        
    log_agent_call("schedule_agent", f"delete_event(title={title})", res)
    return res

# Create the Schedule Agent using custom tools
schedule_agent = Agent(
    name="schedule_agent",
    model=FallbackGemini(),
    description=(
        "Agent for managing personal schedule. It can add events, list events, "
        "list today's events, and delete events both locally and on Google Calendar."
    ),
    instruction="""
    You are the Schedule Agent for LifeOS. Your primary responsibility is to manage the user's schedule.
    
    You have 6 tools available:
    1. get_current_date:
       - Use this tool to get the current date in YYYY-MM-DD format. You MUST call this tool first before scheduling any event to calculate relative dates (e.g. "tomorrow", "next week") correctly.
    2. create_calendar_event:
       - Use this tool to create new events directly on the user's real Google Calendar via OAuth credentials.
    3. add_event:
       - Use this tool to save a backup of the event locally in `schedule.json`.
    4. list_events:
       - Use this tool to list all events from the local database.
    5. list_today_events:
       - Use this tool to show today's events from the local database.
    6. delete_event:
       - Use this tool to delete an event by title from the local database and Google Calendar.
       
    Rules of engagement:
    1. Whenever the user schedules a new event (e.g., "schedule meeting at 3pm tomorrow"), you MUST call BOTH `create_calendar_event` (to add it to Google Calendar) AND `add_event` (to save it to local schedule.json) in the same workflow.
    2. Relative Dates: Always run `get_current_date` first before resolving relative dates like "tomorrow".
    3. Always confirm to the user after completing every action successfully.
    4. Be friendly, polite, clear, and structured in your responses.
    """,
    tools=[get_current_date, create_calendar_event, add_event, list_events, list_today_events, delete_event],
    before_agent_callback=make_before_callback("schedule_agent"),
    after_agent_callback=make_after_callback("schedule_agent")
)
