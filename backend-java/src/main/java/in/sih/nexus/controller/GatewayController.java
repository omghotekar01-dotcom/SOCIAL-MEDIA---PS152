package in.sih.nexus.controller;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

@RestController
@RequestMapping("/api/gateway")
public class GatewayController {

    private final RestClient fastApi;

    public GatewayController(RestClient fastApiClient) {
        this.fastApi = fastApiClient;
    }

    @GetMapping("/health")
    public ResponseEntity<?> health() {
        try {
            String downstream = fastApi.get().uri("/health").retrieve().body(String.class);
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("status", "ok");
            body.put("service", "nexus-gateway");
            body.put("time", Instant.now().toString());
            body.put("analytics", downstream);
            return ResponseEntity.ok(body);
        } catch (Exception ex) {
            return ResponseEntity.status(503).body(Map.of(
                    "status", "degraded",
                    "service", "nexus-gateway",
                    "detail", "FastAPI analytics service is not reachable"
            ));
        }
    }

    @GetMapping("/session/demo")
    public Map<String, Object> demoSession() {
        return Map.of(
                "mode", "DEMO",
                "role", "ANALYST",
                "displayName", "SIH Demo Analyst",
                "permissions", new String[]{"READ_ANALYTICS", "RUN_CONNECTORS", "EXPORT_EVIDENCE"},
                "warning", "Demo session only. Replace with organization SSO/OIDC in production."
        );
    }

    @GetMapping({
            "/api/connectors/status",
            "/api/overview",
            "/api/timeline",
            "/api/trends",
            "/api/narratives",
            "/api/network",
            "/api/demographics",
            "/api/alerts",
            "/api/events",
            "/api/certificates"
    })
    public ResponseEntity<String> proxyGet(
            jakarta.servlet.http.HttpServletRequest request,
            @RequestParam Map<String, String> query
    ) {
        String downstreamPath = request.getRequestURI().substring("/api/gateway".length());
        return get(downstreamPath, query);
    }

    @GetMapping("/api/narratives/{id}")
    public ResponseEntity<String> narrative(@PathVariable String id) {
        return get("/api/narratives/" + id, Map.of());
    }

    @GetMapping("/api/events/{id}")
    public ResponseEntity<String> event(@PathVariable String id) {
        return get("/api/events/" + id, Map.of());
    }

    @GetMapping("/api/certificates/narrative/{id}")
    public ResponseEntity<String> narrativeCertificate(@PathVariable String id) {
        return get("/api/certificates/narrative/" + id, Map.of());
    }

    @GetMapping("/api/certificates/alert/{id}")
    public ResponseEntity<String> alertCertificate(@PathVariable String id) {
        return get("/api/certificates/alert/" + id, Map.of());
    }

    @PostMapping({
            "/api/demo/seed",
            "/api/ingest/replay",
            "/api/connectors/x/search",
            "/api/connectors/x/public",
            "/api/connectors/telegram/poll",
            "/api/connectors/telegram/public",
            "/api/connectors/youtube/search",
            "/api/connectors/youtube/free",
            "/api/connectors/meta/sync",
            "/api/connectors/instagram/hashtag",
            "/api/connectors/instagram/public",
            "/api/connectors/bluesky/search",
            "/api/connectors/reddit/search",
            "/api/connectors/mastodon/search"
    })
    public ResponseEntity<String> proxyPost(
            jakarta.servlet.http.HttpServletRequest request,
            @RequestBody(required = false) String payload
    ) {
        String downstreamPath = request.getRequestURI().substring("/api/gateway".length());
        try {
            String body = fastApi.post()
                    .uri(downstreamPath)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(payload == null || payload.isBlank() ? "{}" : payload)
                    .retrieve()
                    .body(String.class);
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body == null ? "{}" : body);
        } catch (RestClientResponseException ex) {
            return ResponseEntity.status(ex.getStatusCode())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(ex.getResponseBodyAsString());
        } catch (Exception ex) {
            return ResponseEntity.status(503)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body("{\"detail\":\"FastAPI analytics service is not reachable\"}");
        }
    }

    private ResponseEntity<String> get(String path, Map<String, String> query) {
        try {
            String body = fastApi.get()
                    .uri(builder -> {
                        builder.path(path);
                        query.forEach(builder::queryParam);
                        return builder.build();
                    })
                    .retrieve()
                    .body(String.class);
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body == null ? "{}" : body);
        } catch (RestClientResponseException ex) {
            return ResponseEntity.status(ex.getStatusCode())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(ex.getResponseBodyAsString());
        } catch (Exception ex) {
            return ResponseEntity.status(503)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body("{\"detail\":\"FastAPI analytics service is not reachable\"}");
        }
    }
}
