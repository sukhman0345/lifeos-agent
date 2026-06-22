import os
import logging
from datetime import datetime
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

# Create directory for logs if it doesn't exist
SECURITY_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE_PATH = os.path.join(SECURITY_DIR, "telemetry.log")

# Setup standard logger
logger = logging.getLogger("agent_telemetry")
logger.setLevel(logging.INFO)

# Avoid adding multiple handlers if already configured
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Also log to console for debugging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Initialize OpenTelemetry Tracer
provider = TracerProvider()
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("lifeos.agent.telemetry")

def log_agent_call(agent_name: str, action: str, result: str) -> None:
    """Logs an agent invocation with details using OpenTelemetry and a local log file."""
    timestamp = datetime.utcnow().isoformat()
    
    # Log using OpenTelemetry Trace API
    with tracer.start_as_current_span(name=f"AgentCall-{agent_name}") as span:
        span.set_attribute("agent.name", agent_name)
        span.set_attribute("agent.action", action)
        span.set_attribute("agent.timestamp", timestamp)
        span.set_attribute("agent.result", result)
        
        # Log to file
        log_msg = f"Agent: {agent_name} | Action: {action} | Timestamp: {timestamp} | Result: {result}"
        logger.info(log_msg)

def make_before_callback(agent_name: str):
    """Creates a before_agent_callback for ADK Agents."""
    def before_callback(callback_context=None, **kwargs):
        log_agent_call(
            agent_name=agent_name,
            action="started_execution",
            result="Pending"
        )
        return None
    return before_callback

def make_after_callback(agent_name: str):
    """Creates an after_agent_callback for ADK Agents."""
    def after_callback(callback_context=None, **kwargs):
        result = "Success"
        if callback_context and callback_context.session and callback_context.session.events:
            # Try to get the last agent message content
            for ev in reversed(callback_context.session.events):
                if ev.content and ev.content.parts:
                    parts_txt = [p.text for p in ev.content.parts if p.text]
                    if parts_txt:
                        result = " ".join(parts_txt)
                        break
        log_agent_call(
            agent_name=agent_name,
            action="completed_execution",
            result=result
        )
        return None
    return after_callback
