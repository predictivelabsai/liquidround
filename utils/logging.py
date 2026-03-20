"""
Logging utilities for LiquidRound system.
"""
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class LiquidRoundLogger:
    """Custom logger for LiquidRound system."""
    
    def __init__(self, name: str = "liquidround", log_dir: str = "logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up logging handlers."""
        # File handler for general logs
        log_file = self.log_dir / f"{self.name}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # File handler for agent traces
        trace_file = self.log_dir / f"{self.name}_traces.log"
        trace_handler = logging.FileHandler(trace_file)
        trace_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        trace_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(trace_handler)
        self.logger.addHandler(console_handler)
        
        # Store trace handler for agent logging
        self.trace_handler = trace_handler
    
    def log_agent_execution(
        self,
        agent_name: str,
        action: str,
        input_data: Any = None,
        output_data: Any = None,
        execution_time: float = None,
        error: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log agent execution details."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "action": action,
            "input_data": self._serialize_data(input_data),
            "output_data": self._serialize_data(output_data),
            "execution_time": execution_time,
            "error": error,
            "metadata": metadata or {}
        }
        
        log_message = f"AGENT_TRACE: {json.dumps(log_entry, indent=2)}"
        self.logger.debug(log_message)
        
        # Also save to dedicated agent log file
        agent_log_file = self.log_dir / f"agent_{agent_name}.log"
        with open(agent_log_file, "a") as f:
            f.write(f"{log_message}\n")
    
    def log_workflow_step(
        self,
        workflow_name: str,
        step: str,
        state_snapshot: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        """Log workflow execution steps."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "workflow_name": workflow_name,
            "step": step,
            "state_snapshot": self._serialize_data(state_snapshot),
            "metadata": metadata or {}
        }
        
        log_message = f"WORKFLOW: {json.dumps(log_entry, indent=2)}"
        self.logger.info(log_message)
    
    def log_user_interaction(
        self,
        user_id: str,
        action: str,
        input_data: Any = None,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log user interactions."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "action": action,
            "input_data": self._serialize_data(input_data),
            "metadata": metadata or {}
        }
        
        log_message = f"USER_INTERACTION: {json.dumps(log_entry, indent=2)}"
        self.logger.info(log_message)
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Dict[str, Any] = None,
        stack_trace: str = None
    ):
        """Log errors with context."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "stack_trace": stack_trace
        }
        
        log_message = f"ERROR: {json.dumps(log_entry, indent=2)}"
        self.logger.error(log_message)
    
    def _serialize_data(self, data: Any) -> Any:
        """Serialize data for logging."""
        if data is None:
            return None
        
        try:
            # Try to serialize as JSON
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            # If not serializable, convert to string
            return str(data)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, **kwargs)


# Global logger instance
logger = LiquidRoundLogger()


def get_logger(name: str = "liquidround") -> LiquidRoundLogger:
    """Get a logger instance."""
    return LiquidRoundLogger(name)
