"""Immich database operations via SSH and Docker."""

import subprocess
import logging
import shlex
from typing import Optional, Dict, Any


class ImmichDatabase:
    """Handles database operations on remote Immich PostgreSQL via SSH/Docker."""
    
    def __init__(
        self,
        ssh_host: str,
        ssh_user: str,
        ssh_port: int = 22,
        container_name: str = "immich_postgres",
        db_user: str = "postgres",
        db_name: str = "immich",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Immich database handler.
        
        Args:
            ssh_host: SSH hostname or IP address
            ssh_user: SSH username
            ssh_port: SSH port (default: 22)
            container_name: Docker container name (default: immich_postgres)
            db_user: PostgreSQL username (default: postgres)
            db_name: Database name (default: immich)
            logger: Optional logger instance
        """
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_port = ssh_port
        self.container_name = container_name
        self.db_user = db_user
        self.db_name = db_name
        self.logger = logger or logging.getLogger(__name__)
    
    def test_ssh_connection(self) -> bool:
        """
        Test SSH connection to the server.
        Allows interactive password entry if needed.
        
        Returns:
            True if connection successful, False otherwise
        """
        import sys
        try:
            self.logger.info(f"Testing SSH connection (you may be prompted for password)...")
            # Don't capture output to allow interactive password prompt
            result = subprocess.run(
                [
                    "ssh",
                    "-p", str(self.ssh_port),
                    "-o", "ConnectTimeout=5",
                    f"{self.ssh_user}@{self.ssh_host}",
                    "echo 'OK'"
                ],
                stdin=sys.stdin,
                stdout=subprocess.PIPE,
                stderr=sys.stderr,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True
            
            self.logger.error(f"SSH connection failed with exit code {result.returncode}")
            return False
            
        except subprocess.TimeoutExpired:
            self.logger.error("SSH connection timeout")
            return False
        except Exception as e:
            self.logger.error(f"SSH connection error: {e}")
            return False
    
    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """
        Execute SQL command on remote Immich database.
        
        Args:
            sql: SQL command to execute
            
        Returns:
            Dictionary with 'success', 'output', and 'error' keys
        """
        import sys
        try:
            # Build the complete docker command as a string that will be executed on remote
            #docker_cmd = f"docker exec {shlex.quote(self.container_name)} psql -U {shlex.quote(self.db_user)} -d {shlex.quote(self.db_name)} -t -c {shlex.quote(sql)}"
            
            # Alternative: Use psql connection string format which handles special chars better
            docker_cmd = f"docker exec {self.container_name} psql postgresql://{self.db_user}@localhost/{shlex.quote(self.db_name)} -t -c {shlex.quote(sql)}"
            
            self.logger.debug(f"Executing SQL: {sql}")
            self.logger.debug(f"Docker command: {docker_cmd}")
            
            # Execute via SSH - allow password prompt
            result = subprocess.run(
                [
                    "ssh",
                    "-p", str(self.ssh_port),
                    f"{self.ssh_user}@{self.ssh_host}",
                    docker_cmd
                ],
                stdin=sys.stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': 'SQL execution timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
    
    def get_deleted_count(self) -> Optional[int]:
        """
        Get count of deleted assets in database.
        
        Returns:
            Number of deleted assets, or None if query failed
        """
        result = self.execute_sql(
            'SELECT COUNT(*) FROM asset WHERE "deletedAt" IS NOT NULL;'
        )
        
        if not result['success']:
            self.logger.error(f"Failed to query deleted count: {result['error']}")
            return None
        
        try:
            # Parse output like "count\n-----\n   48\n(1 row)"
            lines = result['output'].strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.isdigit():
                    return int(line)
            return None
        except Exception as e:
            self.logger.error(f"Error parsing deleted count: {e}")
            return None
    
    def clear_deletion_records(self) -> Dict[str, Any]:
        """
        Clear deletedAt timestamps from all assets.
        
        Returns:
            Dictionary with 'success', 'affected_rows', and 'error' keys
        """
        # Get count before clearing
        before_count = self.get_deleted_count()
        
        if before_count is None:
            return {
                'success': False,
                'affected_rows': 0,
                'error': 'Failed to query initial deleted count'
            }
        
        self.logger.info(f"Found {before_count} deleted assets")
        
        if before_count == 0:
            return {
                'success': True,
                'affected_rows': 0,
                'error': None
            }
        
        # Execute the UPDATE
        result = self.execute_sql(
            'UPDATE asset SET "deletedAt" = NULL WHERE "deletedAt" IS NOT NULL;'
        )
        
        if not result['success']:
            return {
                'success': False,
                'affected_rows': 0,
                'error': result['error']
            }
        
        # Verify the update
        after_count = self.get_deleted_count()
        
        if after_count is None:
            return {
                'success': False,
                'affected_rows': 0,
                'error': 'Failed to verify deletion was cleared'
            }
        
        affected_rows = before_count - after_count
        
        return {
            'success': True,
            'affected_rows': affected_rows,
            'error': None
        }
