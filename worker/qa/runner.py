"""Docker-based test runner for QA validation."""

import io
import json
import logging
import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import docker
from docker.types import LogConfig

logger = logging.getLogger(__name__)


class TestRunner:
    """Runs tests in isolated Docker containers."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
    
    def run_pytest(
        self,
        workspace_tar_data: bytes,
        test_command: str = "pytest -v",
        timeout: int = 600
    ) -> dict:
        """
        Run pytest tests in a Docker container.
        
        Args:
            workspace_tar_data: Tarball of workspace
            test_command: Command to run tests
            timeout: Maximum execution time in seconds
        
        Returns:
            Dictionary with test results
        """
        container = None
        
        try:
            # Create a temporary directory for workspace
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                
                # Extract tarball
                with tarfile.open(fileobj=io.BytesIO(workspace_tar_data)) as tar:
                    tar.extractall(tmpdir_path)
                
                # Find workspace root (might be in a subdirectory)
                workspace_root = tmpdir_path
                subdirs = list(tmpdir_path.iterdir())
                if len(subdirs) == 1 and subdirs[0].is_dir():
                    workspace_root = subdirs[0]
                
                logger.info(f"Extracted workspace to {workspace_root}")
                
                # Build Docker image with workspace
                image_tag = self._build_pytest_image(workspace_root)
                
                # Run tests in container
                result = self._run_container(
                    image_tag,
                    test_command,
                    timeout
                )
                
                # Parse pytest output
                parsed_result = self._parse_pytest_output(
                    result["stdout"],
                    result["exit_code"]
                )
                
                return {
                    "framework": "pytest",
                    "tests_passed": result["exit_code"] == 0,
                    "num_passed": parsed_result["num_passed"],
                    "num_failed": parsed_result["num_failed"],
                    "runtime_s": result["runtime_s"],
                    "exit_code": result["exit_code"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                    "container_image": image_tag
                }
        
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {
                "framework": "pytest",
                "tests_passed": False,
                "num_passed": 0,
                "num_failed": 0,
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }
        
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
    
    def _build_pytest_image(self, workspace_path: Path) -> str:
        """Build Docker image with the workspace."""
        # Create Dockerfile
        dockerfile_content = """
FROM python:3.11-slim

WORKDIR /workspace

# Install common dependencies
RUN pip install --no-cache-dir pytest pytest-json-report

# Copy workspace
COPY . /workspace/

# Install project dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN if [ -f setup.py ]; then pip install --no-cache-dir -e .; fi

# Create non-root user
RUN useradd -m -u 1000 testuser && chown -R testuser:testuser /workspace
USER testuser

CMD ["pytest", "-v"]
"""
        
        dockerfile_path = workspace_path / "Dockerfile.test"
        dockerfile_path.write_text(dockerfile_content)
        
        # Build image
        image_tag = f"pr-telemetry-test:{workspace_path.name}"
        
        logger.info(f"Building Docker image: {image_tag}")
        
        try:
            image, build_logs = self.docker_client.images.build(
                path=str(workspace_path),
                dockerfile="Dockerfile.test",
                tag=image_tag,
                rm=True,
                forcerm=True
            )
            
            for log in build_logs:
                if "stream" in log:
                    logger.debug(log["stream"].strip())
            
            return image_tag
        
        except docker.errors.BuildError as e:
            logger.error(f"Docker build failed: {e}")
            raise
    
    def _run_container(
        self,
        image_tag: str,
        command: str,
        timeout: int
    ) -> dict:
        """Run command in container with security restrictions."""
        import time
        
        start_time = time.time()
        
        # Security settings
        container = self.docker_client.containers.run(
            image_tag,
            command=command,
            detach=True,
            remove=False,
            network_mode="none",  # No network access
            mem_limit="1g",  # 1GB memory limit
            cpu_period=100000,
            cpu_quota=200000,  # 2 CPU cores max
            pids_limit=100,  # Limit number of processes
            security_opt=["no-new-privileges"],
            cap_drop=["ALL"],
            read_only=False,  # Need write for test artifacts
            user="testuser"
        )
        
        try:
            # Wait for container to finish
            result = container.wait(timeout=timeout)
            exit_code = result["StatusCode"]
            
            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            
            runtime_s = time.time() - start_time
            
            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "runtime_s": runtime_s
            }
        
        finally:
            container.remove(force=True)
    
    def _parse_pytest_output(self, stdout: str, exit_code: int) -> dict:
        """Parse pytest output to extract test counts."""
        num_passed = 0
        num_failed = 0
        
        # Look for pytest summary line
        # Format: "X passed, Y failed in Z seconds"
        for line in stdout.split("\n"):
            line_lower = line.lower()
            
            if "passed" in line_lower:
                try:
                    parts = line_lower.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            num_passed = int(parts[i-1])
                        elif part == "failed":
                            num_failed = int(parts[i-1])
                except (ValueError, IndexError):
                    pass
        
        # Fallback: if exit code is 0, assume at least 1 test passed
        if exit_code == 0 and num_passed == 0:
            num_passed = 1
        
        return {
            "num_passed": num_passed,
            "num_failed": num_failed
        }

