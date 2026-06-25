package com.audiopipeline.service;

import com.audiopipeline.model.TaskMessage;
import com.audiopipeline.model.TaskStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.UUID;

@Service
public class KafkaProducerService {

    private static final Logger log = LoggerFactory.getLogger(KafkaProducerService.class);
    private static final String TOPIC = "audio-generation-tasks";

    private final KafkaTemplate<String, Object> kafkaTemplate;
    private final RedisStatusService redisStatusService;

    public KafkaProducerService(KafkaTemplate<String, Object> kafkaTemplate,
                                RedisStatusService redisStatusService) {
        this.kafkaTemplate = kafkaTemplate;
        this.redisStatusService = redisStatusService;
    }

    public String publishTask(String script, String genre, String language) {
        String taskId = UUID.randomUUID().toString();
        TaskMessage message = new TaskMessage(taskId, script, genre, language, Instant.now());

        redisStatusService.setStatus(taskId, TaskStatus.PENDING);
        kafkaTemplate.send(TOPIC, taskId, message);
        log.info("Published task {} to topic {}", taskId, TOPIC);

        return taskId;
    }
}
