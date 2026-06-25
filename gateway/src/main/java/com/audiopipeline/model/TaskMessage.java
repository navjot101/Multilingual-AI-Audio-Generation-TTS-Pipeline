package com.audiopipeline.model;

import java.time.Instant;

public record TaskMessage(
    String taskId,
    String script,
    String genre,
    String language,
    Instant createdAt
) {}
