package com.audiopipeline.service;

import com.audiopipeline.model.TaskStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Optional;

@Service
public class RedisStatusService {

    private static final Logger log = LoggerFactory.getLogger(RedisStatusService.class);
    private static final Duration TTL = Duration.ofHours(24);
    private static final String KEY_TEMPLATE = "task:%s:status";
    private static final String ERROR_KEY_TEMPLATE = "task:%s:error";

    private final RedisTemplate<String, String> redisTemplate;

    public RedisStatusService(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public void setStatus(String taskId, TaskStatus status) {
        String key = KEY_TEMPLATE.formatted(taskId);
        redisTemplate.opsForValue().set(key, status.name(), TTL);
        log.debug("Set task {} status to {}", taskId, status);
    }

    public Optional<TaskStatus> getStatus(String taskId) {
        String key = KEY_TEMPLATE.formatted(taskId);
        String value = redisTemplate.opsForValue().get(key);
        if (value == null) {
            return Optional.empty();
        }
        return Optional.of(TaskStatus.valueOf(value));
    }

    public void setError(String taskId, String error) {
        String key = ERROR_KEY_TEMPLATE.formatted(taskId);
        redisTemplate.opsForValue().set(key, error, TTL);
    }

    public Optional<String> getError(String taskId) {
        String key = ERROR_KEY_TEMPLATE.formatted(taskId);
        return Optional.ofNullable(redisTemplate.opsForValue().get(key));
    }
}
