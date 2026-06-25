package com.audiopipeline.controller;

import com.audiopipeline.model.GenerateRequest;
import com.audiopipeline.model.TaskResponse;
import com.audiopipeline.model.TaskStatus;
import com.audiopipeline.service.KafkaProducerService;
import com.audiopipeline.service.RedisStatusService;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.File;
import java.nio.file.Path;

@RestController
@RequestMapping("/v1/audio")
public class AudioController {

    private static final Logger log = LoggerFactory.getLogger(AudioController.class);

    private final KafkaProducerService kafkaProducerService;
    private final RedisStatusService redisStatusService;
    private final String sharedAudioPath;
    private final Counter audioGenerationCounter;

    public AudioController(KafkaProducerService kafkaProducerService,
                           RedisStatusService redisStatusService,
                           @Value("${shared.audio.path}") String sharedAudioPath,
                           MeterRegistry meterRegistry) {
        this.kafkaProducerService = kafkaProducerService;
        this.redisStatusService = redisStatusService;
        this.sharedAudioPath = sharedAudioPath;
        this.audioGenerationCounter = Counter.builder("audio_generation_total")
                .description("Total number of audio generation requests")
                .register(meterRegistry);
    }

    @PostMapping("/generate")
    public ResponseEntity<TaskResponse> generate(@Valid @RequestBody GenerateRequest request) {
        audioGenerationCounter.increment();
        String taskId = kafkaProducerService.publishTask(
                request.script(), request.genre(), request.language());

        TaskResponse response = new TaskResponse(
                taskId,
                TaskStatus.PENDING.name(),
                "/v1/audio/status/" + taskId,
                "/v1/audio/download/" + taskId);

        return ResponseEntity.accepted().body(response);
    }

    @GetMapping("/status/{taskId}")
    public ResponseEntity<TaskResponse> getStatus(@PathVariable String taskId) {
        var statusOpt = redisStatusService.getStatus(taskId);
        if (statusOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        TaskStatus status = statusOpt.get();
        TaskResponse response = new TaskResponse(
                taskId,
                status.name(),
                "/v1/audio/status/" + taskId,
                "/v1/audio/download/" + taskId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/download/{taskId}")
    public ResponseEntity<Resource> download(@PathVariable String taskId) {
        var statusOpt = redisStatusService.getStatus(taskId);
        if (statusOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        TaskStatus status = statusOpt.get();
        if (status != TaskStatus.DONE) {
            return ResponseEntity.status(409).build();
        }
        Path filePath = Path.of(sharedAudioPath, taskId + ".wav");
        File file = filePath.toFile();
        if (!file.exists()) {
            log.error("Audio file missing for task {} at {}", taskId, filePath);
            return ResponseEntity.notFound().build();
        }
        FileSystemResource resource = new FileSystemResource(file);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("audio/wav"))
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + taskId + ".wav\"")
                .body(resource);
    }
}
