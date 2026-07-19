package cn.kylin.aiops;

import java.time.Instant;
import java.util.Map;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class DemoApplication {
    private final JdbcTemplate jdbc;

    public DemoApplication(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }

    @GetMapping("/api/demo")
    public Map<String, Object> demo() {
        Integer value = jdbc.queryForObject("SELECT 1", Integer.class);
        return Map.of("status", "ok", "database", value, "timestamp", Instant.now().toString());
    }
}
