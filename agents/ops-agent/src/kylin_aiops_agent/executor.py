import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime

from kylin_aiops_api.actions import ActionEnvelope, ExecutionGuard


class UnsafeAction(ValueError):
    pass


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SAFE_INTERFACE = re.compile(r"^(eth|ens|enp)[A-Za-z0-9_.-]{1,31}$")


@dataclass(frozen=True)
class PreparedCommand:
    argv: list[str]
    precheck_argv: list[str] | None = None
    healthcheck_argv: list[str] | None = None
    shell: bool = field(default=False, init=False)


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    health_check: str


class AllowlistedExecutor:
    def __init__(self, node_id: str, guard: ExecutionGuard) -> None:
        self.node_id = node_id
        self.guard = guard

    def prepare(self, envelope: ActionEnvelope, now: datetime) -> PreparedCommand:
        self.guard.verify(envelope, node_id=self.node_id, now=now)
        params = envelope.parameters
        action = envelope.action_name

        if action == "restart_demo_service":
            if params != {"service": "kylin-demo-app"}:
                raise UnsafeAction("Only the kylin-demo-app service can be restarted")
            return PreparedCommand(
                argv=["/usr/bin/systemctl", "restart", "kylin-demo-app.service"],
                healthcheck_argv=["/usr/bin/systemctl", "is-active", "kylin-demo-app.service"],
            )
        if action == "reload_nginx":
            if params != {"service": "nginx"}:
                raise UnsafeAction("Only the nginx service can be reloaded")
            return PreparedCommand(
                precheck_argv=["/usr/sbin/nginx", "-t"],
                argv=["/usr/bin/systemctl", "reload", "nginx.service"],
                healthcheck_argv=["/usr/bin/systemctl", "is-active", "nginx.service"],
            )
        if action in {"stop_fault_stressor", "remove_fault_file"}:
            experiment_id = str(params.get("experiment_id", ""))
            if not SAFE_ID.fullmatch(experiment_id):
                raise UnsafeAction("Invalid experiment identifier")
            wrapper = (
                "stop-fault-stressor" if action == "stop_fault_stressor" else "remove-fault-file"
            )
            expected = {"experiment_id"} if action == "stop_fault_stressor" else {
                "experiment_id",
                "filename",
            }
            if set(params) != expected:
                raise UnsafeAction("Unexpected action parameters")
            if action == "remove_fault_file" and params["filename"] != "disk-fill.bin":
                raise UnsafeAction("Only the controlled disk-fill file can be removed")
            argv = [f"/usr/local/libexec/kylin-aiops/{wrapper}", experiment_id]
            if action == "remove_fault_file":
                argv.append("disk-fill.bin")
            return PreparedCommand(argv=argv)
        if action == "clear_fault_netem":
            experiment_id = str(params.get("experiment_id", ""))
            interface = str(params.get("interface", ""))
            if not SAFE_ID.fullmatch(experiment_id) or not SAFE_INTERFACE.fullmatch(interface):
                raise UnsafeAction("Invalid experiment or network interface")
            if set(params) != {"experiment_id", "interface"}:
                raise UnsafeAction("Unexpected action parameters")
            return PreparedCommand(
                argv=[
                    "/usr/local/libexec/kylin-aiops/clear-fault-netem",
                    experiment_id,
                    interface,
                ]
            )
        if action == "terminate_fault_db_sessions":
            if params != {"db_user": "ops_fault"}:
                raise UnsafeAction("Only ops_fault database sessions can be terminated")
            return PreparedCommand(
                argv=["/usr/local/libexec/kylin-aiops/terminate-fault-db-sessions", "ops_fault"]
            )
        raise UnsafeAction(f"Action {action!r} is not allowlisted")

    def execute(self, envelope: ActionEnvelope, now: datetime) -> ExecutionResult:
        command = self.prepare(envelope, now)
        if command.precheck_argv:
            precheck = subprocess.run(
                command.precheck_argv, shell=False, check=False, capture_output=True, text=True
            )
            if precheck.returncode != 0:
                return ExecutionResult(
                    exit_code=precheck.returncode,
                    stdout=precheck.stdout,
                    stderr=precheck.stderr,
                    health_check="failed",
                )
        result = subprocess.run(
            command.argv, shell=False, check=False, capture_output=True, text=True, timeout=30
        )
        health = "passed"
        if command.healthcheck_argv:
            health_result = subprocess.run(
                command.healthcheck_argv,
                shell=False,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            health = "passed" if health_result.returncode == 0 else "failed"
        if result.returncode == 0 and health == "passed":
            self.guard.mark_executed(envelope.action_id)
        return ExecutionResult(result.returncode, result.stdout, result.stderr, health)
