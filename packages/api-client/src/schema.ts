export interface paths {
    "/api/v1/auth/token": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["token_api_v1_auth_token_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["refresh_api_v1_auth_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["me_api_v1_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["list_users_api_v1_admin_users_get"];
        put?: never;
        post: operations["create_user_api_v1_admin_users_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/users/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete: operations["archive_user_api_v1_admin_users__user_id__delete"];
        options?: never;
        head?: never;
        patch: operations["update_user_api_v1_admin_users__user_id__patch"];
        trace?: never;
    };
    "/api/v1/admin/users/{user_id}/reset-password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["reset_password_api_v1_admin_users__user_id__reset_password_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/users/{user_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["restore_user_api_v1_admin_users__user_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/resources/nodes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["nodes_api_v1_resources_nodes_get"];
        put?: never;
        post: operations["create_node_api_v1_resources_nodes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/resources/nodes/{node_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete: operations["archive_node_api_v1_resources_nodes__node_id__delete"];
        options?: never;
        head?: never;
        patch: operations["update_node_api_v1_resources_nodes__node_id__patch"];
        trace?: never;
    };
    "/api/v1/resources/nodes/{node_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["restore_node_api_v1_resources_nodes__node_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/resources/services": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["services_api_v1_resources_services_get"];
        put?: never;
        post: operations["create_service_api_v1_resources_services_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/resources/services/{service_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete: operations["archive_service_api_v1_resources_services__service_id__delete"];
        options?: never;
        head?: never;
        patch: operations["update_service_api_v1_resources_services__service_id__patch"];
        trace?: never;
    };
    "/api/v1/resources/services/{service_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["restore_service_api_v1_resources_services__service_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/resources/dependencies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["dependencies_api_v1_resources_dependencies_get"];
        put?: never;
        post: operations["create_dependency_api_v1_resources_dependencies_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/resources/dependencies/{dependency_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete: operations["archive_dependency_api_v1_resources_dependencies__dependency_id__delete"];
        options?: never;
        head?: never;
        patch: operations["update_dependency_api_v1_resources_dependencies__dependency_id__patch"];
        trace?: never;
    };
    "/api/v1/resources/dependencies/{dependency_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["restore_dependency_api_v1_resources_dependencies__dependency_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/incidents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["incidents_api_v1_incidents_get"];
        put?: never;
        post: operations["create_incident_api_v1_incidents_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/incidents/{incident_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["incident_api_v1_incidents__incident_id__get"];
        put?: never;
        post?: never;
        delete: operations["archive_incident_api_v1_incidents__incident_id__delete"];
        options?: never;
        head?: never;
        patch: operations["update_incident_api_v1_incidents__incident_id__patch"];
        trace?: never;
    };
    "/api/v1/incidents/{incident_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["restore_incident_api_v1_incidents__incident_id__restore_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/audit-logs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["audit_logs_api_v1_audit_logs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/healthz": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["healthz_healthz_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/overview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["overview_api_v1_overview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["system_status_api_v1_system_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/internal/v1/alerts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["receive_alerts_internal_v1_alerts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/incidents/{incident_id}/diagnose": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["run_diagnosis_api_v1_incidents__incident_id__diagnose_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/chat/sessions/{session_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["chat_api_v1_chat_sessions__session_id__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/incidents/{incident_id}/actions/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["preview_action_api_v1_incidents__incident_id__actions_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/action-requests/{action_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["approve_action_api_v1_action_requests__action_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/agent/v1/enroll": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["enroll_agent_agent_v1_enroll_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/agent/v1/actions/next": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["next_action_agent_v1_actions_next_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/agent/v1/telemetry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["ingest_telemetry_agent_v1_telemetry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/agent/v1/actions/{action_id}/result": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post: operations["action_result_agent_v1_actions__action_id__result_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/evaluations/runs/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["evaluation_run_api_v1_evaluations_runs__run_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/evaluations/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get: operations["evaluation_runs_api_v1_evaluations_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        ActionPreview: {
            node_id: string;
            action_name: string;
            parameters?: {
                [key: string]: unknown;
            };
        };
        ActionResponse: {
            id: string;
            incident_id: string;
            node_id: string;
            action_name: string;
            parameters: {
                [key: string]: unknown;
            };
            created_at: string;
            expires_at: string;
            status: string;
            approved_by?: string | null;
            approved_at?: string | null;
            risk?: string | null;
            prechecks?: string[] | null;
            rollback?: string | null;
        };
        ActionResult: {
            exit_code: number;
            stdout: string;
            stderr: string;
            health_check: "passed" | "failed";
        };
        Alert: {
            status: "firing" | "resolved";
            labels: {
                [key: string]: string;
            };
            annotations?: {
                [key: string]: string;
            };
            startsAt: string;
            fingerprint: string;
        };
        AlertWebhook: {
            status: "firing" | "resolved";
            alerts: components["schemas"]["Alert"][];
        };
        AuditLogPage: {
            items: components["schemas"]["AuditLogResponse"][];
            total: number;
            page: number;
            page_size: number;
        };
        AuditLogResponse: {
            id: string;
            actor_id: string;
            action: string;
            target: string;
            request_id: string;
            details: {
                [key: string]: unknown;
            };
            created_at: string;
        };
        AuthUser: {
            id: string;
            role: "admin" | "operator" | "viewer" | "agent";
            username?: string | null;
            display_name?: string | null;
        };
        Body_token_api_v1_auth_token_post: {
            username: string;
            password: string;
        };
        ChatMessage: {
            message: string;
            incident_id?: string | null;
        };
        ComponentStatus: {
            status: "available" | "degraded" | "unconfigured" | "unreachable";
            detail: string;
            backend?: string | null;
            model?: string | null;
        };
        DependencyCreate: {
            source_service_id: string;
            target_service_id: string;
        };
        DependencyPage: {
            items: components["schemas"]["DependencyResponse"][];
            total: number;
            page: number;
            page_size: number;
        };
        DependencyResponse: {
            id: number;
            source_service_id: string;
            target_service_id: string;
            source: string;
            confidence: number;
            observed_at: string;
            version: number;
            archived_at?: string | null;
        };
        DependencyUpdate: {
            source_service_id?: string | null;
            target_service_id?: string | null;
        };
        DiagnosisResponse: {
            summary: string;
            root_cause: string;
            severity: string;
            propagation_path: string[];
            evidence_refs: string[];
            recommended_steps: string[];
            action_candidates: string[];
            confidence: number;
            source: string;
        };
        Enrollment: {
            node_id: string;
            hostname: string;
            architecture: string;
            kylin_version: string;
        };
        EvidenceResponse: {
            id: string;
            kind: string;
            node_id: string;
            summary: string;
            observed_at: string;
        };
        HTTPValidationError: {
            detail?: components["schemas"]["ValidationError"][];
        };
        IncidentCreate: {
            title: string;
            fault_type: string;
            severity: "low" | "medium" | "high" | "critical";
            root_node_id?: string | null;
            assignee_user_id?: string | null;
            handling_notes: string;
        };
        IncidentPage: {
            items: components["schemas"]["IncidentResponse"][];
            total: number;
            page: number;
            page_size: number;
        };
        IncidentResponse: {
            id: string;
            title: string;
            fault_type: string;
            severity: string;
            status: string;
            source: string;
            started_at: string;
            ended_at?: string | null;
            root_node?: string | null;
            assignee_user_id?: string | null;
            handling_notes: string;
            version: number;
            archived_at?: string | null;
            propagation_path: string[];
            evidence: components["schemas"]["EvidenceResponse"][];
            diagnosis: components["schemas"]["DiagnosisResponse"];
        };
        IncidentUpdate: {
            title?: string | null;
            fault_type?: string | null;
            severity?: ("low" | "medium" | "high" | "critical") | null;
            status?: ("open" | "acknowledged" | "resolving" | "resolved") | null;
            root_node_id?: string | null;
            assignee_user_id?: string | null;
            handling_notes?: string | null;
        };
        NodeCreate: {
            id: string;
            display_name: string;
            description: string;
            tags?: string[];
            enabled: boolean;
        };
        NodePage: {
            items: components["schemas"]["NodeResponse"][];
            total: number;
            page: number;
            page_size: number;
        };
        NodeResponse: {
            id: string;
            display_name: string;
            description: string;
            tags: string[];
            enabled: boolean;
            hostname?: string | null;
            architecture?: string | null;
            kylin_version?: string | null;
            status: string;
            last_seen_at?: string | null;
            version: number;
            archived_at?: string | null;
        };
        NodeUpdate: {
            display_name?: string | null;
            description?: string | null;
            tags?: string[] | null;
            enabled?: boolean | null;
        };
        OverviewNodeResponse: {
            id: string;
            hostname: string;
            status: string;
            service?: string | null;
            architecture?: string | null;
            kylin_version?: string | null;
            last_seen_at?: string | null;
            metrics?: {
                [key: string]: number;
            };
        };
        OverviewResponse: {
            online_nodes: number;
            total_nodes: number;
            active_incidents: number;
            today_alerts: number;
            pending_actions: number;
            nodes: components["schemas"]["OverviewNodeResponse"][];
            topology: components["schemas"]["TopologyEdgeResponse"][];
        };
        PasswordReset: {
            password: string;
        };
        ServiceCreate: {
            id: string;
            node_id: string;
            name: string;
            service_type: string;
            description: string;
            enabled: boolean;
        };
        ServicePage: {
            items: components["schemas"]["ServiceResponse"][];
            total: number;
            page: number;
            page_size: number;
        };
        ServiceResponse: {
            id: string;
            node_id: string;
            name: string;
            service_type: string;
            description: string;
            enabled: boolean;
            status: string;
            version: number;
            archived_at?: string | null;
        };
        ServiceUpdate: {
            node_id?: string | null;
            name?: string | null;
            service_type?: string | null;
            description?: string | null;
            enabled?: boolean | null;
        };
        SystemStatus: {
            checked_at: string;
            components: {
                [key: string]: components["schemas"]["ComponentStatus"];
            };
        };
        TelemetryBatch: {
            node_id: string;
            observed_at: string;
            metrics: {
                [key: string]: number;
            };
        };
        TopologyEdgeResponse: {
            source: string;
            target: string;
            confidence: number;
        };
        UserCreate: {
            username: string;
            display_name: string;
            password: string;
            role: "admin" | "operator" | "viewer";
        };
        UserPage: {
            items: components["schemas"]["UserResponse"][];
            total: number;
            page: number;
            page_size: number;
        };
        UserResponse: {
            id: string;
            username: string;
            display_name: string;
            role: "admin" | "operator" | "viewer";
            is_active: boolean;
            version: number;
            created_at: string;
            updated_at: string;
            archived_at?: string | null;
        };
        UserUpdate: {
            display_name?: string | null;
            role?: ("admin" | "operator" | "viewer") | null;
            is_active?: boolean | null;
        };
        ValidationError: {
            loc: (string | number)[];
            msg: string;
            type: string;
            input?: unknown;
            ctx?: Record<string, never>;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    token_api_v1_auth_token_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/x-www-form-urlencoded": components["schemas"]["Body_token_api_v1_auth_token_post"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_api_v1_auth_refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                refresh_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout_api_v1_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                refresh_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    me_api_v1_auth_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthUser"];
                };
            };
        };
    };
    list_users_api_v1_admin_users_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
                q?: string | null;
                include_archived?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserPage"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_user_api_v1_admin_users_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_user_api_v1_admin_users__user_id__delete: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_user_api_v1_admin_users__user_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserUpdate"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reset_password_api_v1_admin_users__user_id__reset_password_post: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordReset"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_user_api_v1_admin_users__user_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    nodes_api_v1_resources_nodes_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
                q?: string | null;
                include_archived?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodePage"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_node_api_v1_resources_nodes_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NodeCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodeResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_node_api_v1_resources_nodes__node_id__delete: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                node_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodeResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_node_api_v1_resources_nodes__node_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                node_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NodeUpdate"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodeResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_node_api_v1_resources_nodes__node_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                node_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["NodeResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    services_api_v1_resources_services_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
                q?: string | null;
                include_archived?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ServicePage"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_service_api_v1_resources_services_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ServiceCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ServiceResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_service_api_v1_resources_services__service_id__delete: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                service_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ServiceResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_service_api_v1_resources_services__service_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                service_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ServiceUpdate"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ServiceResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_service_api_v1_resources_services__service_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                service_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ServiceResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    dependencies_api_v1_resources_dependencies_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
                include_archived?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DependencyPage"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_dependency_api_v1_resources_dependencies_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DependencyCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DependencyResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_dependency_api_v1_resources_dependencies__dependency_id__delete: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                dependency_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DependencyResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_dependency_api_v1_resources_dependencies__dependency_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                dependency_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DependencyUpdate"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DependencyResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_dependency_api_v1_resources_dependencies__dependency_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                dependency_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DependencyResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    incidents_api_v1_incidents_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
                status?: string | null;
                source?: string | null;
                include_archived?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncidentPage"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_incident_api_v1_incidents_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IncidentCreate"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncidentResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    incident_api_v1_incidents__incident_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncidentResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_incident_api_v1_incidents__incident_id__delete: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncidentResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_incident_api_v1_incidents__incident_id__patch: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IncidentUpdate"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncidentResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restore_incident_api_v1_incidents__incident_id__restore_post: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IncidentResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    audit_logs_api_v1_audit_logs_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
                actor_id?: string | null;
                action?: string | null;
                target?: string | null;
                created_from?: string | null;
                created_to?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditLogPage"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    healthz_healthz_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
    overview_api_v1_overview_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OverviewResponse"];
                };
            };
        };
    };
    system_status_api_v1_system_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemStatus"];
                };
            };
        };
    };
    receive_alerts_internal_v1_alerts_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AlertWebhook"];
            };
        };
        responses: {
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_diagnosis_api_v1_incidents__incident_id__diagnose_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DiagnosisResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    chat_api_v1_chat_sessions__session_id__messages_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChatMessage"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    preview_action_api_v1_incidents__incident_id__actions_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                incident_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActionPreview"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ActionResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_action_api_v1_action_requests__action_id__approve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                action_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ActionResponse"];
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    enroll_agent_agent_v1_enroll_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["Enrollment"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    next_action_agent_v1_actions_next_get: {
        parameters: {
            query: {
                node_id: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ingest_telemetry_agent_v1_telemetry_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TelemetryBatch"];
            };
        };
        responses: {
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    action_result_agent_v1_actions__action_id__result_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                action_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ActionResult"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    evaluation_run_api_v1_evaluations_runs__run_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    evaluation_runs_api_v1_evaluations_runs_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
}
